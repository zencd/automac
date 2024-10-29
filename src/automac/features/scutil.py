class Scutil:

    def __init__(self, app):
        from automac import AutoMac
        app: AutoMac = app
        self.app = app

    def write_if_needed(self, key: str, value: str):
        # XXX scutil exits with a non-zero code if setting missing
        rc, old_value = self.app.exec.exec_and_capture(['scutil', '--get', key], check=False)
        if rc == 0 and old_value == value:
            # print(f'Already done: scutil {key} {value}')
            pass
        else:
            self.app.exec.sudo(['scutil', '--set', key, value])
