class Iterm2:
    DOMAIN = 'com.googlecode.iterm2'

    def __init__(self, app):
        from automac import AutoMac
        app: AutoMac = app
        self.app = app

    def quit_silently(self):
        """iTerm2: Don't display the annoying prompt when quitting."""
        self.app.defaults.write(self.DOMAIN, 'PromptOnQuit', False)  # confirm quit iterm2
        self.app.defaults.write(self.DOMAIN, 'OnlyWhenMoreTabs', False)  # confirm closing multiple sessions
        return self

    def quit_when_all_windows_closed(self):
        self.app.defaults.write(self.DOMAIN, 'QuitWhenAllWindowsClosed', True)
        return self

    def update_disable(self):
        # todo these settings are the same for a bunch of apps: need to generalize this
        self.app.defaults.write(self.DOMAIN, 'SUAutomaticallyUpdate', False)
        self.app.defaults.write(self.DOMAIN, 'SUEnableAutomaticChecks', False)
        return self

    def analytics_off(self):
        self.app.defaults.write(self.DOMAIN, 'SUSendProfileInfo', False)
        return self
