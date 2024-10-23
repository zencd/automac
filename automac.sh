#!/usr/bin/env bash

# Apply an automac config to macOS.
# Usable on a freshly installed OS mainly.
# NB some pythons, like homebrew's one, doesn't allow installing a package into the main python, so using a venv here

function ensure_cli_tools_installed() {
  # install xcode cli tools via terminal
  # try the gui installer if failed
  # original hack: https://github.com/Homebrew/install/blob/master/install.sh
  # objection: python is not available at macos by default
  if xcode-select -p 1>/dev/null 2>&1; then
    return
  fi
  installed=0
  tmp_file=/tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
  touch "$tmp_file"
  label=$(softwareupdate -l | grep -B 1 -E 'Command Line Tools' | awk -F'*' '/^ *\\*/ {print $2}' | sed -e 's/^ *Label: //' -e 's/^ *//' | sort -V | tail -n1)
  # $label is like 'Command Line Tools for Xcode-16.0'
  if [ -n "$label" ]; then
    (set -x; softwareupdate -i "$label")
    installed=1
  fi
  rm -f "$tmp_file"
  if [ "$installed" = "0" ]; then
    (set -x; xcode-select --install)
  fi
}

if [ $# = 0 ]; then
  echo "Apply an automac config to macOS"
  echo "Usage: $0 <config-file.py>"
  exit 1
fi

distr_url=https://github.com/zencd/automac/archive/v1.zip
venv=automac-venv
conf_py=$1
ensure_cli_tools_installed
[ -d automac-venv ] || (set -x; python3 -m venv $venv)
if ! $venv/bin/python3 -c 'import automac' 2>/dev/null; then
  (set -x; $venv/bin/python3 -m pip install --no-cache-dir "$distr_url")
fi
(set -x; $venv/bin/python3 "$conf_py")
