# automac

A utility that configures macos to a wanted state in one step.
You write configurations in Python.

## Status

I use `automac` to configure my personal MBP M1 Pro, and in virtual machines for tests.
See below the list of macos releases where it's known to work.

## It can

- install command-line programs
- install GUI programs
- install homebrew
- create necessary folders, symbolic links
- change a variety of macos settings: dock, finder, menu bar, locale, input languages, computer name, etc
- associate file extensions with apps
- manage notifications for apps
- remove a freshly installed app from quarantine
- make an app to open automatically when you log in to Mac

## Principles and Pro's

- `automac` applies changes if only they are necessary
- thus repeated execution of the program won't alter OS
- and the number of sudo password prompts is reduced to the minimum
- you write desired settings as an ordinary Python file
- IDE's autocompletion and python docstrings will help

## Usage

#### 1. Authoring your configuration script

```bash
# Assuming Python 3 is installed already.
pip3 install --no-cache-dir 'https://github.com/zencd/automac/archive/v1.zip'
# Edit myconf.py in an IDE like PyCharm or VS Code.
python3 myconf.py
````

#### 2. Configuring a freshly installed macos

```bash
cd a-folder-with-your-config
curl -LO 'https://raw.githubusercontent.com/zencd/automac/refs/heads/v1/automac.sh'
bash automac.sh myconf.py
# Typically you will need to logoff or restart for the changes to take effect.
# Some security confirmations GUI may pop up during the process.
# You may be asked for the sudo password also.
```

## Example configuration

```python
# File `myconf.py`
from automac import AutoMac
with AutoMac() as mac:
    mac = mac  # type: AutoMac # pycharm is sad
    mac.add_lookup_folder('~/Dropbox/config/macos')
    mac.mkdir('~/bin')
    mac.trackpad_tap_to_click()
```

## A broader example

[example-basic.py](example-basic.py)

## Requirements

- MacOS 13 Ventura, 14 Sonoma or 15 Sequoia.
  Sequoia is the latest one at the moment of writing.
  Earlier releases not tested yet.
- Hardware: Apple Silicon (tested) or intel (not checked yet).
- Python 3. To be installed automatically if missing on a fresh macOS.
- Apple's command line tools.
  - To be installed automatically if missing on a fresh macOS.
  - Bad: they grow the tools every year, now hitting 850 MB of traffic.
  - Good: if you are using Homebrew (who wouldn't), it's a requirement anyway.

## What it can't

- manage an app's access to Desktop or Downloads
- manage an app's access to mic, camera
- looks like it's only macos itself who can rule it

## Todo

- test on intel arch (brew prefix differs)
