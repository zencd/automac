import logging


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
