#
# python-netsnmpagent module
# Copyright (c) 2012 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Public License (GPL) version 3
#
# Convenience Makefile
#

VERSION := $(shell sed -n '/version.*=/ {s/^.*= *"//;s/",//;p}' setup.py)

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
	@echo " rpms       - Build RPMs for the current distribution"
	@echo " clean      - Clean up"
	@echo

install:
	python setup.py install

srcdist:
	python setup.py sdist

upload:
	python setup.py sdist upload

rpms: srcdist
	@mkdir -p dist/RPMBUILD/{BUILDROOT,RPMS,SOURCES,SPECS,SRPMS} || exit 1
	@cp -a python-netsnmpagent.spec dist/RPMBUILD/SPECS/ || exit 1
	@cp -a dist/netsnmpagent-$(VERSION).tar.gz dist/RPMBUILD/SOURCES/ || exit 1
	@cd dist/RPMBUILD && \
	rpmbuild \
		--define "%_topdir $$(pwd)" \
		--define "netsnmpagent_version $(VERSION)" \
		-ba SPECS/python-netsnmpagent.spec

clean:
	python setup.py clean
	@[ -e "*.pyc" ] && rm *.pyc || true
	@[ -e build ] && rm -rf build || true
	@[ -e dist ] && rm -rf dist || true
