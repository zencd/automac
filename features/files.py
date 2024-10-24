import os
import stat
from pathlib import Path


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
