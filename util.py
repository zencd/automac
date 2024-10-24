import getpass
import os
import platform
import re


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


def get_os_name():
    s = platform.system()
    return {'Darwin': 'macOS'}.get(s) or s
