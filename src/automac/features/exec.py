import logging
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Union


class Exec:

    def __init__(self, app):
        from automac import AutoMac
        app: AutoMac = app
        self.app = app

    def exec_and_capture(self, cmd: list, check=True, shell=False, charset='utf-8', stderr=subprocess.PIPE, log=False):
        cmd_str = shlex.join(cmd)
        if log:
            logging.info(f'EXEC: {cmd_str}')
        p = subprocess.Popen(cmd, stderr=stderr, stdout=subprocess.PIPE, shell=shell)
        stdout, stderr = p.communicate()
        if check and p.returncode != 0:
            self.app.abort(f'Shell command failed: {cmd_str} - exit code {p.returncode}')
        return p.returncode, stdout.decode(charset).strip()

    def exec_interactive(self, cmd: Union[str, list], check=True, stdout=None, stderr=None, log=True):
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
            self.app.abort(f'Shell command failed: {cmd_str} - exit code {p.returncode}')
        return p.returncode

    def exec(self, cmd: Union[str, list], check=True, log=True):
        return self.exec_interactive(cmd, check=check, log=log)

    def sudo(self, cmd: Union[str, list], check=True, charset='utf-8'):
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        cmd_list = ['sudo', '-S', '--'] + cmd
        cmd_str = shlex.join(cmd_list)
        logging.info(f'Exec: {cmd_str}')
        p = subprocess.Popen(cmd_list, stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if p.returncode != 0 and check:
            self.app.abort(f'Last command exited with code {p.returncode}')
        return stdout.decode(charset).rstrip()

    def exec_script_file(self, shell_script_file, shell='bash'):
        shell_script_file = self.app.resolve_file(shell_script_file)
        self.exec([shell, str(shell_script_file)])

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

