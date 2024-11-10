#!/usr/bin/env bash

# prepare current venv for this package development
# execute it once per venv

# preconditions
[ -z "$VIRTUAL_ENV" ] && echo "Run $(basename "$0") within a virtual environment" && exit 1
cd -- "$(dirname -- "$(readlink -f -- "$0")")" || exit 1

set -xe

# prevent warnings
pip install --upgrade pip

# only used to build tar.gz artifacts (sdist)
pip install build

# install requirements for setup.py
# seems not really useful but otherwise you will see unresolved symbols in setup.py in IDE
pip install setuptools

# install package `mypak` (which we are developing) into the current virtual environment
# thus we will be able to do `import mypak` in any python file within the project
# performing "editable install", -e, so any changes in the package will be reflected without the need to reinstall it
# '.[dev]' will install `mypak` plus all `dev` dependencies defined in setup.py; see `extras_require` there
# '.' will install only `mypak`; we are not using that
pip install -e '.[dev]'
