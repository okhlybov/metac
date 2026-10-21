#!/bin/sh
set -e
venv=.venv
$venv/bin/python -m build
$venv/bin/python -m twine check dist/*
$venv/bin/python -m twine upload --repository testpypi dist/*
#