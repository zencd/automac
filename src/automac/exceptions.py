class AutomacException(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class StopException(AutomacException):
    """Configuration process stopped by a good reason."""

    def __init__(self):
        super().__init__()


class BadAutomacException(AutomacException):
    """Configuration process stopped by an error."""

    def __init__(self, *args):
        super().__init__(*args)

class AbortException(BadAutomacException):
    """Configuration process stopped by an error."""

    def __init__(self, *args):
        super().__init__(*args)
