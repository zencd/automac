# automac

A terminal program that tunes your macos settings to a wanted state in one step.

## It can

- install command-line programs
- install GUI programs
- create necessary folders, symbolic links
- change macos settings: dock, finder, locale, input languages, computer name, etc
- manage file associations
- manage an app's notifications
- remove an app from quarantine

## It cannot

- manage an app's access to Desktop or Downloads
- manage an app's access to mic, camera
- looks like it's only macos itself who can rule it

## Usage

```
curl -O 'https://raw.githubusercontent.com/zencd/automac/refs/heads/master/automac.py'
python3 your-scenario.py
```