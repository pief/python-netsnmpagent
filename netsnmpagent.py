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

class netsnmpAgent(object):
	""" Implements an SNMP agent using the net-snmp libraries. """

	def __init__(self, **args):
		"""Initializes a new netsnmpAgent instance.
		
		"args" is a dictionary that can contain the following optional
		parameters:
		
		- AgentName: The agent's name used for registration with
		             net-snmp.
		- MasterSocket: The Unix domain socket of the running snmpd
		                instance to connect to. Useful for automatic
		                testing with a custom user-space snmpd instance.
		- MIBFiles: A list of filenames of MIBs to be loaded. Required
		            if the OIDs, for which variables will be registered,
		            do not belong to standard MIBs and the custom MIBs
		            are not located in net-snmp's default MIB path
		            (/usr/share/snmp/mibs).
		"""

		# From include/net-snmp/library/default_store.h
		NETSNMP_DS_APPLICATION_ID	= 1

		# From include/net-snmp/agent/ds_agent.h
		NETSNMP_DS_AGENT_ROLE		= 1
		NETSNMP_DS_AGENT_X_SOCKET   = 1

		# Default settings
		defaults = {
			"AgentName"		: os.path.splitext(os.path.basename(sys.argv[0]))[0],
			"MasterSocket"	: None,
			"MIBFiles"		: None
		}
		for key in defaults:
			setattr(self, key, args.get(key, defaults[key]))
		if self.MIBFiles != None and not type(self.MIBFiles) in (list, tuple):
			self.MIBFiles = (self.MIBFiles,)

		# Get access to net-snmp's libraries through ctypes
		for (var,libname) in [
			("agentlib","netsnmpagent"),
		]:
			try:
				exec "self.%s = ctypes.cdll.LoadLibrary(ctypes.util." \
				     "find_library(\"%s\"))" % (var,libname)
			except:
				raise netsnmpAgentException("Could not load library \"%s\"!" % libname)

		# FIXME: log errors to stdout for now
		self.agentlib.snmp_enable_stderrlog()

		# Make us an AgentX client
		args = [
			NETSNMP_DS_APPLICATION_ID,
			NETSNMP_DS_AGENT_ROLE,
			1
		]
		self.agentlib.netsnmp_ds_set_boolean(*args)

		# Use an alternative Unix domain socket to connect to the master?
		if self.MasterSocket:
			args = [
				NETSNMP_DS_APPLICATION_ID,
				NETSNMP_DS_AGENT_X_SOCKET,
				self.MasterSocket
			]
			self.agentlib.netsnmp_ds_set_string(*args)

		# Initialize net-snmp library (see netsnmp_agent_api(3))
		if self.agentlib.init_agent(self.AgentName) != 0:
			raise netsnmpAgentException("init_agent() failed!")

		# Initialize MIB parser
		self.agentlib.netsnmp_init_mib()

		# If MIBFiles were specified (ie. MIBs that can not be found in
		# net-snmp's default MIB directory /usr/share/snmp/mibs), read
		# them in so we can translate OIDs in oidstr2oid()
		if self.MIBFiles:
			for mib in self.MIBFiles:
				print mib
				if self.agentlib.read_mib(mib) == 0:
					raise netsnmpAgentException("netsnmp_read_module({0}) failed!".format(mib))

	def start(self):
		""" Starts the agent. Among other things, this means connecting
		    to the master agent, if configured that way. """
		self.agentlib.init_snmp(self.AgentName);

	def __del__(self):
		if (self.agentlib):
			self.agentlib.snmp_shutdown(self.AgentName)

	def oidstr2oid(self, oidstr):
		""" Converts a textual or numeric OID into net-snmp's internal
		    OID representation. """

		# From net-snmp's include/net-snmp/library/oid.h
		c_oid = ctypes.c_ulong

		# From net-snmp's include/net-snmp/types.h
		MAX_OID_LEN = 128

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
		if self.agentlib.read_objid(*args) == 0:
			raise netsnmpAgentException("read_objid({0}) failed!".format(oidstr))

		# Now we know the length and return a copy of just the required
		# length
		final_oid = (c_oid * work_oid_len.value)(*work_oid[0:work_oid_len.value])
		return (final_oid, work_oid_len.value)

	def registerInstance(self, name, var, oidstr, type):
		# From include/net-snmp/agent/agent_handler.h
		HANDLER_CAN_GETANDGETNEXT	= 0x01
		HANDLER_CAN_SET             = 0x02
		HANDLER_CAN_RWRITE			= (HANDLER_CAN_GETANDGETNEXT |
									   HANDLER_CAN_SET)

		# From include/net-snmp/library/asn1.h
		ASN_INTEGER					= 0x02
		ASN_OCTET_STR				= 0x04
		ASN_APPLICATION				= 0x40

		# From include/net-snmp/library/snmp_impl.h
		ASN_UNSIGNED				= (ASN_APPLICATION | 2)

		# From include/net-snmp/agent/watcher.h
		WATCHER_FIXED_SIZE			= 0x01
		WATCHER_SIZE_STRLEN         = 0x08

		watcher_args = {
			"Integer32": {
				"flags"		: WATCHER_FIXED_SIZE,
				"data_size"	: ctypes.sizeof(ctypes.c_long()),
				"max_size"	: ctypes.sizeof(ctypes.c_long()),
				"asn_type"	: ASN_INTEGER
			},
			"Unsigned32": {
				"flags"		: WATCHER_FIXED_SIZE,
				"data_size"	: ctypes.sizeof(ctypes.c_long()),
				"max_size"	: ctypes.sizeof(ctypes.c_long()),
				"asn_type"	: ASN_UNSIGNED
			},
			"DisplayString": {
				"flags"		: WATCHER_SIZE_STRLEN,
				"data_size"	: 0,
				"max_size"	: 0,
				"asn_type"	: ASN_OCTET_STR
			},
		}

		(oid, oid_len) = self.oidstr2oid(oidstr)
		registration = self.agentlib.netsnmp_create_handler_registration(
			name,								# const char *name
			None,								# Netsnmp_Node_Handler *handler_access_method
			oid,								# const oid *reg_oid
			oid_len,							# size_t reg_oid_len
			HANDLER_CAN_RWRITE					# int modes
		)
		watcher = self.agentlib.netsnmp_create_watcher_info6(
			var,								# void *data
			watcher_args[type]["data_size"],	# size_t size
			watcher_args[type]["asn_type"],		# u_char type
			watcher_args[type]["flags"],		# int flags
			watcher_args[type]["max_size"],		# size_t max_size
			None								# size_t *size_p
		)
		return self.agentlib.netsnmp_register_watched_instance(
			registration,
			watcher
		)

	def poll(self):
		return self.agentlib.agent_check_and_process(1)

class netsnmpAgentException(Exception):
	pass

#~ class netsnmpVar(object):
	#~ def __init__(self, agent):
		#~ if type(agent) != "netsmmpAgent":
			#~ raise netsnmpVariableException("Need a netsnmpAgent instance!")
#~ 
		#~ self._value = None

#~ class netsnmpVarException(Exception):
	#~ pass

#~ class netsnmpLongInt(int):
	#~ def __new__(cls, val):
		#~ instance = int.__new__(cls, val)
		#~ instance._cval = ctypes.c_long(val)
		#~ return instance
#~ 
	#~ def cval(self):
		#~ return self._cval.value
