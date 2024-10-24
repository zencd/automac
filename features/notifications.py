import logging
import os
import plistlib

import util


class Notifications:
    flags_base = 8396814  # macos 13.7 defaults: notifications off, badges, sounds, banners

    def __init__(self, app):
        from automac import AutoMac
        app: AutoMac = app
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
        return self

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
                            self.app.exec.exec(['/usr/libexec/PlistBuddy', '-c', buddy_cmd, plist_file])
                            self.do_reload_configs = True
                    return True
            return False

        def add_new_ncpref_record():
            flags = self.flags_base | FLAG_NOTIFICATIONS_ENABLED if enable else self.flags_base
            new_entry_xml = f'<dict><key>auth</key><integer>7</integer><key>bundle-id</key><string>{bundle_id}</string><key>content_visibility</key><integer>0</integer><key>flags</key><integer>{flags}</integer><key>grouping</key><integer>0</integer><key>path</key><string>{app_path}</string><key>src</key><array></array></dict>'
            self.app.exec.exec(['defaults', 'write', 'com.apple.ncprefs.plist', 'apps', '-array-add', new_entry_xml])
            self.do_reload_configs = True

        FLAG_NOTIFICATIONS_ENABLED = 1 << 25
        plist_file = f'/Users/{util.get_login()}/Library/Preferences/com.apple.ncprefs.plist'
        assert os.path.exists(plist_file)
        rc, cur_xml_text = self.app.exec.exec_and_capture(['defaults', 'export', plist_file, '-'])
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

        app_path = self.app.apps.find_app_path(app_name)
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
