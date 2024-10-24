class AppCleaner:
    DOMAIN = 'net.freemacsoft.AppCleaner'

    def __init__(self, app: 'AutoMac'):
        self.app = app

    def update_disable(self):
        self.app.defaults.write(self.DOMAIN, 'SUAutomaticallyUpdate', False)
        self.app.defaults.write(self.DOMAIN, 'SUEnableAutomaticChecks', False)
        return self

    def mark_as_launched_before(self):
        self.app.defaults.write(self.DOMAIN, 'SUHasLaunchedBefore', True)
        return self

    def analytics_off(self):
        self.app.defaults.write(self.DOMAIN, 'SUSendProfileInfo', False)
        return self
