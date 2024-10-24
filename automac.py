import getpass
import json
import logging
import os
import platform
import plistlib
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Union, Optional
from xml.etree.ElementTree import Element

debug_level = logging.DEBUG


# debug_level = logging.INFO

def str_to_int_or_zero(s):
    try:
        return int(s)
    except ValueError:
        return 0


def get_login():
    # XXX os.getlogin() returns `root` under PyCharm; using getpass instead
    return getpass.getuser()


def get_element(list_: list, index: int, def_val=None):
    if list_ is None:
        return def_val
    return list_[index] if 0 <= index < len(list_) else def_val


def read_file_lines(path):
    with open(path, 'r') as fd:
        lines = [line.strip() for line in fd]
    return lines


def drop_nones(list_: list):
    return list(filter(lambda x: x is not None, list_))


def app_name_to_base_name_without_ext(s: str):
    """
    Converts: `/Applications/TopNotch.app` => `TopNotch`
    """
    s = os.path.split(s)[1]
    s = re.sub(r'\.app', '', s)
    return s


class InputLang:

    def __init__(self, code: int, name: str):
        self.code = code
        self.name = name

    def xml_str(self):
        return f'<dict><key>InputSourceKind</key><string>Keyboard Layout</string><key>KeyboardLayout ID</key><integer>{self.code}</integer><key>KeyboardLayout Name</key><string>{self.name}</string></dict>'


class InputLangs:
    EN_US = InputLang(0, 'U.S.')
    EN_GB = InputLang(2, 'British')
    EN_ABC = InputLang(252, 'ABC')
    RU_PC = InputLang(19458, 'RussianWin')


class Notifications:
    flags_base = 8396814  # macos 13.7 defaults: notifications off, badges, sounds, banners

    def __init__(self, app: 'AutoMac'):
        self.app = app
        self.do_reload_configs = False

    def enable_app(self, app_name):
        self._enable_app_impl(app_name, True)

    def disable_app(self, app_name):
        self._enable_app_impl(app_name, False)

    def change_app(self, app_name, enable: bool):
        self._enable_app_impl(app_name, enable)

    def enable_bundle(self, bundle_id: str, app_path: str = None):
        self._change_ncpref(bundle_id, app_path, True)

    def disable_bundle_id(self, bundle_id: str, app_path: str = None):
        self._change_ncpref(bundle_id, app_path, False)

    def _change_ncpref(self, bundle_id: str, app_path: str, enable: bool):
        """
        Requires restart: NotificationCenter, usernoted.
        :param bundle_id: like 'com.sublimetext.4'
        :param app_path: like '/Applications/Sublime Text.app'
        :return:
        """

        def change_existing_ncpref_record():
            for i, app in enumerate(apps):
                if app.get('bundle-id') == bundle_id:
                    old_flags = app.get('flags')  # type: int
                    if old_flags is not None:
                        if enable:
                            new_flags = old_flags | FLAG_NOTIFICATIONS_ENABLED  # set flag
                        else:
                            new_flags = old_flags & ~FLAG_NOTIFICATIONS_ENABLED  # unset flag
                        if new_flags == old_flags:
                            # logging.debug(f'Flags already set for {bundle_id}')
                            pass
                        else:
                            # PlistBuddy requires a file path, not just domain
                            buddy_cmd = f'Set :apps:{i}:flags {new_flags}'
                            self.app.exec(['/usr/libexec/PlistBuddy', '-c', buddy_cmd, plist_file])
                            self.do_reload_configs = True
                    return True
            return False

        def add_new_ncpref_record():
            flags = self.flags_base | FLAG_NOTIFICATIONS_ENABLED if enable else self.flags_base
            new_entry_xml = f'<dict><key>auth</key><integer>7</integer><key>bundle-id</key><string>{bundle_id}</string><key>content_visibility</key><integer>0</integer><key>flags</key><integer>{flags}</integer><key>grouping</key><integer>0</integer><key>path</key><string>{app_path}</string><key>src</key><array></array></dict>'
            self.app.exec(['defaults', 'write', 'com.apple.ncprefs.plist', 'apps', '-array-add', new_entry_xml])
            self.do_reload_configs = True

        FLAG_NOTIFICATIONS_ENABLED = 1 << 25
        plist_file = f'/Users/{get_login()}/Library/Preferences/com.apple.ncprefs.plist'
        assert os.path.exists(plist_file)
        rc, cur_xml_text = self.app.exec_and_capture(['defaults', 'export', plist_file, '-'])
        xml = plistlib.loads(cur_xml_text.encode('utf-8'))
        apps = xml.get('apps') or []
        app_record_found = change_existing_ncpref_record()
        if not app_record_found:
            if app_path:
                add_new_ncpref_record()
            else:
                logging.debug(
                    f'New notification entry cannot be created for bundle id {bundle_id} because app path unknown')

    def _enable_app_impl(self, app_name, enable: bool):
        def symlink_to_file(path):
            # convert '/Applications/Brave Browser.app/Contents/Frameworks/Brave Browser Framework.framework/Versions/Current/Helpers/Brave Browser Helper (Alerts).app'
            # into '/Applications/Brave Browser.app/Contents/Frameworks/Brave Browser Framework.framework/Versions/129.1.70.123/Helpers/Brave Browser Helper (Alerts).app'
            # because macos uses versioned paths in ncprefs; not sure if it matters
            return os.path.realpath(path)

        app_path = self.app.find_app_path(app_name)
        if not app_path:
            logging.warning(f'''Missing app `{app_name}` - it won't be enabled''')
            return
        app_path = symlink_to_file(app_path)
        assert os.path.exists(app_path), f'Missing path: {app_path}'
        bundle_id = self.app.get_app_bundle_id(app_path)
        if bundle_id:
            self._change_ncpref(bundle_id, app_path, enable)

    def os_to_reload_configs(self):
        self.app.killall('System Settings', 'NotificationCenter', 'usernoted')


class Iterm2:
    DOMAIN = 'com.googlecode.iterm2'

    def __init__(self, app: 'AutoMac'):
        self.app = app

    def quit_silently(self):
        """iTerm2: Don't display the annoying prompt when quitting."""
        self.app.defaults.write(self.DOMAIN, 'PromptOnQuit', False)  # confirm quit iterm2
        self.app.defaults.write(self.DOMAIN, 'OnlyWhenMoreTabs', False)  # confirm closing multiple sessions

    def quit_when_all_windows_closed(self):
        self.app.defaults.write(self.DOMAIN, 'QuitWhenAllWindowsClosed', True)

    def update_disable(self):
        # todo these settings are the same for a bunch of apps: need to generalize this
        self.app.defaults.write(self.DOMAIN, 'SUAutomaticallyUpdate', False)
        self.app.defaults.write(self.DOMAIN, 'SUEnableAutomaticChecks', False)

    def analytics_off(self):
        self.app.defaults.write(self.DOMAIN, 'SUSendProfileInfo', False)


class AppCleaner:
    DOMAIN = 'net.freemacsoft.AppCleaner'

    def __init__(self, app: 'AutoMac'):
        self.app = app

    def update_disable(self):
        self.app.defaults.write(self.DOMAIN, 'SUAutomaticallyUpdate', False)
        self.app.defaults.write(self.DOMAIN, 'SUEnableAutomaticChecks', False)

    def mark_as_launched_before(self):
        self.app.defaults.write(self.DOMAIN, 'SUHasLaunchedBefore', True)

    def analytics_off(self):
        self.app.defaults.write(self.DOMAIN, 'SUSendProfileInfo', False)


class FileAssoc:
    def __init__(self, app: 'AutoMac'):
        self.app = app

    def extensions(self, app_name: str, role: str, extensions: list[str]):
        # todo check duti installed
        # todo resolve path to duti in runtime
        assert role in {'none', 'viewer', 'editor', 'all'}
        extensions = map(str.strip, extensions)
        extensions = filter(bool, extensions)
        extensions = list(extensions)
        bundle_id = self.app.get_app_bundle_id(app_name)
        for ext in extensions:
            ext_orig = ext
            ext = ext[1:] if ext.startswith('.') else ext
            if '.' in ext or not ext:
                logging.warning(f'Improper extension `{ext_orig}` - skipping')
                continue
            bundle_id_before = self._get_current_bundle_by_ext(ext)
            if bundle_id != bundle_id_before:
                # logging.debug(f'Change handler for {ext}: {cur_bundle} -> {bundle_id}')
                cmd = ['/opt/homebrew/bin/duti', '-s', bundle_id, f'.{ext}', role]
                self.app.exec(cmd)
                bundle_id_after = self._get_current_bundle_by_ext(ext)
                if bundle_id_before == bundle_id_after:
                    logging.warning(
                        f'Failed reassigning `{ext}` from `{bundle_id_before}` to `{bundle_id}` with role `{role}`. '
                        'Probably you want a stronger role: `editor` or `all`')

    def _get_current_bundle_by_ext(self, ext):
        rc, cur_settings = self.app.exec_and_capture(['/opt/homebrew/bin/duti', '-x', ext], check=False)
        # Example of `duti -x txt` output:
        #   TextEdit.app
        #   /System/Applications/TextEdit.app
        #   com.apple.TextEdit
        lines = cur_settings.splitlines()
        if rc != 0 or len(lines) < 3:
            return ''
        return lines[2]  # like 'com.apple.TextEdit'


class BrewManager:

    # XXX simple command `brew install xxx` tries to upgrade such package, so not using it

    def __init__(self, app: 'AutoMac'):
        self.app = app
        self.installed_packages_ = None  # populated on demand

    @property
    def installed_packages(self):
        if self.installed_packages_ is None:
            self.installed_packages_ = self._list_installed_packages()
        return self.installed_packages_

    def _list_installed_packages(self):
        cmd_str = f'{self.brew_exe} list'
        p = subprocess.run(cmd_str, shell=True, check=False, capture_output=True, encoding='utf-8')
        assert p.returncode == 0, f'Shell command failed: {cmd_str}'
        packages = p.stdout.splitlines()
        packages = [x.strip().lower() for x in packages]
        return set(packages)

    def install_homebrew(self):
        if not self._brew_exists():
            logging.debug('brew not found, installing it')
            # brew prohibits running it as sudo
            self.app.exec_temp_file(executor='bash', content=[
                '''/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'''
            ])

    def analytics_off(self):
        # output of `brew analytics` when disabled:
        #   InfluxDB analytics are disabled.
        #   Google Analytics were destroyed.
        _, cur_text = self.app.exec_and_capture([self.brew_exe, 'analytics'])
        if 'disabled' in cur_text and 'destroyed' in cur_text:
            pass
        else:
            self.app.exec([self.brew_exe, 'analytics', 'off'])

    def install_formulas(self, list_file: str):
        list_file = self.app._resolve_file(list_file)
        logging.debug(f'Installing brew formulas from {list_file}')
        lines = read_file_lines(list_file)
        lines = list(filter(lambda line: line and ('#' not in line), lines))
        cnt = 0
        for package in lines:
            self.install_formula(package)
            cnt += 1
        logging.debug(f'Formulas processed: {cnt}')

    def install_formula(self, package):
        package_lo = package.lower()
        if package_lo in self.installed_packages:
            # print(f'Already installed: {package}')
            return
        self.app.exec([self.brew_exe, 'install', package])

    def install_casks(self, list_file: str):
        list_file = self.app._resolve_file(list_file)
        logging.debug(f'Installing brew casks from {list_file}')
        lines = read_file_lines(list_file)
        lines = list(filter(lambda line: line and ('#' not in line), lines))
        cnt = 0
        for package in lines:
            self.install_cask(package)
            cnt += 1
        logging.debug(f'Casks processed: {cnt}')

    def install_cask(self, package):
        package_lo = package.lower()
        if package_lo in self.installed_packages:
            # print(f'Already installed: {package}')
            return
        installed_via_brew, existing_macos_apps = self._check_existing_brew_cask(package)
        if installed_via_brew:
            logging.debug(f'Already installed via brew: {package}')
            return
        if existing_macos_apps:
            logging.debug(f'No cask `{package}` installed but macos apps already exists: {existing_macos_apps} - skip')
            return
        # self.setup_manager.exec_string(f'brew install --cask {package}')
        self.app.exec([self.brew_exe, 'install', '--cask', package])

    def _check_existing_brew_cask(self, package):
        rc, stdout = self.app.exec_and_capture([self.brew_exe, 'info', package], check=False)
        installed_via_brew = rc == 0 and 'Not installed' not in stdout
        existing_macos_apps = self._find_macos_apps(stdout)
        return installed_via_brew, existing_macos_apps

    def _find_macos_apps(self, package_info_output):
        apps = []
        for line in package_info_output.splitlines():
            m = re.search(r'(.+\.app)', line, re.IGNORECASE)
            if m:
                app_file = m.group(1)  # like 'Sublime Text.app'
                app_file_full = f'/Applications/{app_file}'
                if os.path.exists(app_file):
                    apps.append(app_file)
                elif os.path.exists(app_file_full):
                    apps.append(app_file_full)
        return set(apps)

    def _brew_exists(self):
        return self._resolve_brew_executable() is not None

    @property
    def brew_exe(self):
        if path := self._resolve_brew_executable():
            return path
        else:
            self.app.abort('Brew not found')

    def _resolve_brew_executable(self):
        for path in ['/opt/homebrew/bin/brew', '/usr/local/bin/brew']:
            if os.path.exists(path):
                return path
        return None


class Scutil:

    def __init__(self, app: 'AutoMac'):
        self.app = app

    def write_if_needed(self, key: str, value: str):
        # XXX scutil exits with a non-zero code if setting missing
        rc, old_value = self.app.exec_and_capture(['scutil', '--get', key], check=False)
        if rc == 0 and old_value == value:
            # print(f'Already done: scutil {key} {value}')
            pass
        else:
            self.app.sudo(['scutil', '--set', key, value])


class Defaults:
    """
    An interface to the `defaults` utility that manages macos plist files.
    """

    def __init__(self, app: 'AutoMac'):
        self.app = app

    def read(self, domain: str, key: str):
        cmd = ['defaults', 'read', domain, key]
        rc, value = self.app.exec_and_capture(cmd, check=False)
        return value if rc == 0 else ''

    def write(self, domain: str, key: str, value: Union[str, int, bool], current_host=False, sudo_write=False):
        """
        Write a value into domain/key if not written yet.
        :param domain:
        :param key:
        :param value:
        :param current_host:
        :param sudo_write:
        :return:
        """

        def norm(val):
            if isinstance(val, bool):
                return '1' if val else '0'
            return str(val)

        def str_value(val):
            if isinstance(val, bool):
                return str(val).lower()
            return str(val)

        assert value is not None
        type_ = {str: '-string', int: '-int', bool: '-bool'}[type(value)]
        ch = '-currentHost' if current_host else None
        cmd = drop_nones(['defaults', ch, 'read', domain, key])
        rc, old_value = self.app.exec_and_capture(cmd, check=False)
        if rc == 0 and norm(value) == norm(old_value):
            # print(f'Already done: {domain} {key} {type_} {new_value}')
            pass
        else:
            cmd = drop_nones(['defaults', ch, 'write', domain, key, type_, str_value(value)])
            if sudo_write:
                self.app.sudo(cmd)
            else:
                self.app.exec(cmd)

    def write_object(self, domain: str, key: str, new_value: Union[list, dict]):
        """
        Write a value into domain/key if not written yet.
        :param domain:
        :param key:
        :param new_value:
        :return:
        """

        def dict_to_plist_xml(value: dict):
            """
            :param value: like {'1': 'y.MM.dd'}
            :return: like '<dict><key>1</key><string>y.MM.dd</string></dict>'
            """
            xml_str_1 = plistlib.dumps(value).decode('utf-8')
            root = ET.fromstring(xml_str_1)  # type: Element
            assert len(root) == 1
            first_child = root[0]
            xml_str_2 = ET.tostring(first_child).decode('utf-8')
            # todo strip \r\n\t only btw tags
            xml_str_2 = xml_str_2.replace('\r', '').replace('\n', '').replace('\t', '')
            return xml_str_2

        assert new_value is not None
        rc, cur_xml_text = self.app.exec_and_capture(['defaults', 'export', domain, '-'])
        # todo check rc
        xml = plistlib.loads(cur_xml_text.encode('utf-8'))
        cur_value = xml.get(key)
        if cur_value is None or new_value != cur_value:
            new_value_xml_str = dict_to_plist_xml(new_value)
            self.app.exec(['defaults', 'write', domain, key, new_value_xml_str])

    def delete_key(self, domain: str, key: str):
        """
        Delete a value by the given domain/key if one exists.
        :param domain:
        :param key:
        :return:
        """
        cmd = ['defaults', 'read', domain, key]
        rc, value = self.app.exec_and_capture(cmd, check=False)
        key_exists = rc == 0
        if key_exists:
            self.app.exec(['defaults', 'delete', domain, key])


class System:

    def __init__(self, app: 'AutoMac'):
        self.app = app

    def current_timezone(self):
        rc, path = self.app.exec_and_capture(['readlink', '/etc/localtime'])
        # path is like '/var/db/timezone/zoneinfo/Europe/Moscow'
        return path.replace('/var/db/timezone/zoneinfo/', '')


class Files:
    def __init__(self, app: 'AutoMac'):
        self.app = app

    def link(self, master_file: str, alias: str):
        # print(f'link_forced: {alias} -> {master_file}')
        master_file = os.path.expanduser(master_file)
        alias = os.path.expanduser(alias)
        assert os.path.exists(master_file), f'Missing master_file: {master_file}'
        if os.path.lexists(alias):
            if os.path.islink(alias):
                current_target = os.readlink(alias)
                if os.path.exists(current_target) and os.path.samefile(master_file, current_target):
                    # print(f'Alias is fine already: {alias} -> {master_file}')
                    return
                else:
                    self.remove(alias)
            elif os.path.isdir(alias):
                self.app.abort(f'Param `alias` cannot be an existing directory: {alias}')
            else:
                self.remove(alias)
        self.mkdir(str(Path(alias).parent))
        self.app.exec(['ln', '-s', master_file, alias])

    def remove(self, path):
        print(f'Removing {path}')
        os.remove(str(path))

    def mkdir(self, path: str):
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            self.app.exec(['mkdir', '-p', path])
        return path

    def mkdirs(self, *paths):
        for path in paths:
            self.mkdir(path)

    def unset_hidden_flag(self, *paths: str):
        for path in paths:
            self._unset_hidden_flag_one(path)

    def _unset_hidden_flag_one(self, path: str):
        path = os.path.expanduser(path)
        res = os.lstat(path)
        hidden = (res.st_flags & stat.UF_HIDDEN) != 0  # UF_HIDDEN is macos-specific
        if hidden:
            # todo no sudo needed for home folders
            self.app.sudo(['chflags', 'nohidden', path])


def get_os_name():
    s = platform.system()
    return {'Darwin': 'macOS'}.get(s) or s


class AutoMac:

    def __init__(self):
        logging.basicConfig(
            level=debug_level,
            format='%(levelname)-5s %(message)s'
        )
        self._lookup_dirs = []
        self.brew = BrewManager(self)  # type: BrewManager
        self.defaults = Defaults(self)  # type: Defaults
        self.scutil = Scutil(self)  # type: Scutil
        self.assoc = FileAssoc(self)  # type: FileAssoc
        self.system = System(self)  # type: System
        self.fs = Files(self)  # type: Files
        self.notifications = Notifications(self)  # type: Notifications
        self.appcleaner = AppCleaner(self)  # type: AppCleaner
        self.iterm2 = Iterm2(self)  # type: Iterm2
        self.manual_steps = []
        self.success = True
        self._machine_serial = self._resolve_serial_number()
        self._enter_called = False  # todo check it's true when a method called

    def __enter__(self):
        self._enter_called = True
        # logging.basicConfig(level=logging.INFO)
        logging.info('AutoMac started')  # todo logged as root x_x
        logging.info(f'{get_os_name()} {platform.mac_ver()[0]} {platform.machine()} {platform.architecture()[0]}')
        logging.debug(f'os.getlogin(): {os.getlogin()}')
        logging.debug(f'getpass.getuser(): {getpass.getuser()}')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.success:
            if self.notifications.do_reload_configs:
                self.notifications.os_to_reload_configs()
            print('OK')
        if self.manual_steps:
            print('')
            print('Manual setup required:')
            for msg in self.manual_steps:
                print(f'- {msg}')

    def add_lookup_folder(self, path: str):
        resolved = self._prepare_lookup_dir(path, check=False)
        status = 'exists' if os.path.exists(resolved) else 'missing'
        logging.debug(f'add_lookup_folder {resolved} ({status})')
        self._lookup_dirs.append(resolved)

    def _prepare_lookup_dir(self, path: str, check=True):
        path = Path(path).expanduser()
        if check:
            assert os.path.exists(path), path
        return path

    def _resolve_serial_number(self):
        rc, stdout = self.exec_and_capture(['system_profiler', 'SPHardwareDataType', '-json'])
        root = json.loads(stdout)
        return root['SPHardwareDataType'][0]['serial_number']  # todo safe read

    def get_machine_serial(self):
        return self._machine_serial

    def is_virtual_machine(self):
        # todo seems only UTM-compatible
        rc = self.exec_temp_file(["system_profiler SPHardwareDataType -json | grep -i virtual > /dev/null"],
                                 check=False, log=False)
        return rc == 0

    def _resolve_file(self, file):
        path = Path(file)
        if path.is_absolute():
            if not path.exists():
                self.abort(f'Missing file {file}')
            return path
        else:
            # todo start looking in CWD
            for lookup_dir in self._lookup_dirs:
                file_full = lookup_dir / path
                return file_full
        self.abort(f'Missing file {file}')
        return path

    def killall(self, *app_names: str):
        for app in app_names:
            self.exec(['killall', app], check=False)

    def exec_and_capture(self, cmd: list, check=True, shell=False, charset='utf-8', stderr=subprocess.PIPE, log=False):
        cmd_str = shlex.join(cmd)
        if log:
            logging.info(f'EXEC: {cmd_str}')
        p = subprocess.Popen(cmd, stderr=stderr, stdout=subprocess.PIPE, shell=shell)
        stdout, stderr = p.communicate()
        if check and p.returncode != 0:
            self.abort(f'Shell command failed: {cmd_str} - exit code {p.returncode}')
        return p.returncode, stdout.decode(charset).strip()

    def _exec_interactive(self, cmd: Union[str, list], check=True, stdout=None, stderr=None, log=True):
        if isinstance(cmd, list):
            cmd_str = shlex.join(cmd)
            cmd_list = cmd
        elif isinstance(cmd, str):
            cmd_str = cmd
            cmd_list = shlex.split(cmd)
        else:
            raise Exception('should not happen')
        if log:
            logging.info(f'Exec: {cmd_str}')
        p = subprocess.Popen(cmd_list, stdout=stdout, stderr=stderr)
        stdout, stderr = p.communicate()
        if check and p.returncode != 0:
            self.abort(f'Shell command failed: {cmd_str} - exit code {p.returncode}')
        return p.returncode

    def exec(self, cmd: Union[str, list], check=True, log=True):
        return self._exec_interactive(cmd, check=check, log=log)

    def sudo(self, cmd: Union[str, list], check=True, charset='utf-8'):
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        cmd_list = ['sudo', '-S', '--'] + cmd
        cmd_str = shlex.join(cmd_list)
        logging.info(f'Exec: {cmd_str}')
        p = subprocess.Popen(cmd_list, stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if p.returncode != 0 and check:
            self.abort(f'Last command exited with code {p.returncode}')
        return stdout.decode(charset).rstrip()

    def exec_script_file(self, shell_script_file, shell='bash'):
        shell_script_file = self._resolve_file(shell_script_file)
        self.exec([shell, str(shell_script_file)])

    def manual_step(self, text):
        self.manual_steps.append(text)

    def abort(self, msg):
        self.success = False
        logging.error(f'ABORT: {msg}')
        sys.exit(1)

    def warn(self, msg):
        logging.warning(f'WARNING: {msg}')

    def is_app_running(self, app_base_name):
        """
        :param app_base_name: like 'Sublime Text'
        :return: 
        """
        # todo pgrep matches not only 'TopNotch' but 'TopNot' too
        rc = self._exec_interactive(['pgrep', app_base_name], check=False, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    log=False)
        return rc == 0

    def run_app(self, app: str):
        """
        Make sure the given app is running.
        :param app: like 'TopNotch' or '/Applications/TopNotch.app'
        """
        base_name = re.sub(r'.*/', '', app)
        base_name = re.sub(r'\.app$', '', base_name)
        assert '/' not in base_name
        if not self.is_app_running(base_name):
            abs_path = self.resolve_app_path(app)
            self.exec(['open', abs_path])

    def sudo_temp_file(self, content: list, executor='bash'):
        assert executor
        assert content
        script_file = tempfile.mktemp('.sh')
        text = '\n'.join(content)
        Path(script_file).write_text(text)
        self.sudo([executor, script_file])

    def exec_temp_file(self, content: list, executor='bash', check=True, log=True):
        assert executor
        assert content
        script_file = tempfile.mktemp('.sh')
        text = '\n'.join(content)
        if log:
            for line in content:
                logging.info(f'EXEC LINE: {line}')
        Path(script_file).write_text(text)
        return self.exec([executor, script_file], check=check, log=log)

    def exec_osa_script(self, text: str, check=True, log=True):
        assert text
        script_file = tempfile.mktemp('.sh')
        if log:
            logging.info(f'EXEC OSA SCRIPT: {text}')
        Path(script_file).write_text(text)
        return self.exec_and_capture(['osascript', script_file], check=check, log=log)

    def user_shell(self, shell_path: str):
        """
        Change user shell to a given path.
        If the shell not in `/etc/shells` yet, then it will be added.
        :param shell_path: like `/opt/homebrew/bin/bash`
        """

        def current_shell():
            rc, stdout = self.exec_and_capture(['dscl', '.', '-read', f'/Users/{get_login()}', 'UserShell'],
                                               check=False)
            # todo warn if rc != 0
            # stdout be like 'UserShell:   /bin/zsh'
            words = stdout.split()
            return get_element(words, 1)

        def is_shell_registered():
            lines = Path(etc_shells).read_text().splitlines()
            return shell_path in lines

        assert os.path.exists(shell_path)
        assert os.path.isabs(shell_path)
        assert os.geteuid() != 0  # not root; health check
        etc_shells = '/etc/shells'
        if not is_shell_registered():
            self.sudo_temp_file([
                'set -x',
                f'echo "{shell_path}" | sudo tee -a {etc_shells}',
            ])
        cur_shell = current_shell()
        if not cur_shell:
            self.warn(f'Failed to determine login shell for user {get_login()}')
        if shell_path != cur_shell:
            self.exec(['chsh', '-s', shell_path, get_login()])
            self.manual_step('New shell session required')

    def link(self, master_file: str, alias: str):
        """
        An equivalent of `ln -s master_file alias`.
        If `alias` is a real file, it will be removed and replaced with a link.
        :param master_file:
        :param alias:
        :return:
        """
        return self.fs.link(master_file, alias)

    def mkdirs(self, *paths):
        """
        Create given directories; all necessary parents will be created also.
        Works like `mkdir -p`.
        """
        return self.fs.mkdirs(*paths)

    def unset_hidden_flag(self, *paths: str):
        return self.fs.unset_hidden_flag(*paths)

    def timezone(self, tz_name):
        # todo add function to list available tz
        # immediate effect
        if tz_name == self.system.current_timezone():
            pass
        else:
            # todo hide stderr
            self.sudo(['systemsetup', '-settimezone', tz_name])

    def all_computer_names(self, name):
        """
        Change computer names: basic machine name, host name, local host name, samba name.
        """
        self.computer_name(name)
        self.host_name(name)
        self.local_host_name(name)
        self.samba_name(name)

    def computer_name(self, name):
        assert name
        self.scutil.write_if_needed('ComputerName', name)

    def host_name(self, name):
        assert name
        self.scutil.write_if_needed('HostName', name)

    def local_host_name(self, name):
        assert name
        # todo dots or underscores leads to error 'Invalid argument'
        self.scutil.write_if_needed('LocalHostName', name)

    def samba_name(self, name):
        assert name
        self.defaults.write('/Library/Preferences/SystemConfiguration/com.apple.smb.server',
                            'NetBIOSName',
                            name, sudo_write=True)

    def locale_region(self, locale: str, currency: str = None):
        """
        GUI: Settings / General / Language & Region / Region.
        Ok for macos 14.
        :param locale: like 'en_US', 'en_GB'
        :param currency: like 'EUR', optional
        """
        locale_full = f'{locale}@currency={currency}' if currency else locale
        self.defaults.write('NSGlobalDomain', 'AppleLocale', locale_full)

    def locale_region_en_us(self):
        """
        Settings / General / Language & Region / Region
        """
        return self.locale_region('en_US')

    def locale_preferred_languages(self, *langs: str):
        """
        Settings / General / Language & Region / Preferred languages
        :param langs: like 'en-US', 'en' or 'ru'
        :return:
        """
        # defaults write NSGlobalDomain AppleLanguages -array "en-US" "ru"
        assert langs
        self.defaults.write_object('NSGlobalDomain', 'AppleLanguages', list(langs))

    def locale_temperature_celsius(self):
        """
        Settings / General / Language & Region / Temperature
        :return:
        """
        self.defaults.write('NSGlobalDomain', 'AppleTemperatureUnit', 'Celsius')

    def locale_temperature_fahrenheit(self):
        """
        Settings / General / Language & Region / Temperature
        :return:
        """
        # todo better delete the key, as it does macos (although 'Fahrenheit' works at 14)
        self.defaults.write('NSGlobalDomain', 'AppleTemperatureUnit', 'Fahrenheit')

    def locale_metric(self):
        """
        Settings / General / Language & Region / Measurement System
        :return:
        """
        self.defaults.write('NSGlobalDomain', 'AppleMeasurementUnits', 'Centimeters')
        self.defaults.write('NSGlobalDomain', 'AppleMetricUnits', True)

    def locale_date_format_1970_01_31_dashed(self):
        """
        Change date format to 1970-01-31.
        GUI: Settings / General / Language & Region / Date format.
        Effect immediate but System Settings must be restarted to reload config.
        """
        self.__locale_date_format_impl('y-MM-dd')

    def locale_date_format_1970_01_31_dotted(self):
        """
        Change date format to 1970.01.31.
        GUI: Settings / General / Language & Region / Date format.
        Effect immediate but System Settings must be restarted to reload config.
        """
        self.__locale_date_format_impl('y.MM.dd')

    def locale_date_format_1970_1_31_slashed(self):
        """
        Change date format to 1970/1/31.
        GUI: Settings / General / Language & Region / Date format.
        Effect immediate but System Settings must be restarted to reload config.
        """
        self.__locale_date_format_impl('y/M/d')

    def locale_date_format_31_01_1970_dashed(self):
        """
        Change date format to 31-01-1970.
        GUI: Settings / General / Language & Region / Date format.
        Effect immediate but System Settings must be restarted to reload config.
        """
        self.__locale_date_format_impl('dd-MM-y')

    def locale_date_format_31_01_1970_dotted(self):
        """
        Change date format to 31.01.1970.
        GUI: Settings / General / Language & Region / Date format.
        Effect immediate but System Settings must be restarted to reload config.
        """
        self.__locale_date_format_impl('dd.MM.y')

    def locale_date_format_31_01_1970_slashed(self):
        """
        Change date format to 31/01/1970.
        GUI: Settings / General / Language & Region / Date format.
        Effect immediate but System Settings must be restarted to reload config.
        """
        self.__locale_date_format_impl('dd/MM/y')

    def locale_date_format_31_1_70_slashed(self):
        """
        Change date format to 31/1/70.
        GUI: Settings / General / Language & Region / Date format.
        Effect immediate but System Settings must be restarted to reload config.
        """
        self.__locale_date_format_impl('d/M/yy')

    def locale_date_format_1_31_70_slashed(self):
        """
        Change date format to 1/31/70.
        GUI: Settings / General / Language & Region / Date format.
        Effect immediate but System Settings must be restarted to reload config.
        """
        # todo macos deletes AppleICUDateFormatStrings in this case; better mimic this
        self.__locale_date_format_impl('M/d/yy')

    def locale_date_format_usa(self):
        """
        Change date format to 1/31/70.
        GUI: Settings / General / Language & Region / Date format.
        Effect immediate but System Settings must be restarted to reload config.
        """
        self.locale_date_format_1_31_70_slashed()

    def locale_date_format_iso(self):
        """
        Change date format to 1970-01-31.
        GUI: Settings / General / Language & Region / Date format.
        Effect immediate but System Settings must be restarted to reload config.
        """
        self.locale_date_format_1970_01_31_dashed()

    def __locale_date_format_impl(self, fmt: str):
        # example:
        # defaults write NSGlobalDomain AppleICUDateFormatStrings -dict 1 'y-MM-dd'
        value = {'1': fmt}
        self.defaults.write_object('NSGlobalDomain', 'AppleICUDateFormatStrings', value)

    def locale_first_day_monday(self):
        self.defaults.write_object('NSGlobalDomain', 'AppleFirstWeekday', {'gregorian': 2})

    def locale_time_format_12h(self):
        """
        Logout required.
        :return:
        todo AppleICUForce12HourTime, https://github.com/tech-otaku/menu-bar-clock
        """
        self.defaults.write('NSGlobalDomain', 'AppleICUForce24HourTime', False)

    def locale_time_format_24h(self):
        """
        Logout required.
        :return:
        """
        self.defaults.write('NSGlobalDomain', 'AppleICUForce24HourTime', True)

    def theme_light(self):
        """
        Works. Logout required.
        :return:
        """
        self.defaults.delete_key('NSGlobalDomain', 'AppleInterfaceStyle')
        self.defaults.write('NSGlobalDomain', 'AppleInterfaceStyleSwitchesAutomatically', False)

    def theme_dark(self):
        """
        Works. Logout required.
        :return:
        """
        self.defaults.write('NSGlobalDomain', 'AppleInterfaceStyle', 'Dark')
        self.defaults.write('NSGlobalDomain', 'AppleInterfaceStyleSwitchesAutomatically', False)

    def theme_auto(self):
        """
        Works. Logout required.
        :return:
        """
        self.defaults.delete_key('NSGlobalDomain', 'AppleInterfaceStyle')
        self.defaults.write('NSGlobalDomain', 'AppleInterfaceStyleSwitchesAutomatically', True)

    def trackpad_tap_to_click(self):
        # defaults write com.apple.driver.AppleBluetoothMultitouch.trackpad Clicking -bool true
        # defaults write com.apple.AppleMultitouchTrackpad Clicking -bool true
        self.defaults.write('com.apple.driver.AppleBluetoothMultitouch.trackpad', 'Clicking', True)
        self.defaults.write('com.apple.AppleMultitouchTrackpad', 'Clicking', True)

    def trackpad_drag_three_fingers(self):
        """
        Drag using three fingers.
        GUI: Pointer Control >  Trackpad Options > Dragging Style: Three Finger Drag.
        Works. Logout required.
        """
        # defaults write com.apple.AppleMultitouchTrackpad Dragging -bool false
        # defaults write com.apple.AppleMultitouchTrackpad TrackpadThreeFingerDrag -bool true
        self.defaults.write('com.apple.AppleMultitouchTrackpad', 'Dragging', False)
        self.defaults.write('com.apple.AppleMultitouchTrackpad', 'TrackpadThreeFingerDrag', True)

    def menubar_input_language_show(self):
        # Show input language switch; works; immediate
        # defaults write com.apple.TextInputMenu visible -bool true
        self.defaults.write('com.apple.TextInputMenu', 'visible', True)

    def menubar_date_hide(self):
        # Menu Bar Only > Clock Options > Show Date: Never
        # defaults write "com.apple.menuextra.clock" ShowDate -int 2
        self.defaults.write('com.apple.menuextra.clock', 'ShowDate', 2)

    def menubar_dow_hide(self):
        """
        GUI: System Settings > Control Center > Menu Bar Only > Clock Options > Show the day of the week.
        """
        # defaults write "com.apple.menuextra.clock" ShowDayOfWeek -bool false
        self.defaults.write('com.apple.menuextra.clock', 'ShowDayOfWeek', False)

    def menubar_spotlight_hide(self):
        # Menu Bar Only > Spotlight > Don't Show in Menu Bar
        # defaults -currentHost write com.apple.Spotlight MenuItemHidden -int 1
        self.defaults.write('com.apple.Spotlight', 'MenuItemHidden', 1, current_host=True)

    def dock_minimize_window_into_app_icon(self):
        # Dock > Minimize windows into application icon; works; logout required
        # defaults write com.apple.dock minimize-to-application -bool true
        self.defaults.write('com.apple.dock', 'minimize-to-application', True)

    def dock_icon_size(self, size: int):
        self.defaults.write('com.apple.dock', 'tilesize', size)

    def dock_orientation_left(self):
        """Works; killall Dock."""
        self.defaults.write('com.apple.dock', 'orientation', 'left')

    def dock_orientation_right(self):
        """Works; killall Dock."""
        self.defaults.write('com.apple.dock', 'orientation', 'right')

    def trash_empty_warning_disable(self):
        # Disable the warning lang-before emptying the Trash; works; immediate
        # defaults write com.apple.finder WarnOnEmptyTrash -bool false
        self.defaults.write('com.apple.finder', 'WarnOnEmptyTrash', False)

    def finder_file_extensions_show(self):
        # Finder: show all filename extensions; macos hides extension for screenshot at least; works; app restart required
        # defaults write NSGlobalDomain AppleShowAllExtensions -bool true
        self.defaults.write('NSGlobalDomain', 'AppleShowAllExtensions', True)

    def finder_file_extensions_rename_silently(self):
        """
        Disable the warning when changing a file extension; works; immediate.
        """
        # defaults write com.apple.finder FXEnableExtensionChangeWarning -bool false
        self.defaults.write('com.apple.finder', 'FXEnableExtensionChangeWarning', False)

    def finder_view_as_list(self):
        self.defaults.write('com.apple.finder', 'FXPreferredViewStyle', 'Nlsv')

    def finder_default_folder_downloads(self):
        """Set default folder (Downloads) for a new Finder window. Effect immediate."""
        self.finder_default_folder(str(Path.home() / 'Downloads'))

    def finder_default_folder_desktop(self):
        """Set default folder (Desktop) for a new Finder window. Effect immediate."""
        self.finder_default_folder(str(Path.home() / 'Desktop'))

    def finder_default_folder(self, folder: str):
        """Set default folder for a new Finder window. Effect immediate."""
        path = Path(folder).expanduser()
        assert path.is_absolute()
        assert path.exists()
        assert path.is_dir()
        is_desktop = path.samefile(str(Path.home() / 'Desktop'))
        self.defaults.write('com.apple.finder', 'NewWindowTarget', 'PfDe' if is_desktop else 'PfLo')
        self.defaults.write('com.apple.finder', 'NewWindowTargetPath', f'file://{path}')

    def finder_sort_folders_atop(self, enable=True):
        """Keep folders on top when sorting by name. Effect immediate."""
        self.defaults.write('com.apple.finder', '_FXSortFoldersFirst', enable)

    def finder_path_in_title(self, enable=True):
        """Display full path in Finder's window/tab title. Restart Finder."""
        self.defaults.write('com.apple.finder', '_FXShowPosixPathInTitle', enable)

    def keyboard_languages(self, *langs: InputLang, keep_non_keyboard_methods=True):
        """
        Logout required.
        :param keep_non_keyboard_methods: todo impl
        """
        domain = 'com.apple.HIToolbox'
        key = 'AppleEnabledInputSources'
        old_value = self.defaults.read(domain, key)
        any_missing = any(lang for lang in langs if f'= {lang.code};' not in old_value)  # todo poor implementation now
        if any_missing:
            xmls = [lang.xml_str() for lang in langs]
            cmd = ['defaults', 'write', domain, key, '-array'] + xmls
            self.exec(cmd)

    def _keyboard_languages_abc_and_ru_pc(self):
        # todo remove
        # Set two input languages: ABC and Russian PC.
        domain = 'com.apple.HIToolbox'
        key = 'AppleEnabledInputSources'
        old_value = self.defaults.read(domain, key)
        done = ('252' in old_value) and ('19458' in old_value)
        if not done:
            self.exec([
                'defaults', 'write', domain, key, '-array',
                '<dict><key>InputSourceKind</key><string>Keyboard Layout</string><key>KeyboardLayout ID</key><integer>252</integer><key>KeyboardLayout Name</key><string>ABC</string></dict>',
                '<dict><key>Bundle ID</key><string>com.apple.CharacterPaletteIM</string><key>InputSourceKind</key><string>Non Keyboard Input Method</string></dict>',
                '<dict><key>InputSourceKind</key><string>Keyboard Layout</string><key>KeyboardLayout ID</key><integer>19458</integer><key>KeyboardLayout Name</key><string>RussianWin</string></dict>',
            ])

    def keyboard_navigation_enable(self):
        """
        Works. You may be required to restart an app.
        Sonoma uses int values 0 and 2.
        """
        self.defaults.write('NSGlobalDomain', 'AppleKeyboardUIMode', 2)

    def keyboard_navigation_disabled(self):
        """
        Works. You may be required to restart an app.
        Sonoma uses int values 0 and 2.
        """
        self.defaults.write('NSGlobalDomain', 'AppleKeyboardUIMode', 0)

    def dock_orientation_bottom(self):
        """Works; killall Dock."""
        self.defaults.write('com.apple.dock', 'orientation', 'bottom')

    def assoc_file_extensions_viewer(self, app_name: str, extensions: list[str]):
        """
        Associate a viewer with the given file types.
        Can be used for music and video.
        """
        self.assoc.extensions(app_name, 'viewer', extensions)

    def assoc_file_extensions_editor(self, app_name: str, extensions: list[str]):
        """
        Associate an editor with the given file types.
        Can be used for textual files.
        """
        self.assoc.extensions(app_name, 'editor', extensions)

    def _assoc_file_extensions_all(self, app_name: str, extensions: list[str]):
        # not sure someone should use it
        self.assoc.extensions(app_name, 'all', extensions)

    def close_windows_when_quitting_an_app(self):
        # todo
        pass

    def resolve_app_path(self, app_name: str):
        """
        Resolve the absolute path to a macos app.
        Fails if path doesn't exist.
        :param app_name: like 'Sublime Text' or '/Applications/Sublime Text.app'
        :return: like '/Applications/Sublime Text.app'
        """
        app_path = self.find_app_path(app_name)
        assert app_path, f'No app found by app name {app_name}'
        assert os.path.exists(app_path), app_path
        return app_path

    def find_app_path(self, app_name: str):
        """
        Find the absolute path to a macos app.
        :param app_name: like 'Sublime Text' or '/Applications/Sublime Text.app'
        :return: like '/Applications/Sublime Text.app' or None
        """
        # a place with system apps: /System/Library/CoreServices
        if os.path.isabs(app_name):
            app_path = app_name
        else:
            if not app_name.endswith('.app'):
                app_name = f'{app_name}.app'
            app_path = f'/Applications/{app_name}'
        return app_path if os.path.exists(app_path) else None

    def app_exists(self, app_name: str):
        path = self.find_app_path(app_name)
        return bool(path)

    def file_exists(self, path: str):
        path = Path(path).expanduser()
        return path.exists()

    def get_app_bundle_id(self, app_name_or_path: str):
        """
        :param app_name_or_path:
        :return: bundle id; or throw exception if app not found
        """
        rc, bundle_id = self.exec_and_capture(['osascript', '-e', f'id of app "{app_name_or_path}"'])
        return bundle_id

    def quarantine_remove_app(self, app_name: str):
        app_path = self.resolve_app_path(app_name)
        xattrs = self._get_xattrs(app_path)
        if 'com.apple.quarantine' in xattrs:
            self.exec(['xattr', '-dr', 'com.apple.quarantine', app_path])

    def _get_xattrs(self, path: str):
        assert os.path.exists(path)
        rc, stdout = self.exec_and_capture(['xattr', path])
        return stdout.splitlines()

    def get_mac_version_str(self):
        return platform.mac_ver()[0]

    def get_mac_version(self):
        """
        Return current macos version as a three-int tuple.
        """
        tup = platform.mac_ver()[0].split('.')
        tup = list(map(str_to_int_or_zero, tup))
        while len(tup) < 3:
            tup.append(0)
        return tuple(tup)

    def screen_lock_off(self, password: str = None):
        """
        Default screen lock is 300 sec, macos 14.7.
        :param password: user will be prompted for password if missing
        """
        # XXX sysadminctl prints current status to stderr bsr
        # XXX password '-' means that user will be asked for it in prompt
        rc, text = self.exec_and_capture(['sysadminctl', '-screenLock', 'status'], stderr=subprocess.STDOUT)
        if 'screenLock is off' not in text:
            self.exec(['sysadminctl', '-screenLock', 'off', '-password', password if password else '-'])

    def desktop_iphone_widgets_disable(self):
        """
        System Settings / Desktop & Dock / Widgets / Use iPhone widgets.
        Missing keys `remoteWidgetsEnabled` and `effectiveRemoteWidgetsEnabled` means the feature is enabled (Sonoma).
        Effect immediate, in System Settings at least (Sonoma).
        """
        domain = 'com.apple.chronod'
        self.defaults.write(domain, 'remoteWidgetsEnabled', False)
        self.defaults.write(domain, 'effectiveRemoteWidgetsEnabled', False)
        self.defaults.write(domain, 'hasRemoteWidgets', False)

    def login_items_add(self, app_path: str):
        """
        Make an app running at startup.
        :param app_path: an absolute path like `/Applications/TopNotch.app`
        """
        assert os.path.isabs(app_path), app_path
        assert os.path.exists(app_path), app_path
        bn = app_name_to_base_name_without_ext(app_path)
        cur_items = self.login_items_list()
        if bn not in cur_items:
            self._login_items_add_impl(app_path)

    def login_items_list(self):
        """
        Return current list of login items in form of ['Dropbox', 'TopNotch'].
        No full paths or uniq ids.
        """
        rc, out = self.exec_osa_script('''tell application "System Events" to get the name of every login item''',
                                       log=False)
        items = out.split(',')
        items = list(map(str.strip, items))
        items = list(filter(bool, items))
        return items

    def _login_items_add_impl(self, app_path: str):
        """
        Add a new login item.
        :param app_path: full path to an app, like '/Applications/TopNotch.app'
        """
        # not sure what param `hidden` means
        # subsequent addition has no effect, 14.7
        text = f'''tell application "System Events" to make login item at end with properties {{path:"{app_path}", hidden:true}}'''
        self.exec_osa_script(text)
