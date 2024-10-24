import os
import subprocess


class Apps:
    def __init__(self, app):
        from automac import AutoMac
        app: AutoMac = app
        self.app = app

    def is_app_running(self, app_base_name):
        """
        :param app_base_name: like 'Sublime Text'
        :return:
        """
        # todo pgrep matches not only 'TopNotch' but 'TopNot' too
        rc = self.app.exec.exec_interactive(['pgrep', app_base_name], check=False, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            log=False)
        return rc == 0

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

    def remove_app_from_quarantine(self, app_name: str):
        app_path = self.app.apps.resolve_app_path(app_name)
        xattrs = self.app.get_xattrs(app_path)
        if 'com.apple.quarantine' in xattrs:
            self.app.exec.exec(['xattr', '-dr', 'com.apple.quarantine', app_path])
