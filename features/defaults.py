import plistlib
import xml.etree.ElementTree as ET
from typing import Union
from xml.etree.ElementTree import Element

import util


class Defaults:
    """
    An interface to the `defaults` utility that manages macos plist files.
    """

    def __init__(self, app):
        from automac import AutoMac
        app: AutoMac = app
        self.app = app

    def read(self, domain: str, key: str):
        cmd = ['defaults', 'read', domain, key]
        rc, value = self.app.exec.exec_and_capture(cmd, check=False)
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
        cmd = util.drop_nones(['defaults', ch, 'read', domain, key])
        rc, old_value = self.app.exec.exec_and_capture(cmd, check=False)
        if rc == 0 and norm(value) == norm(old_value):
            # print(f'Already done: {domain} {key} {type_} {new_value}')
            pass
        else:
            cmd = util.drop_nones(['defaults', ch, 'write', domain, key, type_, str_value(value)])
            if sudo_write:
                self.app.exec.sudo(cmd)
            else:
                self.app.exec.exec(cmd)

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
        rc, cur_xml_text = self.app.exec.exec_and_capture(['defaults', 'export', domain, '-'])
        # todo check rc
        xml = plistlib.loads(cur_xml_text.encode('utf-8'))
        cur_value = xml.get(key)
        if cur_value is None or new_value != cur_value:
            new_value_xml_str = dict_to_plist_xml(new_value)
            self.app.exec.exec(['defaults', 'write', domain, key, new_value_xml_str])

    def delete_key(self, domain: str, key: str):
        """
        Delete a value by the given domain/key if one exists.
        :param domain:
        :param key:
        :return:
        """
        cmd = ['defaults', 'read', domain, key]
        rc, value = self.app.exec.exec_and_capture(cmd, check=False)
        key_exists = rc == 0
        if key_exists:
            self.app.exec.exec(['defaults', 'delete', domain, key])
