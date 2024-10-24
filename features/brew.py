import logging
import os
import re
import subprocess

import util


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
        lines = util.read_file_lines(list_file)
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
        lines = util.read_file_lines(list_file)
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
