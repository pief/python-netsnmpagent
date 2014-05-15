#!/usr/bin/env python
# encoding: utf-8
#
# python-netsnmpagent module
# Copyright (c) 2013 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Public License (GPL) version 3
#
# Integration tests for the netsnmptestenv helper module
#

import sys, os, time, subprocess, re
from nose.tools import *
sys.path.insert(1, "..")
from netsnmptestenv import netsnmpTestEnv

@timed(3)
@raises(netsnmpTestEnv.SNMPTimeoutError)
def test_FirstGetFails():
	""" No test environment yet, snmpget fails """

	netsnmpTestEnv.snmpget("SNMPv2-MIB::snmpSetSerialNo.0")

@timed(1)
def test_Instantiation():
	""" Instantiation without exceptions and within reasonable time """

	global testenv, pid, tmpdir

	# Try creating the instance without raising exceptions
	testenv = netsnmpTestEnv()

	# Remember the PID file the tmpdir the instance uses
	while not os.path.exists(testenv.pidfile):
		time.sleep(.1)
	with open(testenv.pidfile, "r") as f:
		pid = int(f.read())
	tmpdir = testenv.tmpdir

@timed(1)
def test_SecondGetWorks():
	""" test environment set up, snmpget succeeds """

	global testenv

	output = testenv.snmpget("SNMPv2-MIB::snmpSetSerialNo.0")
	ok_(re.match(r"^SNMPv2-MIB::snmpSetSerialNo.0 = INTEGER: \d+$", output) != None)

@timed(1)
def test_Shutdown():
	""" Shutdown without exceptions and within reasonable time """

	global testenv

	testenv.shutdown()

@timed(3)
@raises(netsnmpTestEnv.SNMPTimeoutError)
def test_ThirdGetFailsAgain():
	""" No more test environment, snmpget fails """

	netsnmpTestEnv.snmpget("SNMPv2-MIB::snmpSetSerialNo.0")

@raises(OSError)
def test_SnmpdNotRunning():
	""" snmpd not running anymore """

	global pid

	os.kill(pid, 0)

def test_TmpdirRemoved():
	""" tmpdir was removed """

	global tmpdir

	# List the tempdir's name and its contents if the assert fails
	print tmpdir
	try:
		print os.listdir(tmpdir)
	except OSError:
		pass
	ok_(os.path.exists(tmpdir) == False)
