#!/usr/bin/env python
#
# python-netsnmpagent simple example agent
#
# Copyright (c) 2013-2019 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Lesser Public License (LGPL) version 3
#

#
# This is an example of a simple SNMP sub-agent using the AgentX protocol
# to connect to a master agent (snmpd), extending its MIB with the
# information from the included SIMPLE-MIB.txt.
#
# Use the included script run_simple_agent.sh to test this example.
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
import pprint

# Make sure we use the local copy, not a system-wide one
sys.path.insert(0, os.path.dirname(os.getcwd()))
import netsnmpagent

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

# Then we create all SNMP scalar variables we're willing to serve.
simpleInteger = agent.Integer32(
	oidstr   = "SIMPLE-MIB::simpleInteger"
)
simpleIntegerContext1 = agent.Integer32(
	oidstr   = "SIMPLE-MIB::simpleInteger",
	context  = "context1",
	initval  = 200,
)
simpleIntegerRO = agent.Integer32(
	oidstr   = "SIMPLE-MIB::simpleIntegerRO",
	writable = False
)
simpleUnsigned = agent.Unsigned32(
	oidstr   = "SIMPLE-MIB::simpleUnsigned"
)
simpleUnsignedRO = agent.Unsigned32(
	oidstr   = "SIMPLE-MIB::simpleUnsignedRO",
	writable = False
)
simpleCounter32 = agent.Counter32(
	oidstr   = "SIMPLE-MIB::simpleCounter32"
)
simpleCounter32Context2 = agent.Counter32(
	oidstr   = "SIMPLE-MIB::simpleCounter32",
	context  = "context2",
	initval  = pow(2,32) - 10, # To rule out endianness bugs
)
simpleCounter64 = agent.Counter64(
	oidstr   = "SIMPLE-MIB::simpleCounter64"
)
simpleCounter64Context2 = agent.Counter64(
	oidstr   = "SIMPLE-MIB::simpleCounter64",
	context  = "context2",
	initval  = pow(2,64) - 10, # To rule out endianness bugs
)
simpleTimeTicks = agent.TimeTicks(
	oidstr   = "SIMPLE-MIB::simpleTimeTicks"
)
simpleIpAddress = agent.IpAddress(
	oidstr   = "SIMPLE-MIB::simpleIpAddress",
	initval  = "127.0.0.1"
)
simpleFloat = agent.Float(
	oidstr   = "SIMPLE-MIB::simpleFloat",
	initval  = 3.4000000953674316
)
simpleOctetString = agent.OctetString(
	oidstr   = "SIMPLE-MIB::simpleOctetString",
	initval  = "Hello World"
)
simpleDisplayString = agent.DisplayString(
	oidstr   = "SIMPLE-MIB::simpleDisplayString",
	initval  = "Nice to meet you"
)

simpleEnumVal = agent.Integer32(
	oidstr   = "SIMPLE-MIB::simpleEnumVal",
	initval  = 1
)

# Create the first table
firstTable = agent.Table(
	oidstr  = "SIMPLE-MIB::firstTable",
	indexes = [
		agent.DisplayString()
	],
	columns = [
		# Columns begin with an index of 2 here because 1 is actually
		# used for the single index column above.
		# We must explicitly specify that the columns should be SNMPSETable.
		(2, agent.DisplayString("Unknown place"), True),
		(3, agent.Integer32(0), True)
	],
	counterobj = agent.Unsigned32(
		oidstr = "SIMPLE-MIB::firstTableNumber"
	),
	# Allow adding new records
	extendable = True
)

# Add the first table row
firstTableRow1 = firstTable.addRow([agent.DisplayString("aa")])
firstTableRow1.setRowCell(2, agent.DisplayString("Prague"))
firstTableRow1.setRowCell(3, agent.Integer32(20))

# Add the second table row
firstTableRow2 = firstTable.addRow([agent.DisplayString("ab")])
firstTableRow2.setRowCell(2, agent.DisplayString("Barcelona"))
firstTableRow2.setRowCell(3, agent.Integer32(28))

# Add the third table row
firstTableRow3 = firstTable.addRow([agent.DisplayString("bb")])
firstTableRow3.setRowCell(3, agent.Integer32(18))

# Create the second table
secondTable = agent.Table(
	oidstr  = "SIMPLE-MIB::secondTable",
	indexes = [
		agent.Integer32()
	],
	columns = [
		(2, agent.DisplayString("Unknown interface")),
		(3, agent.Unsigned32())
	],
	counterobj = agent.Unsigned32(
		oidstr = "SIMPLE-MIB::secondTableNumber"
	)
)

# Add the first table row
secondTableRow1 = secondTable.addRow([agent.Integer32(1)])
secondTableRow1.setRowCell(2, agent.DisplayString("foo0"))
secondTableRow1.setRowCell(3, agent.Unsigned32(5030))

# Add the second table row
secondTableRow2 = secondTable.addRow([agent.Integer32(2)])
secondTableRow2.setRowCell(2, agent.DisplayString("foo1"))
secondTableRow2.setRowCell(3, agent.Unsigned32(12842))

# Create the third table
thirdTable = agent.Table(
	oidstr     = "SIMPLE-MIB::thirdTable",
	indexes    = [
		agent.IpAddress()
	],
	columns    = [
		(2, agent.DisplayString("Broadcast")),
		(3, agent.IpAddress("192.168.0.255"))
	],
	counterobj = agent.Unsigned32(
		oidstr = "SIMPLE-MIB::thirdTableNumber"
	)
)

# Add the first table row
thirdTableRow1 = thirdTable.addRow([agent.IpAddress("192.168.0.1")])
thirdTableRow1.setRowCell(2, agent.DisplayString("Host 1"))
thirdTableRow1.setRowCell(3, agent.IpAddress("192.168.0.1"))

# Add the second table row
thirdTableRow2 = thirdTable.addRow([agent.IpAddress("192.168.0.2")])
thirdTableRow2.setRowCell(2, agent.DisplayString("Host 2"))
thirdTableRow2.setRowCell(3, agent.IpAddress("192.168.0.2"))

# Add the third table row
thirdTableRow3 = thirdTable.addRow([agent.IpAddress("192.168.0.3")])

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

	# Since we didn't give simpleCounter, simpleCounter64 and simpleTimeTicks
	# a real meaning in the SIMPLE-MIB, we can basically do with them whatever
	# we want. Here, we just increase them, although in different manners.
	simpleCounter32.update(simpleCounter32.value() + 2)
	simpleCounter64.update(simpleCounter64.value() + 4294967294)
	simpleTimeTicks.update(simpleTimeTicks.value() + 1)

	# With counters, you can also call increment() on them
	simpleCounter32Context2.increment() # By 1
	simpleCounter64Context2.increment(5) # By 5

print("{0}: Terminating.".format(prgname))
agent.shutdown()
