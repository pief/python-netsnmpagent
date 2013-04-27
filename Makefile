#
# python-netsnmpagent module
# Copyright (c) 2013 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Public License (GPL) version 3
#
# Makefile for Git repository-based builds
#

# The version is derived from the latest git tag set
VERSION := $(shell git describe)

# Some features should be available for proper releases with a x.y.z tag only
ifeq ($(shell echo $(VERSION) | sed 's,^[[:digit:]]\+\.[[:digit:]]\+\(\.[[:digit:]]\+\)\?,,'),)
	TAGGED := 1
else
	VERSION := $(shell echo $(VERSION) | sed 's,-,_next,;s,-,_,')
endif

all: help

help:
	@echo
	@echo "                        python-netsnmpagent Module"
	@echo "         Copyright (c) 2013 Pieter Hollants <pieter@hollants.com>"
	@echo
	@echo "Version from \"git describe\": $(VERSION)"
	@echo
	@echo "Targets:"
	@echo " install    - Install locally"
	@echo " srcdist    - Create source distribution archive in .tar.gz format"
ifeq ($(TAGGED),1)
	@echo " upload     - Upload source distribution archive to PyPI"
endif
	@echo " rpms       - Build RPMs for the current distribution"
	@echo " clean      - Clean up"
	@echo

setup.py: setup.py.in
	sed 's/@NETSNMPAGENT_VERSION@/$(VERSION)/' setup.py.in >setup.py
	chmod u+x setup.py

.PHONY: ChangeLog
ChangeLog:
	@[ -e ChangeLog ] && rm ChangeLog || true
	@CURRENT=`git describe`; \
	set -- `git tag -l | egrep ^[[:digit:]]+.[[:digit:]]+\(.[[:digit:]]+\)?$ | sort -r`; \
	if [ "$$CURRENT" == "$$1" ] ; then shift; fi; \
	until [ -z "$$CURRENT" ] ; do \
		if [ -n "$$1" ] ; then \
			LINE="Changes from v$$1 to v$$CURRENT"; \
			PREV="$$1.."; \
		else \
			LINE="Initial version $$CURRENT"; \
			PREV=""; \
		fi; \
		echo >>ChangeLog; \
		echo $$LINE >>ChangeLog; \
		printf "%*s\n" $${#LINE} | tr ' ' '=' >>ChangeLog; \
		echo >>ChangeLog; \
		git log \
			--no-merges \
			--format="* %ad - %aN <%ae>%n%n%+w(75,2,2)%s%n%+b%n(Git commit %H)%n" \
			$$PREV$$CURRENT >>ChangeLog; \
		CURRENT=$$1; \
		shift || true; \
	done

dist:
	@mkdir dist

dist/python-netsnmpagent.spec: dist python-netsnmpagent.spec.in
	@sed "s/%{netsnmpagent_version}/$(VERSION)/" \
	  python-netsnmpagent.spec.in \
	  >dist/python-netsnmpagent.spec

install: setup.py
	python setup.py install

srcdist: setup.py ChangeLog dist/python-netsnmpagent.spec
	python setup.py sdist
	@echo Created source distribution archive as dist/netsnmpagent-$(VERSION).tar.gz
	@echo A suitable RPM .spec file can be found at dist/python-netsnmpagent.spec

upload: setup.py
ifeq ($(TAGGED),1)
	python setup.py sdist upload
else
	@echo "Upload not available for untagged versions!"
endif

rpms: srcdist
	@mkdir -p dist/RPMBUILD/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS} || exit 1
	@cp -a dist/python-netsnmpagent.spec dist/RPMBUILD/SPECS/ || exit 1
	@cp -a dist/netsnmpagent-$(VERSION).tar.gz dist/RPMBUILD/SOURCES/ || exit 1
	@cd dist/RPMBUILD && \
	rpmbuild \
		--define "%_topdir $$(pwd)" \
		-ba SPECS/python-netsnmpagent.spec

clean:
	@[ -e setup.py ] && (python setup.py clean; rm setup.py) || true
	@[ -e ChangeLog ] && rm ChangeLog || true
	@[ -e "*.pyc" ] && rm *.pyc || true
	@[ -e build ] && rm -rf build || true
	@[ -e dist ] && rm -rf dist || true
