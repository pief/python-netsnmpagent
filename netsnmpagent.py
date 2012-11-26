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
			"AgentName"    : os.path.splitext(os.path.basename(sys.argv[0]))[0],
			"MasterSocket" : None,
			"MIBFiles"     : None
		}
		for key in defaults:
			setattr(self, key, args.get(key, defaults[key]))
		if self.MIBFiles != None and not type(self.MIBFiles) in (list, tuple):
			self.MIBFiles = (self.MIBFiles,)

		# Get access to libnetsnmpagent
		try:
			libname = ctypes.util.find_library("netsnmpagent")
			self._agentlib = ctypes.cdll.LoadLibrary(libname)
		except:
			raise netsnmpAgentException("Could not load libnetsnmpagent!")

		# FIXME: log errors to stdout for now
		self._agentlib.snmp_enable_stderrlog()

		# Make us an AgentX client
		self._agentlib.netsnmp_ds_set_boolean(
			NETSNMP_DS_APPLICATION_ID,
			NETSNMP_DS_AGENT_ROLE,
			1
		)

		# Use an alternative Unix domain socket to connect to the master?
		if self.MasterSocket:
			self._agentlib.netsnmp_ds_set_string(
				NETSNMP_DS_APPLICATION_ID,
				NETSNMP_DS_AGENT_X_SOCKET,
				self.MasterSocket
			)

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

	def oidstr2oid(self, oidstr):
		""" Converts a textual or numeric OID into net-snmp's internal
			OID representation. """

		# We can't know the length of the internal OID representation
		# beforehand, so we use a maximum-length buffer for the
		# call to read_objid() below
		workoid = (c_oid * MAX_OID_LEN)()
		workoid_len = ctypes.c_size_t(MAX_OID_LEN)

		# Let libsnmpagent parse it
		result = self._agentlib.read_objid(
			oidstr,
			ctypes.byref(workoid),
			ctypes.byref(workoid_len)
		)
		if result == 0:
			raise netsnmpAgentException(
				"read_objid({0}) failed!".format(oidstr)
			)

		# Now we know the length and return a copy of just the required
		# length
		finaloid = (c_oid * workoid_len.value)(*workoid[0:workoid_len.value])
		return (finaloid, workoid_len.value)

	def VarTypeClass(property_func):
		""" Decorator that transforms a simple property_func into a SNMP
		    variable type class generator. property_func returns a dictionary
		    with variable type properties:
		    
		    - "asntype" : A constant defining the SNMP variable type from an
		                  ASN.1 view, eg. ASN_INTEGER
		    - "ctype"   : A reference to the ctypes data type representing the
		                  SNMP variable in the net-snmp C API, eg. ctypes.c_long
		    - "flags"   : A constant for the watcher's "flags" field describing
		                  the C data type's storage, eg. WATCHER_FIXED_SIZE
		    - "initval" : The value to initialize the C data type with, eg. 0
		    - "writable": Whether SNMP write requests should be allowed. For
		                  most variable types, this field will be set to an
		                  propery_func argument "writable", leaving it up to
		                  the module's user to decide.
		    
		    VarTypeClass will add code to generate a suitable class, create an
		    instance of it based on the args originally given to property_func
		    and register it with net-snmp. """

		# This is the function that replaces the original function definition
		def define_and_register(self, oidstr, *args):
			# Make sure the agent has not been start()ed yet
			if self._may_addvars == False:
				raise netsnmpAgentException("Attempt to add variable after " \
				                            "agent has been started!")

			# property_func is by convention named after the variable type
			vartype = property_func.__name__

			# Call the original property_func to retrieve this variable type's
			# properties such as asntype etc.
			#
			# Passing "oidstr" to property_func won't have any effect since we
			# use it ourselves below, however we must pass it on neitherless
			# since it's part of property_func's function signature which
			# THIS function shares due to the way Python decorators work.
			props = property_func(self, oidstr, *args)

			# Here we define the variable type class whose instance will be
			# returned to the user. Python does not know anonymous classes, so
			# we need to give the class a name. Since the part behind the
			# "class" keyword can't be a variable, we use a proxy name "cls"
			# and overwrite its __name__ property after class creation. The
			# class will be named after vartype, thus yielding the effect that
			# calling foo() will return a "foo" class instance.
			class cls(object):
				def __init__(self):
					self._cval = props["ctype"](props["initval"])

				def value(self):
					return self._cval.value

				def update(self, val):
					self._cval = props["ctype"](val)
			cls.__name__ = vartype

			# Define the class's instance. To use "vartype" here we would
			# have to use "exec", which is superfluous since we still have
			# the "cls" reference. The class will still have the right name.
			var = cls()

			# Convert textual OID to net-snmp's internal representation
			(oid, oid_len) = self.oidstr2oid(oidstr)

			# Create the net-snmp handler registration
			handler_modes = HANDLER_CAN_RWRITE if props["writable"] \
			                                   else HANDLER_CAN_RONLY
			registration = self._agentlib.netsnmp_create_handler_registration(
				oidstr,
				None, # handler_access_method
				oid,
				oid_len,
				handler_modes
			)

			# Create the net-snmp watcher to handle the variable
			data = var._cval if props["ctype"] == ctypes.c_char_p \
			                 else ctypes.byref(var._cval)
			watcher = self._agentlib.netsnmp_create_watcher_info6(
				data,                           # data
				ctypes.sizeof(props["ctype"]),  # data_size
				props["asntype"],               # asn_type
				props["flags"],                 # flags
				ctypes.sizeof(props["ctype"]),  # max_size
				None                            # size_p
			)

			# Now register both handler and watcher
			result = self._agentlib.netsnmp_register_watched_instance(
				registration,
				watcher
			)
			if result != 0:
				raise netsnmpAgentException("Error registering SNMP variable!")

			# Better to keep record of which variables have been registered for
			# this agent
			self._vars[oidstr] = var

			return var

		return define_and_register

	@VarTypeClass
	def Integer32(self, oidstr, writable = True):
		return {
			"asntype"   : ASN_INTEGER,
			"ctype"     : ctypes.c_long,
			"flags"     : WATCHER_FIXED_SIZE,
			"initval"   : 0,
			"writable"  : writable
		}

	@VarTypeClass
	def Unsigned32(self, oidstr, writable = True):
		return {
			"asntype"   : ASN_UNSIGNED,
			"ctype"     : ctypes.c_ulong,
			"flags"     : WATCHER_FIXED_SIZE,
			"initval"   : 0,
			"writable"  : writable
		}

	@VarTypeClass
	def Counter32(self, oidstr):
		return {
			"asntype"   : ASN_COUNTER,
			"ctype"     : ctypes.c_ulong,
			"flags"     : WATCHER_FIXED_SIZE,
			"initval"   : 0,
			"writable"  : False
		}

	@VarTypeClass
	def TimeTicks(self, oidstr, writable = True):
		return {
			"asntype"   : ASN_TIMETICKS,
			"ctype"     : ctypes.c_ulong,
			"flags"     : WATCHER_FIXED_SIZE,
			"initval"   : 0,
			"writable"  : writable
		}

	@VarTypeClass
	def IPAddress(self, oidstr, writable = True):
		return {
			"asntype"   : ASN_IPADDRESS,
			"ctype"     : ctypes.c_uint,
			"flags"     : WATCHER_FIXED_SIZE,
			"initval"   : 0,
			"writable"  : writable
		}

	@VarTypeClass
	def OctetString(self, oidstr, writable = True):
		return {
			"asntype"   : ASN_OCTET_STR,
			"ctype"     : ctypes.c_char_p,
			"flags"     : WATCHER_SIZE_STRLEN,
			"initval"   : "",
			"writable"  : writable
		}

	@VarTypeClass
	def DisplayString(self, oidstr, writable = True):
		return {
			"asntype"   : ASN_OCTET_STR,
			"ctype"     : ctypes.c_char_p,
			"flags"     : WATCHER_SIZE_STRLEN,
			"initval"   : "",
			"writable"  : writable
		}

	def getVars(self):
		""" Returns a dictionary with the currently registered SNMP
		    variables. """
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
