#!/usr/bin/env python
#
# python-netsnmpagent example agent
#
# Copyright (c) 2013 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Public License (GPL) version 3
#

#
# This is an example of a SNMP sub-agent using the AgentX protocol
# to connect to a master agent (snmpd), extending its MIB with the
# information from the included EXAMPLE-MIB.tx.
#
# To run, net-snmp must be installed and snmpd must have as minimal
# configuration:
#
#   master agentx
#
# snmpd must be started first, then this agent must be started as root
# (because of the AgentX socket under /var/run/agentx/master).
#
# Then, from a separate console, you can run eg.:
#
#  snmpwalk -v 2c -c public -M+. localhost EXAMPLE-MIB::exampleMIB
#
# If you wish to test setting values as well, your snmpd.conf needs a
# line like this:
#
#   rwcommunity <secret> 127.0.0.1
#
# Then you can try something like:
#
#   snmpset -v 2c -c <secret> -M+. localhost \
#     EXAMPLE-MIB::exampleInteger i 0
#

import sys, os, signal
import optparse
import pprint
import netsnmpagent

prgname = sys.argv[0]

# Process command line arguments
parser = optparse.OptionParser()
parser.add_option(
	"-m",
	"--mastersocket",
	dest="mastersocket",
	help="Sets the path to the master agent's AgentX unix domain socket",
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
rows,columns = os.popen("stty size", "r").read().split()

# First, create an instance of the netsnmpAgent class. We specify the
# fully-qualified path to EXAMPLE-MIB.txt ourselves here, so that you
# don't have to copy the MIB to /usr/share/snmp/mibs.
agent = netsnmpagent.netsnmpAgent(
	AgentName      = "ExampleAgent",
	MasterSocket   = options.mastersocket,
	PersistenceDir = options.persistencedir,
	MIBFiles       = [ os.path.abspath(os.path.dirname(sys.argv[0])) +
	                   "/EXAMPLE-MIB.txt" ]
)

# Then we create all SNMP scalar variables we're willing to serve.
exampleInteger = agent.Integer32(
	oidstr = "EXAMPLE-MIB::exampleInteger"
)
exampleIntegerContext1 = agent.Integer32(
	oidstr = "EXAMPLE-MIB::exampleInteger",
	context = "context1",
	initval = 200,
)
exampleIntegerRO = agent.Integer32(
	oidstr   = "EXAMPLE-MIB::exampleIntegerRO",
	writable = False
)
exampleUnsigned = agent.Unsigned32(
	oidstr = "EXAMPLE-MIB::exampleUnsigned"
)
exampleUnsignedRO = agent.Unsigned32(
	oidstr   = "EXAMPLE-MIB::exampleUnsignedRO",
	writable = False
)
exampleCounter32 = agent.Counter32(
	oidstr = "EXAMPLE-MIB::exampleCounter32"
)
exampleCounter32Context2 = agent.Counter32(
	oidstr = "EXAMPLE-MIB::exampleCounter32",
	context = "context2",
	initval = pow(2,32) - 10,
)
exampleCounter64Context2 = agent.Counter64(
	oidstr = "EXAMPLE-MIB::exampleCounter64",
	context = "context2",
	initval = pow(2,64) - 10,
)
exampleCounter64 = agent.Counter64(
	oidstr = "EXAMPLE-MIB::exampleCounter64"
)
exampleTimeTicks = agent.TimeTicks(
	oidstr = "EXAMPLE-MIB::exampleTimeTicks"
)
exampleIpAddress = agent.IpAddress(
	oidstr = "EXAMPLE-MIB::exampleIpAddress",
	initval="127.0.0.1"
)
exampleOctetString = agent.OctetString(
	oidstr  = "EXAMPLE-MIB::exampleOctetString",
	initval = "Hello World"
)
exampleDisplayString = agent.DisplayString(
	oidstr  = "EXAMPLE-MIB::exampleDisplayString",
	initval = "Nice to meet you"
)

# Create the first table
firstTable = agent.Table(
	oidstr = "EXAMPLE-MIB::firstTable",
	indexes = [
		agent.DisplayString()
	],
	columns = [
		(2, agent.DisplayString("Unknown place")),
		(3, agent.Integer32(0))
	],
	counterobj = agent.Unsigned32(
		oidstr = "EXAMPLE-MIB::firstTableNumber"
	)
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
	oidstr = "EXAMPLE-MIB::secondTable",
	indexes = [
		agent.Integer32()
	],
	columns = [
		(2, agent.DisplayString("Unknown interface")),
		(3, agent.Unsigned32())
	],
	counterobj = agent.Unsigned32(
		oidstr = "EXAMPLE-MIB::secondTableNumber"
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

# Finally, we tell the agent to "start". This actually connects the
# agent to the master agent.
agent.start()

# Helper function that dumps the state of all registered SNMP variables
def DumpRegistered():
	for context in agent.getContexts():
		print "{0}: Registered SNMP objects in Context \"{1}\": ".format(prgname, context)
		vars = agent.getRegistered(context)
		pprint.pprint(vars, width=columns)
		print
DumpRegistered()

# Install a signal handler that terminates our example agent when
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

# The example agent's main loop. We loop endlessly until our signal
# handler above changes the "loop" variable.
print "{0}: Serving SNMP requests, press ^C to terminate...".format(prgname)

loop = True
while (loop):
	# Block and process SNMP requests, if available
	agent.check_and_process()

	# Since we didn't give exampleCounter, exampleCounter64 and exampleTimeTicks
	# a real meaning in the EXAMPLE-MIB, we can basically do with them whatever
	# we want. Here, we just increase them, although in different manners.
	exampleCounter32.update(exampleCounter32.value() + 2)
	exampleCounter64.update(exampleCounter64.value() + 4294967294)
	exampleTimeTicks.update(exampleTimeTicks.value() + 1)
	exampleCounter32Context2.update(exampleCounter32Context2.value() + 1)
	exampleCounter64Context2.update(exampleCounter64Context2.value() + 1)

print "{0}: Terminating.".format(prgname)
