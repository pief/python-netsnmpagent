#!/usr/bin/env python
#
# python-netsnmpagent callback example agent
#
# Copyright (c) 2013-2016 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Lesser Public License (LGPL) version 3
#

#
# This is an example of a simple SNMP sub-agent using the AgentX protocol
# to connect to a master agent (snmpd), extending its MIB with the
# information from the included SIMPLE-MIB.txt.
#
# Use the included script run_callback_agent.sh to test this example.
#
# Alternatively, if you want to test with your system-wide snmpd instance,
# it must have as minimal configuration:
#
#   rocommunity <rosecret> 127.0.0.1
#   master agentx
#
# snmpd must be started first, then this agent must be started as root
# (because of the AgentX socket under /var/run/agentx/master), eg. via "sudo".
#
# Then, from a separate console and from inside the python-netsnmpagent
# directory, you can run eg.:
#
#  snmpwalk -v 2c -c <rosecret> -M+. localhost SIMPLE-MIB::simpleMIB
#
# If you wish to test setting values as well, your snmpd.conf needs a
# line like this:
#
#   rwcommunity <rwsecret> 127.0.0.1
#
# Then you can try something like:
#
#   snmpset -v 2c -c <rwsecret> -M+. localhost \
#     SIMPLE-MIB::simpleInteger i 0
#

import sys, os, signal
import optparse
import random
import pprint

# Make sure we use the local copy, not a system-wide one
sys.path.insert(0, os.path.dirname(os.getcwd()))
import netsnmpagent
import netsnmpapi

prgname = sys.argv[0]

# Process command line arguments
parser = optparse.OptionParser()
parser.add_option(
	"-m",
	"--mastersocket",
	dest="mastersocket",
	help="Sets the transport specification for the master agent's AgentX socket",
	default="/var/run/agentx/master"
)
parser.add_option(
	"-p",
	"--persistencedir",
	dest="persistencedir",
	help="Sets the path to the persistence directory",
	default="/var/lib/net-snmp"
)
(options, args) = parser.parse_args()

# Get terminal width for usage with pprint
rows, columns = os.popen("stty size", "r").read().split()

# First, create an instance of the netsnmpAgent class. We specify the
# fully-qualified path to SIMPLE-MIB.txt ourselves here, so that you
# don't have to copy the MIB to /usr/share/snmp/mibs.
try:
	agent = netsnmpagent.netsnmpAgent(
		AgentName      = "SimpleAgent",
		MasterSocket   = options.mastersocket,
		PersistenceDir = options.persistencedir,
		MIBFiles       = [ os.path.abspath(os.path.dirname(sys.argv[0])) +
		                   "/SIMPLE-MIB.txt" ]
	)
except netsnmpagent.netsnmpAgentException as e:
	print("{0}: {1}".format(prgname, e))
	sys.exit(1)


class StoredData(object):

	def __init__(self):
		# Then we create all SNMP scalar variables we're willing to serve.
		self.simpleInteger = agent.Integer32(
			oidstr   = "SIMPLE-MIB::simpleInteger",
			initval  = 0,
			callback = self.custom_handler
		)
		self.simpleDisplayString = agent.DisplayString(
			oidstr   = "SIMPLE-MIB::simpleDisplayString",
			initval  = "Nice to meet you",
			callback = self.custom_handler
		)

		# Create the first table
		self.firstTable = agent.Table(
			oidstr  = "SIMPLE-MIB::firstTable",
			indexes = [
				agent.DisplayString()
			],
			columns = [
				(2, agent.DisplayString("Unknown place")),
				(3, agent.Integer32(0))
			],
			counterobj = agent.Unsigned32(
				oidstr = "SIMPLE-MIB::firstTableNumber"
			),
			callback = self.custom_handler
		)

		# Add the first table row
		firstTableRow1 = self.firstTable.addRow([agent.DisplayString("aa")])
		firstTableRow1.setRowCell(2, agent.DisplayString("Prague"))
		firstTableRow1.setRowCell(3, agent.Integer32(20))

	def custom_handler(self, mib_handler_p, handler_reg_p, agent_request_info_p, request_info_p):
		"""
		This is our custom callback handler. See netsnmpapi.SNMPNodeHandler for
		the signature that it should have.
		"""
		if agent_request_info_p[0].mode == netsnmpapi.MODE_GET:
			print("Custom callback called for GET!")

			random_int = random.randint(0, 100)
			update_bytes = ("Callback called: " + str(random_int)).encode('utf-8')

			# We can update values here and the updated value will be in the response
			self.firstTable.addRow([
				agent.DisplayString(update_bytes)
			])
			self.simpleInteger.update(random_int)
			self.simpleDisplayString.update(update_bytes)

		elif agent_request_info_p[0].mode == netsnmpapi.MODE_SET_ACTION:
			print("Custom callback called for SET!")

			# Here, your application could perform any other actions it needs when a
			# value is set. In our case we will return an error indicating this
			# handler does not support SET
			return netsnmpapi.SNMP_ERR_GENERR

		# Return a success value to indicate that the handler did not fail.
		# In many cases, you will want to return SNMP_ERR_NOERROR even if something
		# went wrong in your handler, so the remaining default net-snmp handlers
		# will continue to run
		return netsnmpapi.SNMP_ERR_NOERROR


data_store = StoredData()

# Finally, we tell the agent to "start". This actually connects the
# agent to the master agent.
try:
	agent.start()
except netsnmpagent.netsnmpAgentException as e:
	print("{0}: {1}".format(prgname, e))
	sys.exit(1)

print("{0}: AgentX connection to snmpd established.".format(prgname))

# Helper function that dumps the state of all registered SNMP variables
def DumpRegistered():
	for context in agent.getContexts():
		print("{0}: Registered SNMP objects in Context \"{1}\": ".format(prgname, context))
		vars = agent.getRegistered(context)
		pprint.pprint(vars, width=columns)
		print
DumpRegistered()

# Install a signal handler that terminates our simple agent when
# CTRL-C is pressed or a KILL signal is received
def TermHandler(signum, frame):
	global loop
	loop = False
signal.signal(signal.SIGINT, TermHandler)
signal.signal(signal.SIGTERM, TermHandler)

# Install a signal handler that dumps the state of all registered values
# when SIGHUP is received
def HupHandler(signum, frame):
	DumpRegistered()
signal.signal(signal.SIGHUP, HupHandler)

# The simple agent's main loop. We loop endlessly until our signal
# handler above changes the "loop" variable.
print("{0}: Serving SNMP requests, send SIGHUP to dump SNMP object state, press ^C to terminate...".format(prgname))

loop = True
while (loop):
	# Block and process SNMP requests, if available
	agent.check_and_process()

print("{0}: Terminating.".format(prgname))
agent.shutdown()
