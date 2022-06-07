#!/bin/bash

. env/bin/activate
python -m build
python -m twine upload --repository testpypi dist/*
