#!/usr/bin/env python
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
from netsnmpapi import *

# Maximum string size supported by python-netsnmpagent
MAX_STRING_SIZE                 = 1024

class netsnmpAgent(object):
	""" Implements an SNMP agent using the net-snmp libraries. """

	def __init__(self, **args):
		"""Initializes a new netsnmpAgent instance.
		
		"args" is a dictionary that can contain the following
		optional parameters:
		
		- AgentName    : The agent's name used for registration with net-snmp.
		- MasterSocket : The Unix domain socket of the running snmpd instance to
		                 connect to. Change this if you want to use a custom
		                 snmpd instance, eg. in example.sh or for automatic
		                 testing.
		- PersistentDir: The directory to use to store persistance information.
		                 Change this if you want to use a custom snmpd instance,
		                 eg. in example.sh or for automatic testing.
		- MIBFiles     : A list of filenames of MIBs to be loaded. Required if
		                 the OIDs, for which variables will be registered, do
		                 not belong to standard MIBs and the custom MIBs are not
		                 located in net-snmp's default MIB path
		                 (/usr/share/snmp/mibs). """

		# Default settings
		defaults = {
			"AgentName"    : os.path.splitext(os.path.basename(sys.argv[0]))[0],
			"MasterSocket" : None,
			"PersistentDir": None,
			"MIBFiles"     : None
		}
		for key in defaults:
			setattr(self, key, args.get(key, defaults[key]))
		if self.MIBFiles != None and not type(self.MIBFiles) in (list, tuple):
			self.MIBFiles = (self.MIBFiles,)

		# FIXME: log errors to stdout for now
		libnsa.snmp_enable_stderrlog()

		# Make us an AgentX client
		libnsa.netsnmp_ds_set_boolean(
			NETSNMP_DS_APPLICATION_ID,
			NETSNMP_DS_AGENT_ROLE,
			1
		)

		# Use an alternative Unix domain socket to connect to the master?
		if self.MasterSocket:
			libnsa.netsnmp_ds_set_string(
				NETSNMP_DS_APPLICATION_ID,
				NETSNMP_DS_AGENT_X_SOCKET,
				self.MasterSocket
			)

		# Use an alternative persistence directory?
		if self.PersistentDir:
			libnsa.netsnmp_ds_set_string(
				NETSNMP_DS_LIBRARY_ID,
				NETSNMP_DS_LIB_PERSISTENT_DIR,
				ctypes.c_char_p(self.PersistentDir)
			)

		# Initialize net-snmp library (see netsnmp_agent_api(3))
		if libnsa.init_agent(self.AgentName) != 0:
			raise netsnmpAgentException("init_agent() failed!")

		# Initialize MIB parser
		libnsa.netsnmp_init_mib()

		# If MIBFiles were specified (ie. MIBs that can not be found in
		# net-snmp's default MIB directory /usr/share/snmp/mibs), read
		# them in so we can translate OID strings to net-snmp's internal OID
		# format.
		if self.MIBFiles:
			for mib in self.MIBFiles:
				if libnsa.read_mib(mib) == 0:
					raise netsnmpAgentException("netsnmp_read_module({0}) " +
					                            "failed!".format(mib))

		# Initialize our SNMP object registry
		self._objs    = {}
		self._started = False

	def _prepareRegistration(self, oidstr, writable = True):
		""" Prepares the registration of an SNMP object.

		    "oidstr" is the OID to register the object at.
		    "writable" indicates whether "snmpset" is allowed. """

		# Make sure the agent has not been start()ed yet
		if self._started == True:
			raise netsnmpAgentException("Attempt to register SNMP object " \
			                            "after agent has been started!")

		# We can't know the length of the internal OID representation
		# beforehand, so we use a MAX_OID_LEN sized buffer for the call to
		# read_objid() below
		oid = (c_oid * MAX_OID_LEN)()
		oid_len = ctypes.c_size_t(MAX_OID_LEN)

		# Let libsnmpagent parse the OID
		if libnsa.read_objid(
			oidstr,
			ctypes.cast(ctypes.byref(oid), ctypes.POINTER(ctypes.c_ulong)),
			ctypes.byref(oid_len)
		) == 0:
			raise netsnmpAgentException("read_objid({0}) failed!".format(oidstr))

		# Do we allow SNMP SETting to this OID?
		handler_modes = HANDLER_CAN_RWRITE if writable \
		                                   else HANDLER_CAN_RONLY

		# Create the netsnmp_handler_registration structure. It notifies
		# net-snmp that we will be responsible for anything below the given
		# OID. We use this for leaf nodes only, processing of subtress will be
		# left to net-snmp.
		handler_reginfo = libnsa.netsnmp_create_handler_registration(
			oidstr,
			None,
			oid,
			oid_len,
			handler_modes
		)

		return handler_reginfo

	def VarTypeClass(property_func):
		""" Decorator that transforms a simple property_func into a class
		    factory returning instances of a class for the particular SNMP
		    variable type. property_func is supposed to return a dictionary with
		    the following elements:
		    - "ctype"           : A reference to the ctypes constructor method
		                          yielding the appropriate C representation of
		                          the SNMP variable, eg. ctypes.c_long or
		                          ctypes.create_string_buffer.
		    - "flags"           : A net-snmp constant describing the C data
		                          type's storage behavior, currently either
		                          WATCHER_FIXED_SIZE or WATCHER_SIZE_STRLEN.
		    - "max_size"        : The maximum allowed string size if "flags"
		                          has been set to WATCHER_SIZE_STRLEN.
		    - "initval"         : The value to initialize the C data type with,
		                          eg. 0 or "".
		    - "asntype"         : A constant defining the SNMP variable type
		                          from an ASN.1 perspective, eg. ASN_INTEGER.
		
		    The class instance returned will have no association with net-snmp
		    yet. Use the Register() method to associate it with an OID. """

		# This is the replacement function, the "decoration"
		def create_vartype_class(self, oidstr = None, initval = None, writable = True):
			agent = self

			# Call the original property_func to retrieve this variable type's
			# properties. Passing "initval" to property_func may seem pretty
			# useless as it won't have any effect and we use it ourselves below.
			# However we must supply it nevertheless since it's part of
			# property_func's function signature which THIS function shares.
			# That's how Python's decorators work.
			props = property_func(self, initval)

			# Use variable type's default initval if we weren't given one
			if initval == None:
				initval = props["initval"]

			# Create a class to wrap ctypes' access semantics and enable
			# Register() to do class-specific registration work.
			#
			# Since the part behind the "class" keyword can't be a variable, we
			# use the proxy name "cls" and overwrite its __name__ property
			# after class creation.
			class cls(object):
				def __init__(self):
					for prop in ["flags", "asntype"]:
						setattr(self, "_{0}".format(prop), props[prop])

					# Create the ctypes class instance representing the variable
					# to be handled by the net-snmp C API. If this variable type
					# has no fixed size, pass the maximum size as second
					# argument to the constructor.
					if props["flags"] == WATCHER_FIXED_SIZE:
						self._cvar      = props["ctype"](initval)
						self._data_size = ctypes.sizeof(self._cvar)
						self._max_size  = self._data_size
					else:
						self._cvar      = props["ctype"](initval, props["max_size"])
						self._data_size = len(self._cvar.value)
						self._max_size  = max(self._data_size, props["max_size"])

					if oidstr:
						# Prepare the netsnmp_handler_registration structure.
						handler_reginfo = agent._prepareRegistration(oidstr, writable)

						# Create the netsnmp_watcher_info structure.
						watcher = libnsa.netsnmp_create_watcher_info6(
							self.cref(),
							self._data_size,
							self._asntype,
							self._flags,
							self._max_size,
							None
						)

						# Register handler and watcher with net-snmp.
						result = libnsa.netsnmp_register_watched_instance(
							handler_reginfo,
							watcher
						)
						if result != 0:
							raise netsnmpAgentException("Error registering variable with net-snmp!")

						# Finally, we keep track of all registered SNMP objects for the
						# getRegistered() method.
						agent._objs[oidstr] = self

				def value(self):
					return self._cvar.value

				def cref(self):
					return ctypes.byref(self._cvar) if self._flags == WATCHER_FIXED_SIZE \
					                                else self._cvar

				def update(self, val):
					self._cvar.value = val
					if props["flags"] == WATCHER_SIZE_STRLEN:
						if len(val) > self._max_size:
							raise netsnmpAgentException(
								"Value passed to update() truncated: {0} > {1} "
								"bytes!".format(len(val), self._max_size))
						self._cvar.value = val
						self._data_size  = len(val)

			cls.__name__ = property_func.__name__

			# Return an instance of the just-defined class to the agent
			return cls()

		return create_vartype_class

	@VarTypeClass
	def Integer32(self, oidstr = None, initval = None, writable = True):
		return {
			"ctype"         : ctypes.c_long,
			"flags"         : WATCHER_FIXED_SIZE,
			"initval"       : 0,
			"asntype"       : ASN_INTEGER
		}

	@VarTypeClass
	def Unsigned32(self, oidstr = None, initval = None, writable = True):
		return {
			"ctype"         : ctypes.c_ulong,
			"flags"         : WATCHER_FIXED_SIZE,
			"initval"       : 0,
			"asntype"       : ASN_UNSIGNED
		}

	@VarTypeClass
	def Counter32(self, oidstr = None, initval = None, writable = True):
		return {
			"ctype"         : ctypes.c_ulong,
			"flags"         : WATCHER_FIXED_SIZE,
			"initval"       : 0,
			"asntype"       : ASN_COUNTER
		}

	@VarTypeClass
	def TimeTicks(self, oidstr = None, initval = None, writable = True):
		return {
			"ctype"         : ctypes.c_ulong,
			"flags"         : WATCHER_FIXED_SIZE,
			"initval"       : 0,
			"asntype"       : ASN_TIMETICKS
		}

	@VarTypeClass
	def IpAddress(self, oidstr = None, initval = None, writable = True):
		return {
			"ctype"         : ctypes.c_uint,
			"flags"         : WATCHER_FIXED_SIZE,
			"initval"       : 0,
			"asntype"       : ASN_IPADDRESS
		}

	# Note we can't use ctypes.c_char_p here since that creates an immutable
	# type and net-snmp _can_ modify the buffer (unless writable is False).
	@VarTypeClass
	def OctetString(self, oidstr = None, initval = None, writable = True):
		return {
			"ctype"         : ctypes.create_string_buffer,
			"flags"         : WATCHER_SIZE_STRLEN,
			"max_size"      : MAX_STRING_SIZE,
			"initval"       : "",
			"asntype"       : ASN_OCTET_STR
		}

	# Whereas an OctetString can contain UTF-8 encoded characters, a
	# DisplayString is restricted to ASCII characters only.
	@VarTypeClass
	def DisplayString(self, oidstr = None, initval = None, writable = True):
		return {
			"ctype"         : ctypes.create_string_buffer,
			"flags"         : WATCHER_SIZE_STRLEN,
			"max_size"      : MAX_STRING_SIZE,
			"initval"       : "",
			"asntype"       : ASN_OCTET_STR
		}

	def getRegistered(self):
		""" Returns a dictionary with the currently registered SNMP objects. """
		myobjs = {}
		for (oidstr,snmpobj) in self._objs.iteritems():
			myobjs[oidstr] = {
				"type": type(snmpobj).__name__,
				"value": snmpobj.value()
			}
		return myobjs

	def start(self):
		""" Starts the agent. Among other things, this means connecting
		    to the master agent, if configured that way. """
		self._started = True
		libnsa.init_snmp(self.AgentName)

	def poll(self):
		""" Blocks and processes incoming SNMP requests. """
		return libnsa.agent_check_and_process(1)

	def __del__(self):
		libnsa.snmp_shutdown(self.AgentName)

class netsnmpAgentException(Exception):
	pass
