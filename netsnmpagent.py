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
		if libnsa.netsnmp_ds_set_boolean(
			NETSNMP_DS_APPLICATION_ID,
			NETSNMP_DS_AGENT_ROLE,
			1
		) != SNMPERR_SUCCESS:
			raise netsnmpAgentException(
				"netsnmp_ds_set_boolean() failed for NETSNMP_DS_AGENT_ROLE!"
			)

		# Use an alternative Unix domain socket to connect to the master?
		if self.MasterSocket:
			if libnsa.netsnmp_ds_set_string(
				NETSNMP_DS_APPLICATION_ID,
				NETSNMP_DS_AGENT_X_SOCKET,
				self.MasterSocket
			) != SNMPERR_SUCCESS:
				raise netsnmpAgentException(
					"netsnmp_ds_set_string() failed for NETSNMP_DS_AGENT_X_SOCKET!"
				)

		# Use an alternative persistence directory?
		if self.PersistentDir:
			if libnsa.netsnmp_ds_set_string(
				NETSNMP_DS_LIBRARY_ID,
				NETSNMP_DS_LIB_PERSISTENT_DIR,
				ctypes.c_char_p(self.PersistentDir)
			) != SNMPERR_SUCCESS:
				raise netsnmpAgentException(
					"netsnmp_ds_set_string() failed for NETSNMP_DS_LIB_PERSISTENT_DIR!"
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
			ctypes.cast(ctypes.byref(oid), c_oid_p),
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
	def Counter64(self, oidstr = None, initval = None, writable = True):
		return {
			"ctype"         : counter64,
			"flags"         : WATCHER_FIXED_SIZE,
			"initval"       : 0,
			"asntype"       : ASN_COUNTER64
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

	def Table(self, oidstr, indexes, columns, extendable = False):
		agent = self

		# Define a Python class to provide access to the table.
		class Table(object):
			def __init__(self, oidstr, idxobjs, coldefs, extendable):
				# Create a netsnmp_table_data_set structure, representing both
				# the table definition and the data stored inside it. We use the
				# oidstr as table name.
				self._dataset = libnsa.netsnmp_create_table_data_set(
					ctypes.c_char_p(oidstr)
				)

				# Define the table row's indexes
				for idxobj in idxobjs:
					libnsa.netsnmp_table_dataset_add_index(
						self._dataset,
						idxobj._asntype
					)

				# Define the table's columns and their default values
				for coldef in coldefs:
					colno    = coldef[0]
					defobj   = coldef[1]
					writable = coldef[2] if len(coldef) > 2 \
					                     else 0

					# netsnmp_table_set_add_default_row() ignores the ASN type,
					# so it doesn't implement any special handling for the
					# trailing zero byte in C strings
					size = defobj._data_size + 1 if defobj._asntype == ASN_OCTET_STR \
												 else defobj._data_size
					result = libnsa.netsnmp_table_set_add_default_row(
						self._dataset,
						colno,
						defobj._asntype,
						writable,
						defobj.cref(),
						size
					)
					if result != SNMPERR_SUCCESS:
						raise netsnmpAgentException(
							"netsnmp_table_set_add_default_row() failed with "
							"error code {0}!".format(result)
						)

				# Register handler and table_data_set with net-snmp.
				self._handler_reginfo = agent._prepareRegistration(
					oidstr,
					extendable
				)
				result = libnsa.netsnmp_register_table_data_set(
					self._handler_reginfo,
					self._dataset,
					None
				)
				if result != SNMP_ERR_NOERROR:
					raise netsnmpAgentException(
						"Error code {0} while registering table with "
						"net-snmp!".format(result)
					)

				# Finally, we keep track of all registered SNMP objects for the
				# getRegistered() method.
				agent._objs[oidstr] = self

			def addRow(self, idxobjs):
				dataset = self._dataset

				# Define a Python class to provide access to the table row.
				class TableRow(object):
					def __init__(self, idxobjs):
						# Create the netsnmp_table_set_storage structure for
						# this row.
						self._table_row = libnsa.netsnmp_table_data_set_create_row_from_defaults(
							dataset.contents.default_row
						)

						# Add the indexes
						for idxobj in idxobjs:
							result = libnsa.snmp_varlist_add_variable(
								ctypes.pointer(self._table_row.contents.indexes),
								None,
								0,
								idxobj._asntype,
								idxobj.cref(),
								idxobj._data_size
							)
							if result == None:
								raise netsnmpAgentException("snmp_varlist_add_variable() failed!")

					def setRowCell(self, column, snmpobj):
						# netsnmp_set_row_column() ignores the ASN type, so it doesn't
						# do special handling for the trailing zero byte in C strings
						size = snmpobj._data_size + 1 if snmpobj._asntype == ASN_OCTET_STR \
													  else snmpobj._data_size
						result = libnsa.netsnmp_set_row_column(
							self._table_row,
							column,
							snmpobj._asntype,
							snmpobj.cref(),
							size
						)
						if result != SNMPERR_SUCCESS:
							raise netsnmpAgentException("netsnmp_set_row_column() failed with error code {0}!".format(result))

				row = TableRow(idxobjs)

				libnsa.netsnmp_table_dataset_add_row(
					dataset,        # *table
					row._table_row  # row
				)

				return row

			def value(self):
				# Because tables are more complex than scalar variables, we
				# return a dictionary representing the table's structure and
				# contents instead of a simple string.
				retdict = {}

				# The first entry will contain the defined columns, their types
				# and their defaults, if set. We use array index 0 since it's
				# impossible for SNMP tables to have a row with that index.
				retdict[0] = {}
				col = self._dataset.contents.default_row
				while bool(col):
					retdict[0][int(col.contents.column)] = {}

					asntypes = {
						ASN_INTEGER:    "Integer",
						ASN_OCTET_STR:  "OctetString",
						ASN_IPADDRESS:  "IPAddress",
						ASN_COUNTER:    "Counter32",
						ASN_COUNTER64:  "Counter64",
						ASN_UNSIGNED:   "Unsigned32",
						ASN_TIMETICKS:  "TimeTicks"
					}
					retdict[0][int(col.contents.column)]["type"] = asntypes[col.contents.type]
					if bool(col.contents.data):
						if col.contents.type == ASN_OCTET_STR:
							retdict[0][int(col.contents.column)]["value"] = col.contents.data.string
						else:
							retdict[0][int(col.contents.column)]["value"] = repr(col.contents.data.integer.contents.value)
					col = col.contents.next

				# Next we iterate over the table's rows, creating a dictionary
				# entry for each row after that row's index.
				row = self._dataset.contents.table.contents.first_row
				while bool(row):
					# We want to return the row index in the same way it is
					# shown when using "snmptable", eg. "aa" instead of 2.97.97.
					# This conversion is actually quite complicated (see
					# net-snmp's sprint_realloc_objid() in snmplib/mib.c and
					# get*_table_entries() in apps/snmptable.c for details).
					# All code below assumes eg. that the OID output format was
					# not changed.
					
					# snprint_objid() below requires a _full_ OID whereas the
					# table row contains only the current row's identifer.
					# Unfortunately, net-snmp does not have a ready function to
					# get the full OID. The following code was modelled after
					# similar code in netsnmp_table_data_build_result().
					fulloid = ctypes.cast(
						ctypes.create_string_buffer(
							MAX_OID_LEN * ctypes.sizeof(c_oid)
						),
						c_oid_p
					)

					# Registered OID
					rootoidlen = self._handler_reginfo.contents.rootoid_len
					for i in range(0,rootoidlen):
						fulloid[i] = self._handler_reginfo.contents.rootoid[i]

					# Entry
					fulloid[rootoidlen] = 1

					# Fake the column number. Unlike the table_data and
					# table_data_set handlers, we do not have one here. No
					# biggie, using a fixed value will do for our purposes as
					# we'll do away with anything left of the last dot below.
					fulloid[rootoidlen+1] = 2

					# Index data
					indexoidlen = row.contents.index_oid_len
					for i in range(0,indexoidlen):
						fulloid[rootoidlen+2+i] = row.contents.index_oid[i]

					# Convert the full oid to its string representation
					oidcstr = ctypes.create_string_buffer(MAX_OID_LEN)
					libnsa.snprint_objid(
						oidcstr,
						MAX_OID_LEN,
						fulloid,
						rootoidlen + 2 + indexoidlen
					)

					# And finally do away with anything left of the last dot
					indices = oidcstr.value.split(".")[-1].replace('"', '')

					# If it's a string, remove the double quotes. If it's a
					# string containing an integer, make it one
					try:
						indices = int(indices)
					except ValueError:
						indices = indices.replace('"', '')

					# Finally, iterate over all columns for this row and add
					# stored data, if present
					retdict[indices] = {}
					data = ctypes.cast(row.contents.data, ctypes.POINTER(netsnmp_table_data_set_storage))
					while bool(data):
						if bool(data.contents.data):
							if data.contents.type == ASN_OCTET_STR:
								retdict[indices][int(data.contents.column)] = data.contents.data.string
							else:
								retdict[indices][int(data.contents.column)] = repr(data.contents.data.integer.contents.value)
						else:
							retdict[indices] += {}
						data = data.contents.next

					row = row.contents.next

				return retdict

		# Return an instance of the just-defined class to the agent
		return Table(oidstr, indexes, columns, extendable)

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
