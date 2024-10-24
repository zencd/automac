class System:

    def __init__(self, app):
        from automac import AutoMac
        app: AutoMac = app
        self.app = app

    def current_timezone(self):
        rc, path = self.app.exec.exec_and_capture(['readlink', '/etc/localtime'])
        # path is like '/var/db/timezone/zoneinfo/Europe/Moscow'
        return path.replace('/var/db/timezone/zoneinfo/', '')
