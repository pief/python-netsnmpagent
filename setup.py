#!/usr/bin/env python
#
# python-netsnmpagent module
# Copyright (c) 2013 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Public License (GPL) version 3
#
# Distutils setup script
#

from distutils.core import setup

try:
	import ctypes
except:
	print("netsnmpagent requires the ctypes Python module!")
	import sys
	sys.exit(1)

setup(
	name				= "netsnmpagent",
	version				= "0.2",
	description			= "Facilitates writing Net-SNMP (AgentX) subagents in Python",
	long_description	= """
python-netsnmpagent is a Python module that facilitates writing Net-SNMP
subagents in Python. Subagents connect to a locally running Master agent
(snmpd) over a Unix domain socket (eg. "/var/run/agentx/master") and using the
AgentX protocol (RFC2747). They implement custom Management Information Base
(MIB) modules that extend the local node's MIB tree. Usually, this requires
writing a MIB as well, ie. a text file that specifies the structure, names
and data types of the information within the MIB module.""",
	author				= "Pieter Hollants",
	author_email		= "pieter@hollants.com",
	py_modules			= [ "netsnmpagent", "netsnmpapi" ],
	license				= "GPL-3.0",
)
