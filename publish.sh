#!/bin/sh
set -e
[[ -z "$1" ]] && echo "repository must be specified" && exit 1
venv=.venv
$venv/bin/python -m build
$venv/bin/python -m twine check dist/*
$venv/bin/python -m twine upload --repository $1 dist/*
#