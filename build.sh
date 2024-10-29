set -xe

# build and check the project's release artifacts

# build dist/xxx-0.0.1.tar.gz
python -m build

# build dist/xxx-0.0.1-py3-none-any.whl and do not build wheels for dependencies (sick defaults)
pip wheel . -w dist --no-deps

# verify the artifacts
twine check dist/*
