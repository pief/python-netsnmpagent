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
	global testenv, agent, settableInteger32, settableUnsigned32

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

	# Test OIDs for Integer32 scalar type
	settableInteger32 = agent.Integer32(
		oidstr = "TEST-MIB::testInteger32NoInitval",
	)

	agent.Integer32(
		oidstr  = "TEST-MIB::testInteger32ZeroInitval",
		initval = 0,
	)

	agent.Integer32(
		oidstr  = "TEST-MIB::testInteger32MinusOneInitval",
		initval = -1,
	)

	agent.Integer32(
		oidstr  = "TEST-MIB::testInteger32MinInitval",
		initval = -2147483648,
	)

	agent.Integer32(
		oidstr  = "TEST-MIB::testInteger32MinMinusOneInitval",
		initval = -2147483649,
	)

	agent.Integer32(
		oidstr  = "TEST-MIB::testInteger32OneInitval",
		initval = 1,
	)

	agent.Integer32(
		oidstr  = "TEST-MIB::testInteger32MaxInitval",
		initval = 2147483647,
	)

	agent.Integer32(
		oidstr  = "TEST-MIB::testInteger32MaxPlusOneInitval",
		initval = 2147483648,
	)

	agent.Integer32(
		oidstr   = "TEST-MIB::testInteger32ReadOnly",
		writable = False,
	)

	# Test OIDs for Unsigned32 scalar type
	settableUnsigned32 = agent.Unsigned32(
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
		oidstr  = "TEST-MIB::testUnsigned32OneInitval",
		initval = 1,
	)

	agent.Unsigned32(
		oidstr  = "TEST-MIB::testUnsigned32MaxInitval",
		initval = 4294967295,
	)

	agent.Unsigned32(
		oidstr  = "TEST-MIB::testUnsigned32MaxPlusOneInitval",
		initval = 4294967296,
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
def test_GET_Integer32WithoutInitval_eq_Zero():
	""" GET(Integer32()) == 0

	This tests that the instantiation of an Integer32 SNMP object without
	specifying an initval resulted in a snmpget'able scalar variable of type
	INTEGER and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testInteger32NoInitval.0")
	eq_(datatype, "INTEGER")
	eq_(int(data), 0)

@timed(1)
def test_GET_Integer32ZeroInitval_eq_Zero():
	""" GET(Integer32(initval=0)) == 0

	This tests that the instantiation of an Integer32 SNMP object with an
	initval of 0 resulted in a snmpget'able scalar variable of type INTEGER
	and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testInteger32ZeroInitval.0")
	eq_(datatype, "INTEGER")
	eq_(int(data), 0)

@timed(1)
def test_GET_Integer32MinusOneInitval_eq_MinusOne():
	""" GET(Integer32(initval=-1)) == -1

	This tests that the instantiation of an Integer32 SNMP object with an
	initval of -1 resulted in a snmpget'able scalar variable of type INTEGER
	and value -1. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testInteger32MinusOneInitval.0")
	eq_(datatype, "INTEGER")
	eq_(int(data), -1)

@timed(1)
def test_GET_Integer32MinInitval_eq_Min():
	""" GET(Integer32(initval=-2147483648)) == -2147483648

	This tests that the instantiation of an Integer32 SNMP object with an
	initval of -2147483648 resulted in a snmpget'able scalar variable of type
	INTEGER and value -2147483648. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testInteger32MinInitval.0")
	eq_(datatype, "INTEGER")
	eq_(int(data), -2147483648)

@timed(1)
def test_GET_Integer32MinMinusOneInitval_eq_MaxMinusOne():
	""" GET(Integer32(initval=-2147483649)) == 2147483647

	This tests that the instantiation of an Integer32 SNMP object with an
	initval of -2147483649 resulted in a snmpget'able scalar variable of type
	INTEGER and value 2147483647. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testInteger32MinMinusOneInitval.0")
	eq_(datatype, "INTEGER")
	eq_(int(data), 2147483647)

@timed(1)
def test_GET_Integer32OneInitval_eq_One():
	""" GET(Integer32(initval=1)) == 1

	This tests that the instantiation of an Integer32 SNMP object with an
	initval of 1 resulted in a snmpget'able scalar variable of type INTEGER
	and value 1. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testInteger32OneInitval.0")
	eq_(datatype, "INTEGER")
	eq_(int(data), 1)

@timed(1)
def test_GET_Integer32MaxInitval_eq_Max():
	""" GET(Integer32(initval=2147483647)) == 2147483647

	This tests that the instantiation of an Integer32 SNMP object with an
	initval of 2147483647 resulted in a snmpget'able scalar variable of type
	INTEGER and value 2147483647. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testInteger32MaxInitval.0")
	eq_(datatype, "INTEGER")
	eq_(int(data), 2147483647)

@timed(1)
def test_GET_Integer32MaxPlusOneInitval_eq_Min():
	""" GET(Integer32(initval=2147483648)) == -2147483648

	This tests that the instantiation of an Integer32 SNMP object with an
	initval of 2147483648 resulted in a snmpget'able scalar variable of type
	INTEGER and value -2147483648. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testInteger32MaxPlusOneInitval.0")
	eq_(datatype, "INTEGER")
	eq_(int(data), -2147483648)

@timed(1)
def test_SET_Integer32_42_eq_42():
	""" SET(Integer32(), 42) == 42

	This tests that calling snmpset on a previously instantiated scalar
	variable of type INTEGER and value 0 (this was confirmed by an earlier
	test) with the new value 42 results in the netsnmpagent SNMP object
	returning 42 as its value, too. """

	global testenv, settableInteger32

	print testenv.snmpset("TEST-MIB::testInteger32NoInitval.0", 42, "i")

	eq_(settableInteger32.value(), 42)

@timed(1)
def test_GET_SET_Integer32_42_eq_42():
	""" GET(SET(Integer32(), 42)) == 42

	This tests that calling snmpget on the previously instantiated scalar
	variable of type INTEGER that has just been set to 42 also returns this
	new variable when accessed through snmpget. """

	(data, datatype) = testenv.snmpget("TEST-MIB::testInteger32NoInitval.0")
	eq_(datatype, "INTEGER")
	eq_(int(data), 42)

@timed(1)
@raises(netsnmpTestEnv.NotWritableError)
def test_SET_Integer32ReadOnly_42_raises_Exception():
	""" SET(Integer32(readonly=True) raises Exception

	This tests that calling snmpset on a previously instantiated scalar
	variable of type INTEGER that has the readonly property set triggers
	a NotWriteableError exception. """

	global testenv

	testenv.snmpset("TEST-MIB::testInteger32ReadOnly.0", 42, "i")

@timed(1)
def test_GET_Unsigned32WithoutInitval_eq_Zero():
	""" GET(Unsigned32()) == 0

	This tests that the instantiation of an Unsigned32 SNMP object without
	specifying an initval resulted in a snmpget'able scalar variable of type
	Gauge32 and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testUnsigned32NoInitval.0")
	eq_(datatype, "Gauge32")
	eq_(int(data), 0)

@timed(1)
def test_GET_Unsigned32ZeroInitval_eq_Zero():
	""" GET(Unsigned32(initval=0)) == 0

	This tests that the instantiation of an Unsigned32 SNMP object with an
	initval of 0 resulted in a snmpget'able scalar variable of type Gauge32
	and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testUnsigned32ZeroInitval.0")
	eq_(datatype, "Gauge32")
	eq_(int(data), 0)

@timed(1)
def test_GET_Unsigned32MinusOneInitval_eq_Max():
	""" GET(Unsigned32(initval=-1)) == 4294967295

	This tests that the instantiation of an Unsigned32 SNMP object with an
	initval of -1 resulted in a snmpget'able scalar variable of type Gauge32
	and value 4294967295. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testUnsigned32MinusOneInitval.0")
	eq_(datatype, "Gauge32")
	eq_(int(data), 4294967295)

@timed(1)
def test_GET_Unsigned32OneInitval_eq_One():
	""" GET(Unsigned32(initval=1)) == 1

	This tests that the instantiation of an Unsigned32 SNMP object with an
	initval of 1 resulted in a snmpget'able scalar variable of type Gauge32
	and value 1. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testUnsigned32OneInitval.0")
	eq_(datatype, "Gauge32")
	eq_(int(data), 1)

@timed(1)
def test_GET_Unsigned32MaxInitval_eq_max():
	""" GET(Unsigned32(initval=4294967295)) == 4294967295

	This tests that the instantiation of an Unsigned32 SNMP object with an
	initval of 4294967295 resulted in a snmpget'able scalar variable of type
	Gauge32 and value 4294967295. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testUnsigned32MaxInitval.0")
	eq_(datatype, "Gauge32")
	eq_(int(data), 4294967295)

@timed(1)
def test_GET_Unsigned32MaxPlusOneInitval_eq_zero():
	""" GET(Unsigned32(initval=4294967296)) == 0

	This tests that the instantiation of an Unsigned32 SNMP object with an
	initval of 4294967296 resulted in a snmpget'able scalar variable of type
	Gauge32 and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testUnsigned32MaxPlusOneInitval.0")
	eq_(datatype, "Gauge32")
	eq_(int(data), 0)

@timed(1)
def test_SET_Unsigned32_42_eq_42():
	""" SET(Unsigned32(), 42) == 42

	This tests that calling snmpset on a previously instantiated scalar
	variable of type Gauge32 and value 0 (this was confirmed by an earlier
	test) with the new value 42 results in the netsnmpagent SNMP object
	returning 42 as its value, too. """

	global testenv, settableUnsigned32

	print testenv.snmpset("TEST-MIB::testUnsigned32NoInitval.0", 42, "u")

	eq_(settableUnsigned32.value(), 42)

@timed(1)
def test_GET_SET_Unsigned32_42_eq_42():
	""" GET(SET(Unsigned32(), 42)) == 42

	This tests that calling snmpget on the previously instantiated scalar
	variable of type Gauge32 that has just been set to 42 also returns this
	new variable when accessed through snmpget. """

	(data, datatype) = testenv.snmpget("TEST-MIB::testUnsigned32NoInitval.0")
	eq_(datatype, "Gauge32")
	eq_(int(data), 42)

@timed(1)
@raises(netsnmpTestEnv.NotWritableError)
def test_SET_Unsigned32ReadOnly_42_raises_Exception():
	""" SET(Unsigned32(readonly=True) raises Exception

	This tests that calling snmpset on a previously instantiated scalar
	variable of type Gauge32 that has the readonly property set triggers
	a NotWriteableError exception. """

	global testenv

	testenv.snmpset("TEST-MIB::testUnsigned32ReadOnly.0", 42, "u")
