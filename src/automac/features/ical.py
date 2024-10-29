class Calculator:
    DOMAIN = 'com.apple.iCal'

    def __init__(self, app):
        from src.automac.__init__ import AutoMac
        app: AutoMac = app
        self.app = app

    def skip_welcome_screen(self):
        """
        Skip "What's new in Calendar" startup screen nowadays and anything similar in the future.
        Tested: macos 14.7.
        """
        # macos 14.7 writes value 4 after that welcome screen passed
        # using a higher value here to make the feature work with the future macos versions
        self.app.defaults.write(self.DOMAIN, 'privacyPaneHasBeenAcknowledgedVersion', 100)
