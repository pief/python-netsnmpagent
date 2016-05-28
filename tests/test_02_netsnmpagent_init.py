#!/usr/bin/env python
# encoding: utf-8
#
# python-netsnmpagent module
# Copyright (c) 2013-2016 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Lesser Public License (LGPL) version 3
#
# Integration tests for the netsnmpagent module (init behavior)
#

import sys, os, re, subprocess, threading, signal, time
from nose.tools import *
sys.path.insert(1, "..")
from netsnmptestenv import netsnmpTestEnv
import netsnmpagent

def setUp(self):
	global testenv

	testenv = netsnmpTestEnv()

def tearDown(self):
	global testenv, agent

	if "agent" in globals():
		agent.shutdown()

	if "testenv" in globals():
		testenv.shutdown()

@timed(1)
@raises(netsnmpTestEnv.MIBUnavailableError)
def test_FirstGetFails():
	""" Instance not created yet, MIB unvailable """

	print netsnmpTestEnv.snmpget("TEST-MIB::testUnsigned32NoInitval.0")

@timed(1)
def test_Instantiation():
	""" Instantiation without exceptions and within reasonable time """

	global logbuf, agent

	# Create a buffer to capture net-snmp log messages
	logbuf = []

	# Define a custom net-snmp logging handler
	def NetSNMPLogHandler(msgprio, msgtext):
		global logbuf

		# Store net-snmp log messages in our buffer so we can have a look
		# at them later on
		logbuf.append({
			"time": time.clock(),
			"prio": msgprio,
			"text": msgtext,
		})

		# Also print them out to stdout as the default log handler would, nose
		# will capture the output and display it if a test fails
		print "[{0}] {1}".format(msgprio, msgtext)

	# Create a new netsnmpAgent instance which
	# - connects to the net-snmp test environment's snmpd instance
	# - uses its statedir
	# - loads the TEST-MIB from our tests directory
	# - uses the net-snmp logging handler defined above
	testMIBPath = os.path.abspath(os.path.dirname(__file__)) + \
				  "/TEST-MIB.txt"
	agent = netsnmpagent.netsnmpAgent(
		AgentName      = "netsnmpAgentTestAgent",
		MasterSocket   = testenv.mastersocket,
		PersistenceDir = testenv.statedir,
		MIBFiles       = [ testMIBPath ],
		LogHandler     = NetSNMPLogHandler,
	)

@nottest
def in_netsnmp_log(regexp):
	""" Checks whether "regexp" was logged by net-snmp. """

	global logbuf

	for msg in logbuf:
		if re.search(regexp, msg["text"]):
			return True

	return False

@timed(1)
@raises(netsnmpTestEnv.MIBUnavailableError)
def test_SecondGetFails():
	""" Subagent not connected yet, MIB still unavailable """

	global testenv

	testenv.snmpget("TEST-MIB::testUnsigned32NoInitval.0")

@timed(1)
def test_StartingAgentConnectsToMaster():
	""" Calling agent.start() connects to master agent """

	global agent

	agent.start()

	ok_(in_netsnmp_log("NET-SNMP version .* subagent connected") == True, "No connection to master agent")

@timed(1)
@raises(netsnmpTestEnv.MIBUnavailableError)
def test_ThirdGetFails():
	""" No OIDs registered, OID still unknown """

	global testenv

	testenv.snmpget("TEST-MIB::testUnsigned32NoInitval.0")
