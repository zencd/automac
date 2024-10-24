import getpass
import json
import logging
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

import util
from base import AutoMacBase
from features.appcleaner import AppCleaner
from features.brew import BrewManager
from features.defaults import Defaults
from features.exec import Exec
from features.fileassoc import FileAssoc
from features.files import Files
from features.iterm2 import Iterm2
from features.notifications import Notifications
from features.scutil import Scutil
from features.system import System

debug_level = logging.DEBUG


# debug_level = logging.INFO


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


class AutoMac(AutoMacBase):

    def __init__(self):
        logging.basicConfig(
            level=debug_level,
            format='%(levelname)-5s %(message)s'
        )
        self._lookup_dirs = []
        self.exec = Exec(self)
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
        logging.info(f'{util.get_os_name()} {platform.mac_ver()[0]} {platform.machine()} {platform.architecture()[0]}')
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
        rc, stdout = self.exec.exec_and_capture(['system_profiler', 'SPHardwareDataType', '-json'])
        root = json.loads(stdout)
        return root['SPHardwareDataType'][0]['serial_number']  # todo safe read

    def get_machine_serial(self):
        return self._machine_serial

    def is_virtual_machine(self):
        # todo seems only UTM-compatible
        rc = self.exec.exec_temp_file(["system_profiler SPHardwareDataType -json | grep -i virtual > /dev/null"],
                                      check=False, log=False)
        return rc == 0

    def resolve_file(self, file):
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
            self.exec.exec(['killall', app], check=False)

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
        rc = self.exec.exec_interactive(['pgrep', app_base_name], check=False, stdout=subprocess.PIPE,
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
            self.exec.exec(['open', abs_path])

    def user_shell(self, shell_path: str):
        """
        Change user shell to a given path.
        If the shell not in `/etc/shells` yet, then it will be added.
        :param shell_path: like `/opt/homebrew/bin/bash`
        """

        def current_shell():
            rc, stdout = self.exec.exec_and_capture(['dscl', '.', '-read', f'/Users/{util.get_login()}', 'UserShell'],
                                                    check=False)
            # todo warn if rc != 0
            # stdout be like 'UserShell:   /bin/zsh'
            words = stdout.split()
            return util.get_element(words, 1)

        def is_shell_registered():
            lines = Path(etc_shells).read_text().splitlines()
            return shell_path in lines

        assert os.path.exists(shell_path)
        assert os.path.isabs(shell_path)
        assert os.geteuid() != 0  # not root; health check
        etc_shells = '/etc/shells'
        if not is_shell_registered():
            self.exec.sudo_temp_file([
                'set -x',
                f'echo "{shell_path}" | sudo tee -a {etc_shells}',
            ])
        cur_shell = current_shell()
        if not cur_shell:
            self.warn(f'Failed to determine login shell for user {util.get_login()}')
        if shell_path != cur_shell:
            self.exec.exec(['chsh', '-s', shell_path, util.get_login()])
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
            self.exec.sudo(['systemsetup', '-settimezone', tz_name])

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
            self.exec.exec(cmd)

    def _keyboard_languages_abc_and_ru_pc(self):
        # todo remove
        # Set two input languages: ABC and Russian PC.
        domain = 'com.apple.HIToolbox'
        key = 'AppleEnabledInputSources'
        old_value = self.defaults.read(domain, key)
        done = ('252' in old_value) and ('19458' in old_value)
        if not done:
            self.exec.exec([
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
        rc, bundle_id = self.exec.exec_and_capture(['osascript', '-e', f'id of app "{app_name_or_path}"'])
        return bundle_id

    def quarantine_remove_app(self, app_name: str):
        app_path = self.resolve_app_path(app_name)
        xattrs = self._get_xattrs(app_path)
        if 'com.apple.quarantine' in xattrs:
            self.exec.exec(['xattr', '-dr', 'com.apple.quarantine', app_path])

    def _get_xattrs(self, path: str):
        assert os.path.exists(path)
        rc, stdout = self.exec.exec_and_capture(['xattr', path])
        return stdout.splitlines()

    def get_mac_version_str(self):
        return platform.mac_ver()[0]

    def get_mac_version(self):
        """
        Return current macos version as a three-int tuple.
        """
        tup = platform.mac_ver()[0].split('.')
        tup = list(map(util.str_to_int_or_zero, tup))
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
        rc, text = self.exec.exec_and_capture(['sysadminctl', '-screenLock', 'status'], stderr=subprocess.STDOUT)
        if 'screenLock is off' not in text:
            self.exec.exec(['sysadminctl', '-screenLock', 'off', '-password', password if password else '-'])

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
        bn = util.app_name_to_base_name_without_ext(app_path)
        cur_items = self.login_items_list()
        if bn not in cur_items:
            self._login_items_add_impl(app_path)

    def login_items_list(self):
        """
        Return current list of login items in form of ['Dropbox', 'TopNotch'].
        No full paths or uniq ids.
        """
        rc, out = self.exec.exec_osa_script('''tell application "System Events" to get the name of every login item''',
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
        self.exec.exec_osa_script(text)
