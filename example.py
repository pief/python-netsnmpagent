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
import netsnmpagent

# First, create an instance of the netsnmpAgent class. We specify the
# fully-qualified path to EXAMPLE-MIB.txt ourselves here, so that you
# don't have to copy the MIB to /usr/share/snmp/mibs.
agent = netsnmpagent.netsnmpAgent(
	AgentName    = "ExampleAgent",
	MasterSocket = "/var/run/agentx/master",
	MIBFiles     = [ os.path.abspath(os.path.dirname(sys.argv[0])) +
	                 "/EXAMPLE-MIB.txt" ]
)

# Then we create all SNMP variables we're willing to serve.
exampleInteger    = agent.Integer32("EXAMPLE-MIB::exampleInteger")
exampleIntegerRO  = agent.Integer32("EXAMPLE-MIB::exampleIntegerRO", False)
exampleUnsigned   = agent.Unsigned32("EXAMPLE-MIB::exampleUnsigned")
exampleUnsignedRO = agent.Unsigned32("EXAMPLE-MIB::exampleUnsignedRO", False)
exampleCounter    = agent.Counter32("EXAMPLE-MIB::exampleCounter")
exampleTimeTicks  = agent.TimeTicks("EXAMPLE-MIB::exampleTimeTicks")
exampleIPAddress  = agent.IPAddress("EXAMPLE-MIB::exampleIPAddress")
exampleString     = agent.DisplayString("EXAMPLE-MIB::exampleString")

# Just to verify that all variables were created successfully. You wouldn't
# need to do this in production code.
print "Registered SNMP variables: "
vars = agent.getVars().__str__()
print vars.replace("},", "}\n")

# Finally, we tell the agent to "start". This actually connects the
# agent to the master agent.
agent.start()

# Install a signal handler that terminates our example agent when
# CTRL-C is pressed or a KILL signal is received
def TermHandler(signum, frame):
	global loop
	loop = False
signal.signal(signal.SIGINT, TermHandler)
signal.signal(signal.SIGTERM, TermHandler)

# The example agent's main loop. We loop endlessly until our signal
# handler above changes the "loop" variable.
print "Serving SNMP requests, press ^C to terminate..."

loop = True
while (loop):
	# Block until something happens
	agent.poll()

	# Since we didn't give exampleCounter and exampleTimeTicks a real
	# meaning in the EXAMPLE-MIB, we can basically do with them whatever
	# we want. Here, we just increase both, although in different manners.
	exampleCounter.update(exampleCounter.value() + 2)
	exampleTimeTicks.update(exampleTimeTicks.value() + 1)

print "Terminating."
