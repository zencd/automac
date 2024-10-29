#!/usr/bin/env bash

# prepare current venv for this package development
# execute it once per venv

# preconditions
script_dir=$(dirname -- "$(readlink -f -- "$0")")
[ ! "$script_dir" -ef '.' ] && echo "Run $(basename "$0") from $script_dir" && exit 1
[ -z "$VIRTUAL_ENV" ] && echo "Run $(basename "$0") within a virtual environment" && exit 1

set -e

# preventing warnings
(set -x; pip install --upgrade pip)

# only used to build xxx.tar.gz artifacts
(set -x; pip install build)

# install requirements for setup.py
(set -x; pip install setuptools)

# install requirements for development; picking them from setup.py
stdout=$(python setup.py print-dev-requirements)
echo "$stdout" | while IFS= read -r line; do
  (set -x; pip install "$line")
done

# install the package we are developing into the current virtual environment
# thus it can be imported in any python file by its absolute name
# performing "editable install", -e, so any changes in the package will be reflected without the need to reinstall it
(set -x; pip install -e .)
