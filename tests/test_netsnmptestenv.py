#!/usr/bin/env python
# encoding: utf-8
#
# python-netsnmpagent module
# Copyright (c) 2013 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Public License (GPL) version 3
#
# Integration tests for the netsnmptestenv helper module
#

import sys, os, subprocess, re
sys.path.insert(1, "..")
from netsnmptestenv import netsnmpTestEnv
from nose.tools import *

def test_FirstGetFails():
	""" No test environment yet, snmpget fails """

	with assert_raises(netsnmpTestEnv.SNMPTimeoutError):
		netsnmpTestEnv.snmpget("SNMPv2-MIB::snmpSetSerialNo.0")

def test_Instantiation():
	""" Instantiation without exceptions """

	global testenv

	testenv = netsnmpTestEnv()

def test_SecondGetWorks():
	""" test environment set up, snmpget succeeds """

	global testenv

	output = testenv.snmpget("SNMPv2-MIB::snmpSetSerialNo.0")
	m = re.match(r"^SNMPv2-MIB::snmpSetSerialNo.0 = INTEGER: \d+$", output)
	try:
		assert_not_equal(m, None)
	except AssertionError:
		raise AssertionError("'{0}' != ^SNMPv2-MIB::snmpSetSerialNo.0 = INTEGER: \d+$".format(output))

def tearDown(self):
	global testenv

	testenv.shutdown()
