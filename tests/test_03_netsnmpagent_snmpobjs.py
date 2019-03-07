#!/usr/bin/env python
# encoding: utf-8
#
# python-netsnmpagent module
# Copyright (c) 2013-2019 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Lesser Public License (LGPL) version 3
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
	global settableInteger32, settableUnsigned32, settableTimeTicks
	global settableOctetString, settableDisplayString

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

	# Test OIDs for Counter32 scalar type
	agent.Counter32(
		oidstr = "TEST-MIB::testCounter32NoInitval",
	)

	agent.Counter32(
		oidstr  = "TEST-MIB::testCounter32ZeroInitval",
		initval = 0,
	)

	agent.Counter32(
		oidstr  = "TEST-MIB::testCounter32MinusOneInitval",
		initval = -1,
	)

	agent.Counter32(
		oidstr  = "TEST-MIB::testCounter32OneInitval",
		initval = 1,
	)

	agent.Counter32(
		oidstr  = "TEST-MIB::testCounter32MaxInitval",
		initval = 4294967295,
	)

	agent.Counter32(
		oidstr  = "TEST-MIB::testCounter32MaxPlusOneInitval",
		initval = 4294967296,
	)

	# Test OIDs for Counter64 scalar type
	agent.Counter64(
		oidstr = "TEST-MIB::testCounter64NoInitval",
	)

	agent.Counter64(
		oidstr  = "TEST-MIB::testCounter64ZeroInitval",
		initval = 0,
	)

	agent.Counter64(
		oidstr  = "TEST-MIB::testCounter64MinusOneInitval",
		initval = -1,
	)

	agent.Counter64(
		oidstr  = "TEST-MIB::testCounter64OneInitval",
		initval = 1,
	)

	agent.Counter64(
		oidstr  = "TEST-MIB::testCounter64MaxInitval",
		initval = 18446744073709551615,
	)

	agent.Counter64(
		oidstr  = "TEST-MIB::testCounter64MaxPlusOneInitval",
		initval = 18446744073709551616,
	)

	# Test OIDs for Gauge32 scalar type
	agent.Gauge32(
		oidstr = "TEST-MIB::testGauge32NoInitval",
	)

	agent.Gauge32(
		oidstr  = "TEST-MIB::testGauge32ZeroInitval",
		initval = 0,
	)

	agent.Gauge32(
		oidstr  = "TEST-MIB::testGauge32MinusOneInitval",
		initval = -1,
	)

	agent.Gauge32(
		oidstr  = "TEST-MIB::testGauge32OneInitval",
		initval = 1,
	)

	agent.Gauge32(
		oidstr  = "TEST-MIB::testGauge32MaxInitval",
		initval = 4294967295,
	)

	agent.Gauge32(
		oidstr  = "TEST-MIB::testGauge32MaxPlusOneInitval",
		initval = 4294967296,
	)

	# Test OIDs for TimeTicks scalar type
	settableTimeTicks = agent.TimeTicks(
		oidstr = "TEST-MIB::testTimeTicksNoInitval",
	)

	agent.TimeTicks(
		oidstr  = "TEST-MIB::testTimeTicksZeroInitval",
		initval = 0,
	)

	agent.TimeTicks(
		oidstr  = "TEST-MIB::testTimeTicksMinusOneInitval",
		initval = -1,
	)

	agent.TimeTicks(
		oidstr  = "TEST-MIB::testTimeTicksOneInitval",
		initval = 1,
	)

	agent.TimeTicks(
		oidstr  = "TEST-MIB::testTimeTicksMaxInitval",
		initval = 4294967295,
	)

	agent.TimeTicks(
		oidstr  = "TEST-MIB::testTimeTicksMaxPlusOneInitval",
		initval = 4294967296,
	)

	agent.TimeTicks(
		oidstr   = "TEST-MIB::testTimeTicksReadOnly",
		writable = False,
	)

	# Test OIDs for IpAddress scalar type
	settableIpAddress = agent.IpAddress(
		oidstr = "TEST-MIB::testIpAddressNoInitval",
	)

	agent.IpAddress(
		oidstr = "TEST-MIB::testIpAddressEmptyInitval",
		initval = ""
	)

	agent.IpAddress(
		oidstr = "TEST-MIB::testIpAddress1234Initval",
		initval = "1.2.3.4"
	)

	# Test OIDs for TruthValue scalar type
	settableTruthValue = agent.TruthValue(
		oidstr = "TEST-MIB::testTruthValueNoInitval",
	)

	agent.TruthValue(
		oidstr  = "TEST-MIB::testTruthValueFalseInitval",
		initval = False,
	)

	agent.TruthValue(
		oidstr  = "TEST-MIB::testTruthValueTrueInitval",
		initval = True,
	)

	# Test OIDs for Float scalar type
	settableFloat = agent.Float(
		oidstr = "TEST-MIB::testFloatNoInitval",
	)

	agent.Float(
		oidstr  = "TEST-MIB::testFloatZeroPointZeroInitval",
		initval = 0.0,
	)

	agent.Float(
		oidstr  = "TEST-MIB::testFloatZeroPointOneInitval",
		initval = 0.1,
	)

	agent.Float(
		oidstr  = "TEST-MIB::testFloatOnePointTwoInitval",
		initval = 1.2,
	)

	agent.Float(
		oidstr  = "TEST-MIB::testFloatMinusZeroPointOneInitval",
		initval = -0.1,
	)

	agent.Float(
		oidstr  = "TEST-MIB::testFloatMinusOnePointTwoInitval",
		initval = -1.2,
	)

	# Test OIDs for OctetString scalar type
	settableOctetString = agent.OctetString(
		oidstr = "TEST-MIB::testOctetStringNoInitval",
	)

	agent.OctetString(
		oidstr  = "TEST-MIB::testOctetStringEmptyInitval",
		initval = "",
	)

	agent.OctetString(
		oidstr  = "TEST-MIB::testOctetStringOneASCIICharInitval",
		initval = "A",
	)

	agent.OctetString(
		oidstr  = "TEST-MIB::testOctetStringOneUTF8CharInitval",
		initval = "Ä",
	)

	agent.OctetString(
		oidstr  = "TEST-MIB::testOctetString255ASCIICharsInitval",
		initval = "A" * 255,
	)

	agent.OctetString(
		oidstr  = "TEST-MIB::testOctetString255UTF8CharsInitval",
		initval = "Ä" * 255,
	)

	agent.OctetString(
		oidstr  = "TEST-MIB::testOctetString256ASCIICharsInitval",
		initval = "A" * 256,
	)

	agent.OctetString(
		oidstr  = "TEST-MIB::testOctetString256UTF8CharsInitval",
		initval = "Ä" * 256,
	)

	# Test OIDs for DisplayString scalar type
	settableDisplayString = agent.DisplayString(
		oidstr = "TEST-MIB::testDisplayStringNoInitval",
	)

	agent.DisplayString(
		oidstr  = "TEST-MIB::testDisplayStringEmptyInitval",
		initval = "",
	)

	agent.DisplayString(
		oidstr  = "TEST-MIB::testDisplayStringOneASCIICharInitval",
		initval = "A",
	)

	agent.DisplayString(
		oidstr  = "TEST-MIB::testDisplayString255ASCIICharsInitval",
		initval = "A" * 255,
	)

	agent.DisplayString(
		oidstr  = "TEST-MIB::testDisplayString256ASCIICharsInitval",
		initval = "A" * 256,
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

	print(testenv.snmpset("TEST-MIB::testInteger32NoInitval.0", 42, "i"))

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

	print(testenv.snmpset("TEST-MIB::testUnsigned32NoInitval.0", 42, "u"))

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

@timed(1)
def test_GET_Counter32WithoutInitval_eq_Zero():
	""" GET(Counter32()) == 0

	This tests that the instantiation of a Counter32 SNMP object without
	specifying an initval resulted in a snmpget'able scalar variable of type
	Counter32 and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testCounter32NoInitval.0")
	eq_(datatype, "Counter32")
	eq_(int(data), 0)

@timed(1)
def test_GET_Counter32ZeroInitval_eq_Zero():
	""" GET(Counter32(initval=0)) == 0

	This tests that the instantiation of a Counter32 SNMP object with an
	initval of 0 resulted in a snmpget'able scalar variable of type Counter32
	and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testCounter32ZeroInitval.0")
	eq_(datatype, "Counter32")
	eq_(int(data), 0)

@timed(1)
def test_GET_Counter32MinusOneInitval_eq_Max():
	""" GET(Counter32(initval=-1)) == 4294967295

	This tests that the instantiation of a Counter32 SNMP object with an
	initval of -1 resulted in a snmpget'able scalar variable of type Counter32
	and value 4294967295. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testCounter32MinusOneInitval.0")
	eq_(datatype, "Counter32")
	eq_(int(data), 4294967295)

@timed(1)
def test_GET_Counter32OneInitval_eq_One():
	""" GET(Counter32(initval=1)) == 1

	This tests that the instantiation of a Counter32 SNMP object with an
	initval of 1 resulted in a snmpget'able scalar variable of type Counter32
	and value 1. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testCounter32OneInitval.0")
	eq_(datatype, "Counter32")
	eq_(int(data), 1)

@timed(1)
def test_GET_Counter32MaxInitval_eq_max():
	""" GET(Counter32(initval=4294967295)) == 4294967295

	This tests that the instantiation of a Counter32 SNMP object with an
	initval of 4294967295 resulted in a snmpget'able scalar variable of type
	Counter32 and value 4294967295. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testCounter32MaxInitval.0")
	eq_(datatype, "Counter32")
	eq_(int(data), 4294967295)

@timed(1)
def test_GET_Counter32MaxPlusOneInitval_eq_zero():
	""" GET(Counter32(initval=4294967296)) == 0

	This tests that the instantiation of a Counter32 SNMP object with an
	initval of 4294967296 resulted in a snmpget'able scalar variable of type
	Counter32 and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testCounter32MaxPlusOneInitval.0")
	eq_(datatype, "Counter32")
	eq_(int(data), 0)

# No way to test SETting a Counter32 because snmpset does not support it
# (see http://sourceforge.net/p/net-snmp/feature-requests/4/ and RFC2578
# Section 7.1.6)

@timed(1)
def test_GET_Counter64WithoutInitval_eq_Zero():
	""" GET(Counter64()) == 0

	This tests that the instantiation of a Counter64 SNMP object without
	specifying an initval resulted in a snmpget'able scalar variable of type
	Counter64 and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testCounter64NoInitval.0")
	eq_(datatype, "Counter64")
	eq_(int(data), 0)

@timed(1)
def test_GET_Counter64ZeroInitval_eq_Zero():
	""" GET(Counter64(initval=0)) == 0

	This tests that the instantiation of a Counter64 SNMP object with an
	initval of 0 resulted in a snmpget'able scalar variable of type Counter64
	and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testCounter64ZeroInitval.0")
	eq_(datatype, "Counter64")
	eq_(int(data), 0)

@timed(1)
def test_GET_Counter64MinusOneInitval_eq_Max():
	""" GET(Counter64(initval=-1)) == 18446744073709551615

	This tests that the instantiation of a Counter64 SNMP object with an
	initval of -1 resulted in a snmpget'able scalar variable of type Counter64
	and value 18446744073709551615. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testCounter64MinusOneInitval.0")
	eq_(datatype, "Counter64")
	eq_(int(data), 18446744073709551615)

@timed(1)
def test_GET_Counter64OneInitval_eq_One():
	""" GET(Counter64(initval=1)) == 1

	This tests that the instantiation of a Counter64 SNMP object with an
	initval of 1 resulted in a snmpget'able scalar variable of type Counter64
	and value 1. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testCounter64OneInitval.0")
	eq_(datatype, "Counter64")
	eq_(int(data), 1)

@timed(1)
def test_GET_Counter64MaxInitval_eq_max():
	""" GET(Counter64(initval=18446744073709551615)) == 18446744073709551615

	This tests that the instantiation of a Counter64 SNMP object with an
	initval of 18446744073709551616 resulted in a snmpget'able scalar variable
	of type Counter64 and value 18446744073709551615. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testCounter64MaxInitval.0")
	eq_(datatype, "Counter64")
	eq_(int(data), 18446744073709551615)

@timed(1)
def test_GET_Counter64MaxPlusOneInitval_eq_zero():
	""" GET(Counter64(initval=18446744073709551616)) == 0

	This tests that the instantiation of a Counter64 SNMP object with an
	initval of 18446744073709551617 resulted in a snmpget'able scalar variable
	of type Counter64 and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testCounter64MaxPlusOneInitval.0")
	eq_(datatype, "Counter64")
	eq_(int(data), 0)

# No way to test SETting a Counter64 because snmpset does not support it
# (see http://sourceforge.net/p/net-snmp/feature-requests/4/ and RFC2578
# Section 7.1.10)

@timed(1)
def test_GET_Gauge32WithoutInitval_eq_Zero():
	""" GET(Gauge32()) == 0

	This tests that the instantiation of a Gauge32 SNMP object without
	specifying an initval resulted in a snmpget'able scalar variable of type
	Gauge32 and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testGauge32NoInitval.0")
	eq_(datatype, "Gauge32")
	eq_(int(data), 0)

@timed(1)
def test_GET_Gauge32ZeroInitval_eq_Zero():
	""" GET(Gauge32(initval=0)) == 0

	This tests that the instantiation of a Gauge32 SNMP object with an
	initval of 0 resulted in a snmpget'able scalar variable of type Gauge32
	and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testGauge32ZeroInitval.0")
	eq_(datatype, "Gauge32")
	eq_(int(data), 0)

@timed(1)
def test_GET_Gauge32MinusOneInitval_eq_Max():
	""" GET(Gauge32(initval=-1)) == 4294967295

	This tests that the instantiation of a Gauge32 SNMP object with an
	initval of -1 resulted in a snmpget'able scalar variable of type Gauge32
	and value 4294967295. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testGauge32MinusOneInitval.0")
	eq_(datatype, "Gauge32")
	eq_(int(data), 4294967295)

@timed(1)
def test_GET_Gauge32OneInitval_eq_One():
	""" GET(Gauge32(initval=1)) == 1

	This tests that the instantiation of a Gauge32 SNMP object with an
	initval of 1 resulted in a snmpget'able scalar variable of type Gauge32
	and value 1. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testGauge32OneInitval.0")
	eq_(datatype, "Gauge32")
	eq_(int(data), 1)

@timed(1)
def test_GET_Gauge32MaxInitval_eq_max():
	""" GET(Gauge32(initval=4294967295)) == 4294967295

	This tests that the instantiation of a Gauge32 SNMP object with an
	initval of 4294967295 resulted in a snmpget'able scalar variable of type
	Gauge32 and value 4294967295. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testGauge32MaxInitval.0")
	eq_(datatype, "Gauge32")
	eq_(int(data), 4294967295)

@timed(1)
def test_GET_Gauge32MaxPlusOneInitval_eq_zero():
	""" GET(Gauge32(initval=4294967296)) == 0

	This tests that the instantiation of a Gauge32 SNMP object with an
	initval of 4294967296 resulted in a snmpget'able scalar variable of type
	Gauge32 and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testGauge32MaxPlusOneInitval.0")
	eq_(datatype, "Gauge32")
	eq_(int(data), 0)

@timed(1)
def test_GET_TimeTicksWithoutInitval_eq_Zero():
	""" GET(TimeTicks()) == 0

	This tests that the instantiation of a TimeTicks SNMP object without
	specifying an initval resulted in a snmpget'able scalar variable of type
	Timeticks and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testTimeTicksNoInitval.0")
	eq_(datatype, "Timeticks")
	eq_(data, "(0) 0:00:00.00")

@timed(1)
def test_GET_TimeTicksZeroInitval_eq_Zero():
	""" GET(TimeTicks(initval=0)) == 0

	This tests that the instantiation of a TimeTicks SNMP object with an
	initval of 0 resulted in a snmpget'able scalar variable of type Timeticks
	and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testTimeTicksZeroInitval.0")
	eq_(datatype, "Timeticks")
	eq_(data, "(0) 0:00:00.00")

@timed(1)
def test_GET_TimeTicksMinusOneInitval_eq_Max():
	""" GET(TimeTicks(initval=-1)) == 4294967295

	This tests that the instantiation of a TimeTicks SNMP object with an
	initval of -1 resulted in a snmpget'able scalar variable of type Timeticks
	and value 4294967295. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testTimeTicksMinusOneInitval.0")
	eq_(datatype, "Timeticks")
	eq_(data, "(4294967295) 497 days, 2:27:52.95")

@timed(1)
def test_GET_TimeTicksOneInitval_eq_One():
	""" GET(TimeTicks(initval=1)) == 1

	This tests that the instantiation of a TimeTicks SNMP object with an
	initval of 1 resulted in a snmpget'able scalar variable of type Timeticks
	and value 1. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testTimeTicksOneInitval.0")
	eq_(datatype, "Timeticks")
	eq_(data, "(1) 0:00:00.01")

@timed(1)
def test_GET_TimeTicksMaxInitval_eq_max():
	""" GET(TimeTicks(initval=4294967295)) == 4294967295

	This tests that the instantiation of a TimeTicks SNMP object with an
	initval of 4294967295 resulted in a snmpget'able scalar variable of type
	Timeticks and value 4294967295. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testTimeTicksMaxInitval.0")
	eq_(datatype, "Timeticks")
	eq_(data, "(4294967295) 497 days, 2:27:52.95")

@timed(1)
def test_GET_TimeTicksMaxPlusOneInitval_eq_zero():
	""" GET(TimeTicks(initval=4294967296)) == 0

	This tests that the instantiation of a TimeTicks SNMP object with an
	initval of 4294967296 resulted in a snmpget'able scalar variable of type
	Timeticks and value 0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testTimeTicksMaxPlusOneInitval.0")
	eq_(datatype, "Timeticks")
	eq_(data, "(0) 0:00:00.00")

@timed(1)
def test_SET_TimeTicks_42_eq_42():
	""" SET(TimeTicks(), 42) == 42

	This tests that calling snmpset on a previously instantiated scalar
	variable of type TimeTicks and value 0 (this was confirmed by an earlier
	test) with the new value 42 results in the netsnmpagent SNMP object
	returning 42 as its value, too. """

	global testenv, settableTimeTicks

	print(testenv.snmpset("TEST-MIB::testTimeTicksNoInitval.0", 42, "t"))

	eq_(settableTimeTicks.value(), 42)

@timed(1)
def test_GET_SET_TimeTicks_42_eq_42():
	""" GET(SET(TimeTicks(), 42)) == 42

	This tests that calling snmpget on the previously instantiated scalar
	variable of type TimeTicks that has just been set to 42 also returns this
	new variable when accessed through snmpget. """

	(data, datatype) = testenv.snmpget("TEST-MIB::testTimeTicksNoInitval.0")
	eq_(datatype, "Timeticks")
	eq_(data, "(42) 0:00:00.42")

@timed(1)
@raises(netsnmpTestEnv.NotWritableError)
def test_SET_TimeTicksReadOnly_42_raises_Exception():
	""" SET(TimeTicks(readonly=True) raises Exception

	This tests that calling snmpset on a previously instantiated scalar
	variable of type TimeTicks that has the readonly property set triggers
	a NotWriteableError exception. """

	global testenv

	testenv.snmpset("TEST-MIB::testTimeTicksReadOnly.0", 42, "t")

@timed(1)
def test_GET_IpAddressWithoutInitval_eq_0_0_0_0():
	""" GET(IpAddress()) == "0.0.0.0"

	This tests that the instantiation of an IpAddress SNMP object without
	specifying an initval resulted in a snmpget'able scalar variable of type
	IpAddress and the IP address "0.0.0.0" as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testIpAddressNoInitval.0")
	eq_(datatype, "IpAddress")
	eq_(data, "0.0.0.0")

@timed(1)
def test_GET_IpAddressEmptyInitval_eq_0_0_0_0():
	""" GET(IpAddress(initval="")) == "0.0.0.0"

	This tests that the instantiation of an IpAddress SNMP object with an
	empty string as initval resulted in a snmpget'able scalar variable of type
	IpAddress and the IP address "0.0.0.0" as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testIpAddressEmptyInitval.0")
	eq_(datatype, "IpAddress")
	eq_(data, "0.0.0.0")

@timed(1)
def test_GET_IpAddress1234Initval_eq_1_2_3_4():
	""" GET(IpAddress(initval="1.2.3.4")) == "1.2.3.4"

	This tests that the instantiation of an IpAddress SNMP object with the
	string "1.2.3.4" as initval resulted in a snmpget'able scalar variable of
	type IpAddress and the IP address '1.2.3.4' as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testIpAddress1234Initval.0")
	eq_(datatype, "IpAddress")
	eq_(data, "1.2.3.4")

@timed(1)
def test_GET_TruthValueWithoutInitval_eq_False():
	""" GET(TruthValue()) == false(2)

	This tests that the instantiation of a TruthValue SNMP object without
	specifying an initval resulted in a snmpget'able scalar variable of type
	INTEGER and value false(2). """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testTruthValueNoInitval.0")
	eq_(datatype, "INTEGER")
	eq_(data, "false(2)")

@timed(1)
def test_GET_TruthValueFalseInitval_eq_False():
	""" GET(TruthValue(initval=False)) == false(2)

	This tests that the instantiation of a TruthValue SNMP object with an
	initval of False resulted in a snmpget'able scalar variable of type INTEGER
	and value false(2). """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testTruthValueFalseInitval.0")
	eq_(datatype, "INTEGER")
	eq_(data, "false(2)")

@timed(1)
def test_GET_TruthValueTrueInitval_eq_True():
	""" GET(TruthValue(initval=True)) == true(1)

	This tests that the instantiation of a TruthValue SNMP object with an
	initval of True resulted in a snmpget'able scalar variable of type INTEGER
	and value true(1). """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testTruthValueTrueInitval.0")
	eq_(datatype, "INTEGER")
	eq_(data, "true(1)")

@timed(1)
def test_GET_FloatWithoutInitval_eq_ZeroPointZero():
	""" GET(Float()) == 0.0

	This tests that the instantiation of a Float SNMP object without
	specifying an initval resulted in a snmpget'able scalar variable of type
	"Opaque: Float" and value 0.0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testFloatNoInitval.0")
	eq_(datatype, "Opaque: Float")
	eq_(float(data), 0.0)

@timed(1)
def test_GET_FloatZeroPointZeroInitval_eq_ZeroPointZero():
	""" GET(Float(initval=0.0)) == 0.0

	This tests that the instantiation of a Float SNMP object with an
	initval of 0.0 resulted in a snmpget'able scalar variable of type
	"Opaque: Float" and value 0.0. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testFloatZeroPointZeroInitval.0")
	eq_(datatype, "Opaque: Float")
	eq_(float(data), 0.0)

@timed(1)
def test_GET_FloatZeroPointOneInitval_eq_ZeroPointOne():
	""" GET(Float(initval=0.1)) == 0.1

	This tests that the instantiation of a Float SNMP object with an
	initval of 0.1 resulted in a snmpget'able scalar variable of type
	"Opaque: Float" and value 0.1. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testFloatZeroPointOneInitval.0")
	eq_(datatype, "Opaque: Float")
	eq_(float(data), 0.1)

@timed(1)
def test_GET_FloatOnePointTwoInitval_eq_OnePointTwo():
	""" GET(Float(initval=1.2)) == 1.2

	This tests that the instantiation of a Float SNMP object with an
	initval of 1.2 resulted in a snmpget'able scalar variable of type
	"Opaque: Float" and value 1.2. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testFloatOnePointTwoInitval.0")
	eq_(datatype, "Opaque: Float")
	eq_(float(data), 1.2)

@timed(1)
def test_GET_FloatMinusZeroPointOneInitval_eq_MinusZeroPointOne():
	""" GET(Float(initval=-0.1)) == -0.1

	This tests that the instantiation of a Float SNMP object with an
	initval of -0.1 resulted in a snmpget'able scalar variable of type
	"Opaque: Float" and value -0.1. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testFloatMinusZeroPointOneInitval.0")
	eq_(datatype, "Opaque: Float")
	eq_(float(data), -0.1)

@timed(1)
def test_GET_FloatMinusOnePointTwoInitval_eq_MinusOnePointTwo():
	""" GET(Float(initval=-1.2)) == -1.2

	This tests that the instantiation of a Float SNMP object with an
	initval of -1.2 resulted in a snmpget'able scalar variable of type
	"Opaque: Float" and value -1.2. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testFloatMinusOnePointTwoInitval.0")
	eq_(datatype, "Opaque: Float")
	eq_(float(data), -1.2)

@timed(1)
def test_GET_OctetStringWithoutInitval_eq_Empty():
	""" GET(OctetString()) == ""

	This tests that the instantiation of an OctetString SNMP object without
	specifying an initval resulted in a snmpget'able scalar variable of type
	STRING and an empty string as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testOctetStringNoInitval.0")
	eq_(datatype, "STRING")
	eq_(data, "")

@timed(1)
def test_GET_OctetStringEmptyInitval_eq_Empty():
	""" GET(OctetString(initval="")) == ""

	This tests that the instantiation of an OctetString SNMP object with an
	empty string as initval resulted in a snmpget'able scalar variable of type
	STRING and an empty string as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testOctetStringEmptyInitval.0")
	eq_(datatype, "STRING")
	eq_(data, "")

@timed(1)
def test_GET_OctetStringOneASCIICharInitval_eq_ASCIIChar():
	""" GET(OctetString(initval="A")) == "A"

	This tests that the instantiation of an OctetString SNMP object with a
	string consisting of a single ASCII character 'A' as initval resulted in a
	snmpget'able scalar variable of type STRING and the single ASCII character
	'A' as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testOctetStringOneASCIICharInitval.0")
	eq_(datatype, "STRING")
	eq_(data, "A")

@timed(1)
def test_GET_OctetStringOneUTF8CharInitval_eq_UTF8Char():
	""" GET(OctetString(initval="Ä")) == utf8("Ä")

	This tests that the instantiation of an OctetString SNMP object with a
	string consisting of the single UTF8 character 'Ä' as initval resulted in
	a snmpget'able scalar variable of type Hex-STRING and the UTF8 hexadecimal
	representation of 'Ä', "C384", as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testOctetStringOneUTF8CharInitval.0")
	eq_(datatype, "Hex-STRING")
	data = re.sub('( |\n)', '', data)
	eq_(data, "C384")

@timed(1)
def test_GET_OctetString255ASCIICharsInitval_eq_255ASCIIChars():
	""" GET(OctetString(initval="AAA..." [n=255])) == "AAA..." [n=255]

	This tests that the instantiation of an OctetString SNMP object with a
	string consisting of 255 ASCII characters as initval resulted in a
	snmpget'able scalar variable of type STRING and the 255 ASCII characters
	as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testOctetString255ASCIICharsInitval.0")
	eq_(datatype, "STRING")
	eq_(data, "A" * 255)

@timed(1)
def test_GET_OctetString255UTF8CharsInitval_eq_255UTF8Chars():
	""" GET(OctetString(initval="ÄÄÄ..." [n=255])) == utf8("ÄÄÄ...") [n=255]

	This tests that the instantiation of an OctetString SNMP object with a
	string consisting of 255 UTF8 characters 'Ä' as initval resulted in a
	snmpget'able scalar variable of type Hex-STRING and the UTF8 hexadecimal
	representation of the 255 'Ä' characters as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testOctetString255UTF8CharsInitval.0")
	eq_(datatype, "Hex-STRING")
	data = re.sub('( |\n)', '', data)
	eq_(data, "C384" * 255)

@timed(1)
def test_GET_OctetString256ASCIICharsInitval_eq_256ASCIIChars():
	""" GET(OctetString(initval="AAA..." [n=256])) == "AAA..." [n=256]

	This tests that the instantiation of an OctetString SNMP object with a
	string consisting of 256 ASCII characters as initval resulted in a
	snmpget'able scalar variable of type STRING and 256 ASCII characters
	as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testOctetString256ASCIICharsInitval.0")
	eq_(datatype, "STRING")
	eq_(data, "A" * 256)

@timed(1)
def test_GET_OctetString256UTF8CharsInitval_eq_256UTF8Chars():
	""" GET(OctetString(initval="ÄÄÄ..." [n=256])) == utf8("ÄÄÄ...") [n=256]

	This tests that the instantiation of an OctetString SNMP object with a
	string consisting of 256 UTF8 characters 'Ä' as initval resulted in a
	snmpget'able scalar variable of type Hex-STRING and the UTF8 hexadecimal
	representation of the 256 'Ä' characters as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testOctetString256UTF8CharsInitval.0")
	eq_(datatype, "Hex-STRING")
	data = re.sub('( |\n)', '', data)
	eq_(data, "C384" * 256)

@timed(1)
def test_SET_OctetStringWithoutInterval_abcdef_eq_abcdef():
	""" SET(OctetString(), abcdef) == abcdef

	This tests that calling snmpset on a previously instantiated scalar
	variable of type OctetString and the empty string "" as value (this was
	confirmed by an earlier test) with the new value "abcdef" results in the
	netsnmpagent SNMP object returning "abcdef" as its value, too. """

	global testenv, settableOctetString

	print(testenv.snmpset("TEST-MIB::testOctetStringNoInitval.0", "abcdef", "s"))

	eq_(settableOctetString.value(), "abcdef")

@timed(1)
def test_GET_SET_OctetStringWithoutInterval_abcdef_eq_abcdef():
	""" GET(SET(OctetString(), abcdef)) == abcdef

	This tests that calling snmpget on the previously instantiated scalar
	variable of type OctetString that has just been set to "abcdef" also
	returns this new variable when accessed through snmpget. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testOctetStringNoInitval.0")
	eq_(datatype, "STRING")
	eq_(data, "abcdef")

@timed(1)
def test_GET_DisplayStringWithoutInitval_eq_Empty():
	""" GET(DisplayString()) == ""

	This tests that the instantiation of a DisplayString SNMP object without
	specifying an initval resulted in a snmpget'able scalar variable of type
	STRING and an empty string as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testDisplayStringNoInitval.0")
	eq_(datatype, "STRING")
	eq_(data, "")

@timed(1)
def test_GET_DisplayStringEmptyInitval_eq_Empty():
	""" GET(DisplayString(initval="")) == ""

	This tests that the instantiation of a DisplayString SNMP object with an
	empty string as initval resulted in a snmpget'able scalar variable of type
	STRING and an empty string as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testDisplayStringEmptyInitval.0")
	eq_(datatype, "STRING")
	eq_(data, "")

@timed(1)
def test_GET_DisplayStringOneASCIICharInitval_eq_ASCIIChar():
	""" GET(DisplayString(initval="A")) == "A"

	This tests that the instantiation of a DisplayString SNMP object with a
	string consisting of a single ASCII character 'A' as initval resulted in a
	snmpget'able scalar variable of type STRING and the single ASCII character
	'A' as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testDisplayStringOneASCIICharInitval.0")
	eq_(datatype, "STRING")
	eq_(data, "A")

@timed(1)
def test_GET_DisplayString255ASCIICharsInitval_eq_255ASCIIChars():
	""" GET(DisplayString(initval="AAA..." [n=255])) == "AAA..." [n=255]

	This tests that the instantiation of a DisplayString SNMP object with a
	string consisting of 255 ASCII characters as initval resulted in a
	snmpget'able scalar variable of type STRING and the 255 ASCII characters
	as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testDisplayString255ASCIICharsInitval.0")
	eq_(datatype, "STRING")
	eq_(data, "A" * 255)

@timed(1)
def test_GET_DisplayString256ASCIICharsInitval_eq_256ASCIIChars():
	""" GET(DisplayString(initval="AAA..." [n=256])) == "AAA..." [n=256]

	This tests that the instantiation of a DisplayString SNMP object with a
	string consisting of 256 ASCII characters as initval resulted in a
	snmpget'able scalar variable of type STRING and 256 ASCII characters
	as value. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testDisplayString256ASCIICharsInitval.0")
	eq_(datatype, "STRING")
	eq_(data, "A" * 256)

@timed(1)
def test_SET_DisplayStringWithoutInterval_abcdef_eq_abcdef():
	""" SET(DisplayString(), abcdef) == abcdef

	This tests that calling snmpset on a previously instantiated scalar
	variable of type DisplayString and the empty string "" as value (this was
	confirmed by an earlier test) with the new value "abcdef" results in the
	netsnmpagent SNMP object returning "abcdef" as its value, too. """

	global testenv, settableDisplayString

	print(testenv.snmpset("TEST-MIB::testDisplayStringNoInitval.0", "abcdef", "s"))

	eq_(settableDisplayString.value(), "abcdef")

@timed(1)
def test_GET_SET_DisplayStringWithoutInterval_abcdef_eq_abcdef():
	""" GET(SET(DisplayString(), abcdef)) == abcdef

	This tests that calling snmpget on the previously instantiated scalar
	variable of type DisplayString that has just been set to "abcdef" also
	returns this new variable when accessed through snmpget. """

	global testenv

	(data, datatype) = testenv.snmpget("TEST-MIB::testDisplayStringNoInitval.0")
	eq_(datatype, "STRING")
	eq_(data, "abcdef")
