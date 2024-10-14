#!/usr/bin/env bash

function install_tools_if_needed() {
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

install_tools_if_needed
py_file="$(dirname $0)/automac.py"
(set -x; python3 "$py_file" $*)
