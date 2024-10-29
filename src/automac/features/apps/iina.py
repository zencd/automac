class Iina:
    DOMAIN = 'com.colliderli.iina'

    def __init__(self, app):
        from automac import AutoMac
        app: AutoMac = app
        self.app = app

    def quit_when_all_windows_closed(self):
        self.app.defaults.write(self.DOMAIN, 'quitWhenNoOpenedWindow', True)
        return self

    def single_window(self):
        self.app.defaults.write(self.DOMAIN, 'alwaysOpenInNewWindow', False)
        return self
