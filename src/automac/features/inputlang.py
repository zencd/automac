"""
A list of known non-keyboard methods, sometimes one of them presented, sometimes two:
<dict><key>Bundle ID</key><string>com.apple.CharacterPaletteIM</string><key>InputSourceKind</key><string>Non Keyboard Input Method</string></dict>
<dict><key>Bundle ID</key><string>com.apple.PressAndHold</string><key>InputSourceKind</key><string>Non Keyboard Input Method</string></dict>
"""

class InputLang:
    def to_plist_xml_str(self):
        raise Exception(f'not overridden for {type(self)}')

    def get_code(self):
        return -1

class KeyboardLang(InputLang):
    def __init__(self, code: int, name: str):
        self.code = code
        self.name = name

    def get_code(self):
        return self.code

    def to_plist_xml_str(self):
        return f'<dict><key>InputSourceKind</key><string>Keyboard Layout</string><key>KeyboardLayout ID</key><integer>{self.code}</integer><key>KeyboardLayout Name</key><string>{self.name}</string></dict>'

class NonKeyboardInputMethod(InputLang):
    def __init__(self, bundle_id: str):
        self.bundle_id = bundle_id

    def to_plist_xml_str(self):
        return f'<dict><key>Bundle ID</key><string>{self.bundle_id}</string><key>InputSourceKind</key><string>Non Keyboard Input Method</string></dict>'


class InputLangs:
    EN_US = KeyboardLang(0, 'U.S.')
    EN_GB = KeyboardLang(2, 'British')
    EN_ABC = KeyboardLang(252, 'ABC')
    RU_PC = KeyboardLang(19458, 'RussianWin')

    PRESS_AND_HOLD = NonKeyboardInputMethod('com.apple.PressAndHold')
    CHARACTER_PALETTE_IM = NonKeyboardInputMethod('com.apple.CharacterPaletteIM')
