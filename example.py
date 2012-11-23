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
import ctypes

# This example agent will serve some scalar variables. As we have to
# pass them to net-snmp's C API, the variables must be of types
# ctypes.c_ulong, ctypes.c_long etc.
#
# We initialize them here and will modify them later in our main
# loop below.
exampleInteger		= ctypes.c_long(0)
exampleIntegerRO	= ctypes.c_long(0)
exampleUnsigned		= ctypes.c_ulong(0)
exampleUnsignedRO	= ctypes.c_ulong(0)
exampleString		= ctypes.c_char_p("Test string")

# First, we initialize the netsnmpAgent class itself. We specify the
# fully-qualified path to EXAMPLE-MIB.txt ourselves here, so that you
# don't have to copy the MIB to /usr/share/snmp/mibs.
agent = netsnmpagent.netsnmpAgent(
	AgentName    = "ExampleAgent",
	MasterSocket = "/var/run/agentx/master",
	MIBFiles     = [ os.path.abspath(os.path.dirname(sys.argv[0])) +
	                 "/EXAMPLE-MIB.txt" ]
)

# Then we register all SNMP variables we're willing to serve. Since
# we want the net-snmp C API to access (and modify) variables that are
# under our control (ie. not under the netsnmpagent module's control),
# we must make sure that we pass a C-style pointer to the variable
# itself (to its memory location, to be precisely). This is achieved
# by using ctypes.byref(<variablename>). 
agent.registerInstance("exampleInteger",
                       ctypes.byref(exampleInteger),
                       "EXAMPLE-MIB::exampleInteger",
                       "Integer32",
                       False)

agent.registerInstance("exampleIntegerRO",
                       ctypes.byref(exampleIntegerRO),
                       "EXAMPLE-MIB::exampleIntegerRO",
                       "Integer32",
                       True)

agent.registerInstance("exampleUnsigned",
                       ctypes.byref(exampleUnsigned),
                       "EXAMPLE-MIB::exampleUnsigned",
                       "Unsigned32",
                       False)

agent.registerInstance("exampleUnsignedRO",
                       ctypes.byref(exampleUnsignedRO),
                       "EXAMPLE-MIB::exampleUnsignedRO",
                       "Unsigned32",
                       True)

agent.registerInstance("exampleString",
                       exampleString,
                       "EXAMPLE-MIB::exampleString",
                       "DisplayString",
                       False)

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
	agent.poll()

print "Terminating."
