# automac

A utility that tunes macos settings to a wanted state in one step.

## It can

- install command-line programs
- install GUI programs
- create necessary folders, symbolic links
- change a variety of macos settings: dock, finder, menu bar, locale, input languages, computer name, etc
- manage file associations
- manage an app's notifications
- remove an app from quarantine

## It can't

- manage an app's access to Desktop or Downloads
- manage an app's access to mic, camera
- looks like it's only macos itself who can rule it

## Principles

- this program applies changes if only they are necessary
- thus repeated execution of the program won't alter OS
- IDE's autocompletion and python docstrings is the reference
- thus you'd better edit your preferences file in PyCharm or VS Code
- your preferences file is just a Python script

## Usage

- `cd a-folder-with-your-prefs`
- edit `your-prefs.py`
- `curl -O 'https://raw.githubusercontent.com/zencd/automac/refs/heads/master/automac.py'`
- `python3 your-prefs.py`
