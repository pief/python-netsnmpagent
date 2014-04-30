#!/usr/bin/env python
# encoding: utf-8
#
# python-netsnmpagent module
# Copyright (c) 2013 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Public License (GPL) version 3
#
# Integration tests for the netsnmptestenv helper module
#

import sys, os, unittest, subprocess, re
sys.path.insert(1, "..")
from netsnmptestenv import netsnmpTestEnv

class netsnmpTestEnvTest(unittest.TestCase):
	""" Tests the netsnmptestenv module. """

	def setUp(self):
		self.testenv = None

	def test_snmpget_snmpv2mib(self):
		# Initially snmpget should fail
		with self.assertRaises(subprocess.CalledProcessError):
			netsnmpTestEnv.snmpget("SNMPv2-MIB::snmpSetSerialNo.0")

		# After we create our test environment...
		self.testenv = netsnmpTestEnv()

		# ...snmpget should work
		output = netsnmpTestEnv.snmpget("SNMPv2-MIB::snmpSetSerialNo.0")
		m = re.match(r"^SNMPv2-MIB::snmpSetSerialNo.0 = INTEGER: \d+$", output)
		try:
			self.assertNotEqual(m, None)
		except AssertionError:
			raise AssertionError("'{0}' != ^SNMPv2-MIB::snmpSetSerialNo.0 = INTEGER: \d+$".format(output))

	def tearDown(self):
		# Destroy the test environment, if set up before
		if self.testenv:
			del self.testenv

		# snmpget should fail
		with self.assertRaises(subprocess.CalledProcessError):
			netsnmpTestEnv.snmpget("SNMPv2-MIB::snmpSetSerialNo.0")

if __name__ == '__main__':
	unittest.main(verbosity=2)
