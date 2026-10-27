#!/bin/sh
set -e
[[ -z "$1" ]] && echo "repository must be specified" && exit 1
venv=.venv
$venv/bin/pip install twine build --upgrade
$venv/bin/python -m build; rm -rf src/*.egg-info
$venv/bin/python -m twine check dist/*
$venv/bin/python -m twine upload --repository $1 dist/*
#