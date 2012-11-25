#
# python-netsnmpagent module
#
# Copyright (c) 2012 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Public License (GPL) version 3
#

"""Allows to write net-snmp subagents in Python.

The Python bindings that ship with net-snmp support client operations
only. I fixed a couple of issues in the existing python-agentx module
but eventually to rewrite a new module from scratch due to design
issues. For example, it implemented its own handler for registered SNMP
variables, which requires re-doing a lot of stuff which net-snmp
actually takes care of in its API's helpers.

This module, by contrast, concentrates on wrapping the net-snmp C API
for SNMP subagents in an easy manner. It is still under heavy
development and some features are yet missing."""

import sys, os
import ctypes, ctypes.util

# include/net-snmp/library/default_store.h
NETSNMP_DS_APPLICATION_ID   = 1

# include/net-snmp/agent/ds_agent.h
NETSNMP_DS_AGENT_ROLE       = 1
NETSNMP_DS_AGENT_X_SOCKET   = 1

# include/net-snmp/library/oid.h
c_oid                       = ctypes.c_ulong

# include/net-snmp/types.h
MAX_OID_LEN                 = 128

# include/net-snmp/agent/agent_handler.h
HANDLER_CAN_GETANDGETNEXT   = 0x01
HANDLER_CAN_SET             = 0x02
HANDLER_CAN_RONLY           = HANDLER_CAN_GETANDGETNEXT
HANDLER_CAN_RWRITE          = (HANDLER_CAN_GETANDGETNEXT | HANDLER_CAN_SET)

# include/net-snmp/library/asn1.h
ASN_INTEGER                 = 0x02
ASN_OCTET_STR               = 0x04
ASN_APPLICATION             = 0x40

# include/net-snmp/library/snmp_impl.h
ASN_IPADDRESS               = ASN_APPLICATION | 0
ASN_COUNTER                 = ASN_APPLICATION | 1
ASN_UNSIGNED                = ASN_APPLICATION | 2
ASN_TIMETICKS               = ASN_APPLICATION | 3

# From include/net-snmp/agent/watcher.h
WATCHER_FIXED_SIZE          = 0x01
WATCHER_SIZE_STRLEN         = 0x08

class netsnmpAgent(object):
	""" Implements an SNMP agent using the net-snmp libraries. """

	def __init__(self, **args):
		"""Initializes a new netsnmpAgent instance.
		
		"args" is a dictionary that can contain the following
		optional parameters:
		
		- AgentName:    The agent's name used for registration
		                with net-snmp.
		- MasterSocket: The Unix domain socket of the running
		                snmpd instance to connect to. Useful for
		                automatic testing with a custom
		                user-space snmpd instance.
		- MIBFiles:     A list of filenames of MIBs to be
		                loaded. Required if the OIDs, for which
		                variables will be registered, do not
		                belong to standard MIBs and the custom
		                MIBs are not located in net-snmp's
		                default MIB path (/usr/share/snmp/mibs). """


		# Default settings
		defaults = {
			"AgentName"     : os.path.splitext(os.path.basename(sys.argv[0]))[0],
			"MasterSocket"  : None,
			"MIBFiles"      : None
		}
		for key in defaults:
			setattr(self, key, args.get(key, defaults[key]))
		if self.MIBFiles != None and not type(self.MIBFiles) in (list, tuple):
			self.MIBFiles = (self.MIBFiles,)

		# Get access to libnetsnmpagent
		try:
			self._agentlib = ctypes.cdll.LoadLibrary(ctypes.util.find_library("netsnmpagent"))
		except:
			raise netsnmpAgentException("Could not load libnetsnmpagent!")

		# FIXME: log errors to stdout for now
		self._agentlib.snmp_enable_stderrlog()

		# Make us an AgentX client
		args = [
			NETSNMP_DS_APPLICATION_ID,
			NETSNMP_DS_AGENT_ROLE,
			1
		]
		self._agentlib.netsnmp_ds_set_boolean(*args)

		# Use an alternative Unix domain socket to connect to the master?
		if self.MasterSocket:
			args = [
				NETSNMP_DS_APPLICATION_ID,
				NETSNMP_DS_AGENT_X_SOCKET,
				self.MasterSocket
			]
			self._agentlib.netsnmp_ds_set_string(*args)

		# Initialize net-snmp library (see netsnmp_agent_api(3))
		if self._agentlib.init_agent(self.AgentName) != 0:
			raise netsnmpAgentException("init_agent() failed!")

		# Initialize MIB parser
		self._agentlib.netsnmp_init_mib()

		# If MIBFiles were specified (ie. MIBs that can not be found in
		# net-snmp's default MIB directory /usr/share/snmp/mibs), read
		# them in so we can translate OIDs in oidstr2oid()
		if self.MIBFiles:
			for mib in self.MIBFiles:
				if self._agentlib.read_mib(mib) == 0:
					raise netsnmpAgentException("netsnmp_read_module({0}) " +
					                            "failed!".format(mib))

		# Initialize our variable registry
		self._vars = {}
		self._may_addvars = True

	def addVar(self, varclass, oidstr, writable):
		""" Adds a new SNMP variable to the netsnmpAgent object. Only allowed
		    until the agent has been start()ed. """

		# Make sure the agent has not been start()ed yet
		if self._may_addvars == False:
			raise netsnmpAgentException("Attempt to add variable after agent has been started!")

		# Create a new variable instance...
		var = varclass(self._agentlib, oidstr, writable)

		# Better to keep record of which variables have been registered for
		# this agent
		self._vars[oidstr] = var

		return var

	def Integer32(self, oidstr, writable = True):
		return self.addVar(Integer32, oidstr, writable)

	def Unsigned32(self, oidstr, writable = True):
		return self.addVar(Unsigned32, oidstr, writable)

	def Counter32(self, oidstr):
		return self.addVar(Integer32, oidstr, False)

	def TimeTicks(self, oidstr, writable = True):
		return self.addVar(TimeTicks, oidstr, writable)

	def IPAddress(self, oidstr, writable = True):
		return self.addVar(IPAddress, oidstr, writable)

	def OctetString(self, oidstr, writable = True):
		return self.addVar(OctetString, oidstr, writable)

	def DisplayString(self, oidstr, writable = True):
		return self.addVar(DisplayString, oidstr, writable)

	def getVars(self):
		""" Returns a dictionary with the currently registered SNMP variables. """
		myvars = {}
		for (oidstr,varclass) in self._vars.iteritems():
			myvars[oidstr] = {
				"type": type(varclass).__name__,
				"value": varclass.value()
			}
		return myvars

	def start(self):
		""" Starts the agent. Among other things, this means connecting
		    to the master agent, if configured that way. """
		self._agentlib.init_snmp(self.AgentName)

	def poll(self):
		""" Blocks and processes incoming SNMP requests. """
		return self._agentlib.agent_check_and_process(1)

	def __del__(self):
		if (self._agentlib):
			self._agentlib.snmp_shutdown(self.AgentName)
			self._agentlib = None

class netsnmpAgentException(Exception):
	pass

class netsnmpVariable(object):
	def __init__(self, agentlib, oidstr, writable, watcher_args):
		""" Initializes a new netsnmpVariable instance. """

		self._oidstr = oidstr

		# Convert textual OID to net-snmp's internal representation
		(oid, oid_len) = self.oidstr2oid(agentlib, oidstr)

		# Create a handler registration
		registration = agentlib.netsnmp_create_handler_registration(
			oidstr,
			None, # handler_access_method
			oid,
			oid_len,
			HANDLER_CAN_RWRITE if writable else HANDLER_CAN_RONLY # handler_modes
		)

		# Create a watcher to handle the specified SNMP variable
		watcher = agentlib.netsnmp_create_watcher_info6(
			watcher_args["data"],
			watcher_args["data_size"],
			watcher_args["asn_type"],
			watcher_args["flags"],
			watcher_args["max_size"],
			None # size_p
		)

		# Now register both handler and watcher
		result = agentlib.netsnmp_register_watched_instance(
			registration,
			watcher
		)

		return result

	def oidstr2oid(self, agentlib, oidstr):
		""" Converts a textual or numeric OID into net-snmp's internal
		    OID representation. """

		# We can't know the length of the internal OID representation
		# beforehand, so we use a maximum-length buffer for the
		# call to read_objid() below
		work_oid = (c_oid * MAX_OID_LEN)()
		work_oid_len = ctypes.c_size_t(MAX_OID_LEN)
		args = [
			oidstr,
			ctypes.byref(work_oid),
			ctypes.byref(work_oid_len)
		]

		# Let libsnmpagent parse it
		if agentlib.read_objid(*args) == 0:
			raise netsnmpAgentException("read_objid({0}) failed!".format(oidstr))

		# Now we know the length and return a copy of just the required
		# length
		final_oid = (c_oid * work_oid_len.value)(*work_oid[0:work_oid_len.value])
		return (final_oid, work_oid_len.value)

	def value(self):
		return self._cval.value

	def update(self, val):
		self._cval = self._ctype(val)

class netsnmpIntegerVariable(netsnmpVariable):
	def __init__(self, agentlib, oidstr, ctype, asntype, writable):
		self._ctype = ctype
		self._cval = ctype(0)

		watcher_args  = {
			"data"      : ctypes.byref(self._cval),
			"data_size" : ctypes.sizeof(ctype),
			"max_size"  : ctypes.sizeof(ctype),
			"asn_type"  : asntype,
			"flags"     : WATCHER_FIXED_SIZE
		}

		netsnmpVariable.__init__(self, agentlib, oidstr, writable, watcher_args)

class Integer32(netsnmpIntegerVariable):
	def __init__(self, agentlib, oidstr, writable = True):
		netsnmpIntegerVariable.__init__(self, agentlib, oidstr, ctypes.c_long, ASN_INTEGER, writable)

class Unsigned32(netsnmpIntegerVariable):
	def __init__(self, agentlib, oidstr, writable = True):
		netsnmpIntegerVariable.__init__(self, agentlib, oidstr, ctypes.c_ulong, ASN_UNSIGNED, writable)

class Counter32(netsnmpIntegerVariable):
	def __init__(self, agentlib, oidstr):
		netsnmpIntegerVariable.__init__(self, agentlib, oidstr, ctypes.c_ulong, ASN_COUNTER, False)

class TimeTicks(netsnmpIntegerVariable):
	def __init__(self, agentlib, oidstr, writable = True):
		netsnmpIntegerVariable.__init__(self, agentlib, oidstr, ctypes.c_ulong, ASN_TIMETICKS, writable)

class IPAddress(netsnmpIntegerVariable):
	def __init__(self, agentlib, oidstr, writable = True):
		netsnmpIntegerVariable.__init__(self, agentlib, oidstr, ctypes.c_uint, ASN_IPADDRESS, writable)

class OctetString(netsnmpVariable):
	def __init__(self, agentlib, oidstr, writable = True):
		self._ctype = ctypes.c_char_p
		self._cval = ctypes.c_char_p("")

		watcher_args  = {
			"data"      : self._cval,
			"data_size" : 0,
			"max_size"  : 0,
			"asn_type"  : ASN_OCTET_STR,
			"flags"     : WATCHER_SIZE_STRLEN
		}

		netsnmpVariable.__init__(self, agentlib, oidstr, writable, watcher_args)

class DisplayString(OctetString):
	pass
