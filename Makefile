#
# python-netsnmpagent module
# Copyright (c) 2012 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Public License (GPL) version 3
#
# Convenience Makefile
#

all: help

help:
	@echo
	@echo "                        python-netsnmpagent Module"
	@echo "         Copyright (c) 2012 Pieter Hollants <pieter@hollants.com>"
	@echo
	@echo "Targets:"
	@echo " install    - Install locally"
	@echo " srcdist    - Create source distribution archive in .tar.gz format"
	@echo " upload     - Upload source distribution archive to PyPI"
	@echo " clean      - Clean up"
	@echo

install:
	python setup.py install

dist:
	python setup.py sdist

upload:
	python setup.py sdist upload

clean:
	python setup.py clean
	@[ -e "*.pyc" ] && rm *.pyc || true
	@[ -e build ] && rm -rf build || true
	@[ -e dist ] && rm -rf dist || true
