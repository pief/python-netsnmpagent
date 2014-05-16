#!/usr/bin/env python
# encoding: utf-8
#
# python-netsnmpagent module
# Copyright (c) 2013 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Public License (GPL) version 3
#
# Integration tests for the netsnmpagent module (SNMP objects)
#

import sys, os, re, subprocess, threading, signal, time
from nose.tools import *
sys.path.insert(1, "..")
from netsnmptestenv import netsnmpTestEnv
import netsnmpagent

def setUp(self):
	global testenv, agent

	testenv = netsnmpTestEnv()

	# Create a new netsnmpAgent instance which
	# - connects to the net-snmp test environment's snmpd instance
	# - uses its statedir
	# - loads the TEST-MIB from our tests directory
	testMIBPath = os.path.abspath(os.path.dirname(__file__)) + \
				  "/TEST-MIB.txt"
	agent = netsnmpagent.netsnmpAgent(
		AgentName      = "netsnmpAgentTestAgent",
		MasterSocket   = testenv.mastersocket,
		PersistenceDir = testenv.statedir,
		MIBFiles       = [ testMIBPath ],
	)

	# Test OIDs for Unsigned32 scalar type
	agent.Unsigned32(
		oidstr = "TEST-MIB::testUnsigned32NoInitval",
	)

	agent.Unsigned32(
		oidstr  = "TEST-MIB::testUnsigned32ZeroInitval",
		initval = 0,
	)

	agent.Unsigned32(
		oidstr  = "TEST-MIB::testUnsigned32MinusOneInitval",
		initval = -1,
	)

	agent.Unsigned32(
		oidstr  = "TEST-MIB::testUnsigned32MaxInitval",
		initval = 4294967295,
	)

	agent.Unsigned32(
		oidstr   = "TEST-MIB::testUnsigned32ReadOnly",
		writable = False,
	)

	# Connect to master snmpd instance
	agent.start()

	# Create a separate thread to implement the absolutely most
	# minimalistic possible agent doing nothing but request handling
	agent.loop = True
	def RequestHandler():
		while self.agent.loop:
			agent.check_and_process(False)

	agent.thread = threading.Thread(target=RequestHandler)
	agent.thread.daemon = True
	agent.thread.start()

def tearDown(self):
	global testenv, agent

	if "agent" in globals():
		agent.loop = False
		if hasattr(agent, "thread"):
			agent.thread.join()
		agent.shutdown()

	if "testenv" in globals():
		testenv.shutdown()

@timed(1)
def test_Unsigned32_NoInitval_GETs_Zero():
	""" Unsigned32 without initval GETs zero """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testUnsigned32NoInitval.0")
	eq_(int(data), 0)

@timed(1)
def test_Unsigned32_NoInitval_SET_to_42():
	""" Unsigned32 without initval SET to 42 """

	global testenv

	print testenv.snmpset("TEST-MIB::testUnsigned32NoInitval.0", 42, "u")

@timed(1)
def test_Unsigned32_NoInitval_GETs_42():
	""" Unsigned32 without initval GETs 42 """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testUnsigned32NoInitval.0")
	eq_(int(data), 42)

@timed(1)
def test_Unsigned32_ZeroInitval_GETs_Zero():
	""" Unsigned32 with zero initval GETs zero """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testUnsigned32ZeroInitval.0")
	eq_(int(data), 0)

@timed(1)
def test_Unsigned32_MinusOneInitval_GETs_MaxVal():
	""" Unsigned32 with minus one initval GETs max. value """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testUnsigned32MinusOneInitval.0")
	eq_(int(data), 4294967295)

@timed(1)
def test_Unsigned32_MaxInitval_GETs_Max():
	""" Unsigned32 with max initval GETs max. value """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testUnsigned32MaxInitval.0")
	eq_(int(data), 4294967295)

@timed(1)
def test_Unsigned32_ReadOnly_GETs_Zero():
	""" Read-only Unsigned32 GETs zero """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testUnsigned32ReadOnly.0")
	eq_(int(data), 0)

@timed(1)
@raises(netsnmpTestEnv.NotWritableError)
def test_Unsigned32_ReadOnly_SET_raises_Exception():
	""" Read-only Unsigned32 SET raises Exception """

	global testenv

	testenv.snmpset("TEST-MIB::testUnsigned32ReadOnly.0", 42, "u")
