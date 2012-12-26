#!/usr/bin/env python
#
# python-netsnmpagent example agent
#
# Copyright (c) 2012 Pieter Hollants <pieter@hollants.com>
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
import netsnmpagent

prgname = sys.argv[0]

# Process command line arguments
parser = optparse.OptionParser()
parser.add_option(
	"-m",
	"--master-socket",
	dest="mastersocket",
	help="Sets the path to the master agent's AgentX unix domain socket",
	default="/var/run/agentx/master"
)
parser.add_option(
	"-p",
	"--persistent-dir",
	dest="persistentdir",
	help="Sets the path to the persistance directory",
	default="/var/lib/net-snmp"
)
(options, args) = parser.parse_args()

# First, create an instance of the netsnmpAgent class. We specify the
# fully-qualified path to EXAMPLE-MIB.txt ourselves here, so that you
# don't have to copy the MIB to /usr/share/snmp/mibs.
agent = netsnmpagent.netsnmpAgent(
	AgentName     = "ExampleAgent",
	MasterSocket  = options.mastersocket,
	PersistentDir = options.persistentdir,
	MIBFiles      = [ os.path.abspath(os.path.dirname(sys.argv[0])) +
	                  "/EXAMPLE-MIB.txt" ]
)

# Then we create all SNMP scalar variables we're willing to serve.
exampleInteger = agent.Integer32(
	oidstr = "EXAMPLE-MIB::exampleInteger"
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
exampleCounter = agent.Counter32(
	oidstr = "EXAMPLE-MIB::exampleCounter"
)
exampleTimeTicks = agent.TimeTicks(
	oidstr = "EXAMPLE-MIB::exampleTimeTicks"
)
exampleIpAddress = agent.IpAddress(
	oidstr = "EXAMPLE-MIB::exampleIpAddress"
)
exampleOctetString = agent.OctetString(
	oidstr  = "EXAMPLE-MIB::exampleOctetString",
	initval = "Hello World"
)
exampleDisplayString = agent.DisplayString(
	oidstr  = "EXAMPLE-MIB::exampleDisplayString",
	initval = "Nice to meet you"
)

# Create a table
exampleTable = agent.Table(
	oidstr = "EXAMPLE-MIB::exampleTable",
	indexes = [
		agent.DisplayString()
	],
	columns = [
		(2, agent.DisplayString(initval="Unknown place")),
		(3, agent.Integer32(initval=0))
	]
)

# First table row
exampleRow1 = exampleTable.addRow([agent.DisplayString(initval="aa")])
exampleRow1.setRowCell(2, agent.DisplayString(initval="Prague"))
exampleRow1.setRowCell(3, agent.Integer32(initval=20))

# Second table row
exampleRow2 = exampleTable.addRow([agent.DisplayString(initval="ab")])
exampleRow2.setRowCell(2, agent.DisplayString(initval="Barcelona"))
exampleRow2.setRowCell(3, agent.Integer32(initval=28))

# Third table row
exampleRow3 = exampleTable.addRow([agent.DisplayString(initval="bb")])
exampleRow3.setRowCell(3, agent.Integer32(initval=18))

# Finally, we tell the agent to "start". This actually connects the
# agent to the master agent.
agent.start()

# Helper function that dumps the state of all registered SNMP variables
def DumpRegistered():
	print "{0}: Registered SNMP objects: ".format(prgname)
	vars = agent.getRegistered().__str__()
	print vars.replace("},", "}\n")
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
	# Block until something happens
	agent.poll()

	# Since we didn't give exampleCounter and exampleTimeTicks a real
	# meaning in the EXAMPLE-MIB, we can basically do with them whatever
	# we want. Here, we just increase both, although in different manners.
	exampleCounter.update(exampleCounter.value() + 2)
	exampleTimeTicks.update(exampleTimeTicks.value() + 1)

print "{0}: Terminating.".format(prgname)
