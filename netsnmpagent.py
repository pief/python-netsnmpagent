#
# python-netsnmpagent module
# Copyright (c) 2013-2019 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Lesser Public License (LGPL) version 3
#
# Main module
#

""" Allows to write net-snmp subagents in Python.

The Python bindings that ship with net-snmp support client operations
only. I fixed a couple of issues in the existing python-agentx module
but eventually decided to write a new module from scratch due to design
issues. For example, it implemented its own handler for registered SNMP
variables, which requires re-doing a lot of stuff which net-snmp
actually takes care of in its API's helpers.

This module, by contrast, concentrates on wrapping the net-snmp C API
for SNMP subagents in an easy manner. """

import sys, os, socket, struct, re, locale
from collections import defaultdict
from netsnmpapi import *

# Maximum string size supported by python-netsnmpagent
MAX_STRING_SIZE = 1024

# Helper function courtesy of Alec Thomas and taken from
# http://stackoverflow.com/questions/36932/how-can-i-represent-an-enum-in-python
def enum(*sequential, **named):
	enums = dict(zip(sequential, range(len(sequential))), **named)
	try:
		# Python 2.x
		enums_iterator = enums.iteritems()
	except AttributeError:
		# Python 3.x
		enums_iterator = enums.items()
	enums["Names"] = dict((value,key) for key, value in enums_iterator)
	return type("Enum", (), enums)

# Helper functions to deal with converting between byte strings (required by
# ctypes) and Unicode strings (possibly used by the Python version in use)
def b(s):
	""" Encodes Unicode strings to byte strings, if necessary. """

	return s if isinstance(s, bytes) else s.encode(locale.getpreferredencoding())

def u(s):
	""" Decodes byte strings to Unicode strings, if necessary. """

	return s if isinstance("Test", bytes) else s.decode(locale.getpreferredencoding())

# Indicates the status of a netsnmpAgent object
netsnmpAgentStatus = enum(
	"REGISTRATION",     # Unconnected, SNMP object registrations possible
	"FIRSTCONNECT",     # No more registrations, first connection attempt
	"CONNECTFAILED",    # Error connecting to snmpd
	"CONNECTED",        # Connected to a running snmpd instance
	"RECONNECTING",     # Got disconnected, trying to reconnect
)

# Helper function to determine if "x" is a num
def isnum(x):
	try:
		x + 1
		return True
	except TypeError:
		return False

class netsnmpAgent(object):
	""" Implements an SNMP agent using the net-snmp libraries. """

	def __init__(self, **args):
		"""Initializes a new netsnmpAgent instance.
		
		"args" is a dictionary that can contain the following
		optional parameters:
		
		- AgentName     : The agent's name used for registration with net-snmp.
		- MasterSocket  : The transport specification of the AgentX socket of
		                  the running snmpd instance to connect to (see the
		                  "LISTENING ADDRESSES" section in the snmpd(8) manpage).
		                  Change this if you want to use eg. a TCP transport or
		                  access a custom snmpd instance, eg. as shown in
		                  run_simple_agent.sh, or for automatic testing.
		- PersistenceDir: The directory to use to store persistence information.
		                  Change this if you want to use a custom snmpd
		                  instance, eg. for automatic testing.
		- MIBFiles      : A list of filenames of MIBs to be loaded. Required if
		                  the OIDs, for which variables will be registered, do
		                  not belong to standard MIBs and the custom MIBs are not
		                  located in net-snmp's default MIB path
		                  (/usr/share/snmp/mibs).
		- UseMIBFiles   : Whether to use MIB files at all or not. When False,
		                  the parser for MIB files will not be initialized, so
		                  neither system-wide MIB files nor the ones provided
		                  in the MIBFiles argument will be in use.
		- LogHandler    : An optional Python function that will be registered
		                  with net-snmp as a custom log handler. If specified,
		                  this function will be called for every log message
		                  net-snmp itself generates, with parameters as follows:
		                  1. a string indicating the message's priority: one of
		                  "Emergency", "Alert", "Critical", "Error", "Warning",
		                  "Notice", "Info" or "Debug".
		                  2. the actual log message. Note that heading strings
		                  such as "Warning: " and "Error: " will be stripped off
		                  since the priority level is explicitly known and can
		                  be used to prefix the log message, if desired.
		                  Trailing linefeeds will also have been stripped off.
		                  If undefined, log messages will be written to stderr
		                  instead. """

		# Default settings
		defaults = {
			"AgentName"     : os.path.splitext(os.path.basename(sys.argv[0]))[0],
			"MasterSocket"  : None,
			"PersistenceDir": None,
			"UseMIBFiles"   : True,
			"MIBFiles"      : None,
			"LogHandler"    : None,
		}
		for key in defaults:
			setattr(self, key, args.get(key, defaults[key]))
		if self.UseMIBFiles and self.MIBFiles is not None and type(self.MIBFiles) not in (list, tuple):
			self.MIBFiles = (self.MIBFiles,)

		# Initialize status attribute -- until start() is called we will accept
		# SNMP object registrations
		self._status = netsnmpAgentStatus.REGISTRATION

		# Unfortunately net-snmp does not give callers of init_snmp() (used
		# in the start() method) any feedback about success or failure of
		# connection establishment. But for AgentX clients this information is
		# quite essential, thus we need to implement some more or less ugly
		# workarounds.

		# For net-snmp 5.7.x, we can derive success and failure from the log
		# messages it generates. Normally these go to stderr, in the absence
		# of other so-called log handlers. Alas we define a callback function
		# that we will register with net-snmp as a custom log handler later on,
		# hereby effectively gaining access to the desired information.
		def _py_log_handler(majorID, minorID, serverarg, clientarg):
			# "majorID" and "minorID" are the callback IDs with which this
			# callback function was registered. They are useful if the same
			# callback was registered multiple times.
			# Both "serverarg" and "clientarg" are pointers that can be used to
			# convey information from the calling context to the callback
			# function: "serverarg" gets passed individually to every call of
			# snmp_call_callbacks() while "clientarg" was initially passed to
			# snmp_register_callback().

			# In this case, "majorID" and "minorID" are always the same (see the
			# registration code below). "serverarg" needs to be cast back to
			# become a pointer to a "snmp_log_message" C structure (passed by
			# net-snmp's log_handler_callback() in snmplib/snmp_logging.c) while
			# "clientarg" will be None (see the registration code below).
			logmsg = ctypes.cast(serverarg, snmp_log_message_p)

			# Generate textual description of priority level
			priorities = {
				LOG_EMERG: "Emergency",
				LOG_ALERT: "Alert",
				LOG_CRIT: "Critical",
				LOG_ERR: "Error",
				LOG_WARNING: "Warning",
				LOG_NOTICE: "Notice",
				LOG_INFO: "Info",
				LOG_DEBUG: "Debug"
			}
			msgprio = priorities[logmsg.contents.priority]

			# Strip trailing linefeeds and in addition "Warning: " and "Error: "
			# from msgtext as these conditions are already indicated through
			# msgprio
			msgtext = re.sub(
				"^(Warning|Error): *",
				"",
				u(logmsg.contents.msg.rstrip(b"\n"))
			)

			# Intercept log messages related to connection establishment and
			# failure to update the status of this netsnmpAgent object. This is
			# really an ugly hack, introducing a dependency on the particular
			# text of log messages -- hopefully the net-snmp guys won't
			# translate them one day.
			if  msgprio == "Warning" \
			or  msgprio == "Error" \
			and re.match("Failed to .* the agentx master agent.*", msgtext):
				# If this was the first connection attempt, we consider the
				# condition fatal: it is more likely that an invalid
				# "MasterSocket" was specified than that we've got concurrency
				# issues with our agent being erroneously started before snmpd.
				if self._status == netsnmpAgentStatus.FIRSTCONNECT:
					self._status = netsnmpAgentStatus.CONNECTFAILED

					# No need to log this message -- we'll generate our own when
					# throwing a netsnmpAgentException as consequence of the
					# ECONNECT
					return 0

				# Otherwise we'll stay at status RECONNECTING and log net-snmp's
				# message like any other. net-snmp code will keep retrying to
				# connect.
			elif msgprio == "Info" \
			and  re.match("AgentX subagent connected", msgtext):
				self._status = netsnmpAgentStatus.CONNECTED
			elif msgprio == "Info" \
			and  re.match("AgentX master disconnected us.*", msgtext):
				self._status = netsnmpAgentStatus.RECONNECTING

			# If "LogHandler" was defined, call it to take care of logging.
			# Otherwise print all log messages to stderr to resemble net-snmp
			# standard behavior (but add log message's associated priority in
			# plain text as well)
			if self.LogHandler:
				self.LogHandler(msgprio, msgtext)
			else:
				print("[{0}] {1}".format(msgprio, msgtext))

			return 0

		# We defined a Python function that needs a ctypes conversion so it can
		# be called by C code such as net-snmp. That's what SNMPCallback() is
		# used for. However we also need to store the reference in "self" as it
		# will otherwise be lost at the exit of this function so that net-snmp's
		# attempt to call it would end in nirvana...
		self._log_handler = SNMPCallback(_py_log_handler)

		# Now register our custom log handler with majorID SNMP_CALLBACK_LIBRARY
		# and minorID SNMP_CALLBACK_LOGGING.
		if libnsa.snmp_register_callback(
			SNMP_CALLBACK_LIBRARY,
			SNMP_CALLBACK_LOGGING,
			self._log_handler,
			None
		) != SNMPERR_SUCCESS:
			raise netsnmpAgentException(
				"snmp_register_callback() failed for _netsnmp_log_handler!"
			)

		# Finally the net-snmp logging system needs to be told to enable
		# logging through callback functions. This will actually register a
		# NETSNMP_LOGHANDLER_CALLBACK log handler that will call out to any
		# callback functions with the majorID and minorID shown above, such as
		# ours.
		libnsa.snmp_enable_calllog()

		# Unfortunately our custom log handler above is still not enough: in
		# net-snmp 5.4.x there were no "AgentX master disconnected" log
		# messages yet. So we need another workaround to be able to detect
		# disconnects for this release. Both net-snmp 5.4.x and 5.7.x support
		# a callback mechanism using the "majorID" SNMP_CALLBACK_APPLICATION and
		# the "minorID" SNMPD_CALLBACK_INDEX_STOP, which we can abuse for our
		# purposes. Again, we start by defining a callback function.
		def _py_index_stop_callback(majorID, minorID, serverarg, clientarg):
			# For "majorID" and "minorID" see our log handler above.
			# "serverarg" is a disguised pointer to a "netsnmp_session"
			# structure (passed by net-snmp's subagent_open_master_session() and
			# agentx_check_session() in agent/mibgroup/agentx/subagent.c). We
			# can ignore it here since we have a single session only anyway.
			# "clientarg" will be None again (see the registration code below).

			# We only care about SNMPD_CALLBACK_INDEX_STOP as our custom log
			# handler above already took care of all other events.
			if minorID == SNMPD_CALLBACK_INDEX_STOP:
				self._status = netsnmpAgentStatus.RECONNECTING

			return 0

		# Convert it to a C callable function and store its reference
		self._index_stop_callback = SNMPCallback(_py_index_stop_callback)

		# Register it with net-snmp
		if libnsa.snmp_register_callback(
			SNMP_CALLBACK_APPLICATION,
			SNMPD_CALLBACK_INDEX_STOP,
			self._index_stop_callback,
			None
		) != SNMPERR_SUCCESS:
			raise netsnmpAgentException(
				"snmp_register_callback() failed for _netsnmp_index_callback!"
			)

		# No enabling necessary here

		# Make us an AgentX client
		if libnsa.netsnmp_ds_set_boolean(
			NETSNMP_DS_APPLICATION_ID,
			NETSNMP_DS_AGENT_ROLE,
			1
		) != SNMPERR_SUCCESS:
			raise netsnmpAgentException(
				"netsnmp_ds_set_boolean() failed for NETSNMP_DS_AGENT_ROLE!"
			)

		# Use an alternative transport specification to connect to the master?
		# Defaults to "/var/run/agentx/master".
		# (See the "LISTENING ADDRESSES" section in the snmpd(8) manpage)
		if self.MasterSocket:
			if libnsa.netsnmp_ds_set_string(
				NETSNMP_DS_APPLICATION_ID,
				NETSNMP_DS_AGENT_X_SOCKET,
				b(self.MasterSocket)
			) != SNMPERR_SUCCESS:
				raise netsnmpAgentException(
					"netsnmp_ds_set_string() failed for NETSNMP_DS_AGENT_X_SOCKET!"
				)

		# Use an alternative persistence directory?
		if self.PersistenceDir:
			if libnsa.netsnmp_ds_set_string(
				NETSNMP_DS_LIBRARY_ID,
				NETSNMP_DS_LIB_PERSISTENT_DIR,
				b(self.PersistenceDir)
			) != SNMPERR_SUCCESS:
				raise netsnmpAgentException(
					"netsnmp_ds_set_string() failed for NETSNMP_DS_LIB_PERSISTENT_DIR!"
				)

		# Initialize net-snmp library (see netsnmp_agent_api(3))
		if libnsa.init_agent(b(self.AgentName)) != 0:
			raise netsnmpAgentException("init_agent() failed!")

		# Initialize MIB parser
		if self.UseMIBFiles:
			libnsa.netsnmp_init_mib()

		# If MIBFiles were specified (ie. MIBs that can not be found in
		# net-snmp's default MIB directory /usr/share/snmp/mibs), read
		# them in so we can translate OID strings to net-snmp's internal OID
		# format.
		if self.UseMIBFiles and self.MIBFiles:
			for mib in self.MIBFiles:
				if libnsa.read_mib(b(mib)) == 0:
					raise netsnmpAgentException("netsnmp_read_module({0}) " +
					                            "failed!".format(mib))

		# Initialize our SNMP object registry
		self._objs = defaultdict(dict)

	def _prepareRegistration(self, oidstr, writable = True):
		# Make sure the agent has not been start()ed yet
		if self._status != netsnmpAgentStatus.REGISTRATION:
			raise netsnmpAgentException("Attempt to register SNMP object " \
			                            "after agent has been started!")

		if self.UseMIBFiles:
			# We can't know the length of the internal OID representation
			# beforehand, so we use a MAX_OID_LEN sized buffer for the call to
			# read_objid() below
			oid = (c_oid * MAX_OID_LEN)()
			oid_len = ctypes.c_size_t(MAX_OID_LEN)

			# Let libsnmpagent parse the OID
			if libnsa.read_objid(
				b(oidstr),
				ctypes.cast(ctypes.byref(oid), c_oid_p),
				ctypes.byref(oid_len)
			) == 0:
				raise netsnmpAgentException("read_objid({0}) failed!".format(oidstr))
		else:
			# Interpret the given oidstr as the oid itself.
			try:
				parts = [c_oid(long(x) if sys.version_info <= (3,) else int(x)) for x in oidstr.split('.')]
			except ValueError:
				raise netsnmpAgentException("Invalid OID (not using MIB): {0}".format(oidstr))

			oid = (c_oid * len(parts))(*parts)
			oid_len = ctypes.c_size_t(len(parts))

		# Do we allow SNMP SETting to this OID?
		handler_modes = HANDLER_CAN_RWRITE if writable \
		                                   else HANDLER_CAN_RONLY

		# Create the netsnmp_handler_registration structure. It notifies
		# net-snmp that we will be responsible for anything below the given
		# OID. We use this for leaf nodes only, processing of subtrees will be
		# left to net-snmp.
		handler_reginfo = libnsa.netsnmp_create_handler_registration(
			b(oidstr),
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
		                          WATCHER_FIXED_SIZE or WATCHER_MAX_SIZE.
		    - "max_size"        : The maximum allowed string size if "flags"
		                          has been set to WATCHER_MAX_SIZE.
		    - "initval"         : The value to initialize the C data type with,
		                          eg. 0 or "".
		    - "asntype"         : A constant defining the SNMP variable type
		                          from an ASN.1 perspective, eg. ASN_INTEGER.
		    - "context"         : A string defining the context name for the
		                          SNMP variable
		
		    The class instance returned will have no association with net-snmp
		    yet. Use the Register() method to associate it with an OID. """

		# This is the replacement function, the "decoration"
		def create_vartype_class(self, initval = None, oidstr = None, writable = True, context = ""):
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
						self._cvar      = props["ctype"](initval if isnum(initval) else b(initval))
						self._data_size = ctypes.sizeof(self._cvar)
						self._max_size  = self._data_size
					else:
						self._cvar      = props["ctype"](initval if isnum(initval) else b(initval), props["max_size"])
						self._data_size = len(self._cvar.value)
						self._max_size  = max(self._data_size, props["max_size"])

					if oidstr:
						# Prepare the netsnmp_handler_registration structure.
						handler_reginfo = agent._prepareRegistration(oidstr, writable)
						handler_reginfo.contents.contextName = b(context)

						# Create the netsnmp_watcher_info structure.
						self._watcher = libnsX.netsnmp_create_watcher_info(
							self.cref(),
							self._data_size,
							self._asntype,
							self._flags
						)

						# Explicitly set netsnmp_watcher_info structure's
						# max_size parameter. netsnmp_create_watcher_info6 would
						# have done that for us but that function was not yet
						# available in net-snmp 5.4.x.
						self._watcher.contents.max_size = self._max_size

						# Register handler and watcher with net-snmp.
						result = libnsX.netsnmp_register_watched_scalar(
							handler_reginfo,
							self._watcher
						)
						if result != 0:
							raise netsnmpAgentException("Error registering variable with net-snmp!")

						# Finally, we keep track of all registered SNMP objects for the
						# getRegistered() method.
						agent._objs[context][oidstr] = self

				def value(self):
					val = self._cvar.value

					if isnum(val):
						# Python 2.x will automatically switch from the "int"
						# type to the "long" type, if necessary. Python 3.x
						# has no limits on the "int" type anymore.
						val = int(val)
					else:
						val = u(val)

					return val

				def cref(self, **kwargs):
					return ctypes.byref(self._cvar) if self._flags == WATCHER_FIXED_SIZE \
					                                else self._cvar

				def update(self, val):
					if self._asntype == ASN_COUNTER and val >> 32:
						val = val & 0xFFFFFFFF
					if self._asntype == ASN_COUNTER64 and val >> 64:
						val = val & 0xFFFFFFFFFFFFFFFF
					self._cvar.value = val
					if props["flags"] == WATCHER_MAX_SIZE:
						if len(val) > self._max_size:
							raise netsnmpAgentException(
								"Value passed to update() truncated: {0} > {1} "
								"bytes!".format(len(val), self._max_size)
							)
						self._data_size = self._watcher.contents.data_size = len(val)

				if props["asntype"] in [ASN_COUNTER, ASN_COUNTER64]:
					def increment(self, count=1):
						self.update(self.value() + count)

			cls.__name__ = property_func.__name__

			# Return an instance of the just-defined class to the agent
			return cls()

		return create_vartype_class

	@VarTypeClass
	def Integer32(self, initval = None, oidstr = None, writable = True, context = ""):
		return {
			"ctype"         : ctypes.c_long,
			"flags"         : WATCHER_FIXED_SIZE,
			"initval"       : 0,
			"asntype"       : ASN_INTEGER
		}

	@VarTypeClass
	def Unsigned32(self, initval = None, oidstr = None, writable = True, context = ""):
		return {
			"ctype"         : ctypes.c_ulong,
			"flags"         : WATCHER_FIXED_SIZE,
			"initval"       : 0,
			"asntype"       : ASN_UNSIGNED
		}

	@VarTypeClass
	def Counter32(self, initval = None, oidstr = None, writable = True, context = ""):
		return {
			"ctype"         : ctypes.c_ulong,
			"flags"         : WATCHER_FIXED_SIZE,
			"initval"       : 0,
			"asntype"       : ASN_COUNTER
		}

	@VarTypeClass
	def Counter64(self, initval = None, oidstr = None, writable = True, context = ""):
		return {
			"ctype"         : counter64,
			"flags"         : WATCHER_FIXED_SIZE,
			"initval"       : 0,
			"asntype"       : ASN_COUNTER64
		}

	@VarTypeClass
	def TimeTicks(self, initval = None, oidstr = None, writable = True, context = ""):
		return {
			"ctype"         : ctypes.c_ulong,
			"flags"         : WATCHER_FIXED_SIZE,
			"initval"       : 0,
			"asntype"       : ASN_TIMETICKS
		}

	# Note we can't use ctypes.c_char_p here since that creates an immutable
	# type and net-snmp _can_ modify the buffer (unless writable is False).
	# Also note that while net-snmp 5.5 introduced a WATCHER_SIZE_STRLEN flag,
	# we have to stick to WATCHER_MAX_SIZE for now to support net-snmp 5.4.x
	# (used eg. in SLES 11 SP2 and Ubuntu 12.04 LTS).
	@VarTypeClass
	def OctetString(self, initval = None, oidstr = None, writable = True, context = ""):
		return {
			"ctype"         : ctypes.create_string_buffer,
			"flags"         : WATCHER_MAX_SIZE,
			"max_size"      : MAX_STRING_SIZE,
			"initval"       : "",
			"asntype"       : ASN_OCTET_STR
		}

	# Whereas an OctetString can contain UTF-8 encoded characters, a
	# DisplayString is restricted to ASCII characters only.
	@VarTypeClass
	def DisplayString(self, initval = None, oidstr = None, writable = True, context = ""):
		return {
			"ctype"         : ctypes.create_string_buffer,
			"flags"         : WATCHER_MAX_SIZE,
			"max_size"      : MAX_STRING_SIZE,
			"initval"       : "",
			"asntype"       : ASN_OCTET_STR
		}

	# IP addresses are stored as unsigned integers, but the Python interface
	# should use strings. So we need a special class.
	def IpAddress(self, initval = "0.0.0.0", oidstr = None, writable = True, context = ""):
		agent = self

		class IpAddress(object):
			def __init__(self):
				self._flags     = WATCHER_FIXED_SIZE
				self._asntype   = ASN_IPADDRESS
				self._cvar      = ctypes.c_uint(0)
				self._data_size = ctypes.sizeof(self._cvar)
				self._max_size  = self._data_size
				self.update(initval)

				if oidstr:
					# Prepare the netsnmp_handler_registration structure.
					handler_reginfo = agent._prepareRegistration(oidstr, writable)
					handler_reginfo.contents.contextName = b(context)

					# Create the netsnmp_watcher_info structure.
					watcher = libnsX.netsnmp_create_watcher_info(
						self.cref(),
						ctypes.sizeof(self._cvar),
						ASN_IPADDRESS,
						WATCHER_FIXED_SIZE
					)
					watcher._maxsize = ctypes.sizeof(self._cvar)

					# Register handler and watcher with net-snmp.
					result = libnsX.netsnmp_register_watched_scalar(
						handler_reginfo,
						watcher
					)
					if result != 0:
						raise netsnmpAgentException("Error registering variable with net-snmp!")

					# Finally, we keep track of all registered SNMP objects for the
					# getRegistered() method.
					agent._objs[context][oidstr] = self

			def value(self):
				# Get string representation of IP address.
				return socket.inet_ntoa(
					struct.pack("I", self._cvar.value)
				)

			def cref(self, **kwargs):
				# Due to an unfixed Net-SNMP issue (see
				# https://sourceforge.net/p/net-snmp/bugs/2136/) we have
				# to convert the value to host byte order if it shall be
				# used as table index.
				if kwargs.get("is_table_index", False) == False:
					return ctypes.byref(self._cvar)
				else:
					_cidx = ctypes.c_uint(0)
					_cidx.value = struct.unpack("I", struct.pack("!I", self._cvar.value))[0]
					return ctypes.byref(_cidx)

			def update(self, val):
				# Convert dotted decimal IP address string to ctypes
				# unsigned int in network byte order.
				self._cvar.value = struct.unpack(
					"I",
					socket.inet_aton(val if val else "0.0.0.0")
				)[0]

		# Return an instance of the just-defined class to the agent
		return IpAddress()

	def Table(self, oidstr, indexes, columns, counterobj = None, extendable = False, context = ""):
		agent = self

		# Define a Python class to provide access to the table.
		class Table(object):
			def __init__(self, oidstr, idxobjs, coldefs, counterobj, extendable, context):
				# Create a netsnmp_table_data_set structure, representing both
				# the table definition and the data stored inside it. We use the
				# oidstr as table name.
				self._dataset = libnsX.netsnmp_create_table_data_set(
					ctypes.c_char_p(b(oidstr))
				)

				# Define the table row's indexes
				for idxobj in idxobjs:
					libnsX.netsnmp_table_dataset_add_index(
						self._dataset,
						idxobj._asntype
					)

				# Define the table's columns and their default values
				for coldef in coldefs:
					colno    = coldef[0]
					defobj   = coldef[1]
					writable = coldef[2] if len(coldef) > 2 \
					                     else 0

					result = libnsX.netsnmp_table_set_add_default_row(
						self._dataset,
						colno,
						defobj._asntype,
						writable,
						defobj.cref(),
						defobj._data_size
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
				self._handler_reginfo.contents.contextName = b(context)
				result = libnsX.netsnmp_register_table_data_set(
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
				agent._objs[context][oidstr] = self

				# If "counterobj" was specified, use it to track the number
				# of table rows
				if counterobj:
					counterobj.update(0)
				self._counterobj = counterobj

			def addRow(self, idxobjs):
				dataset = self._dataset

				# Define a Python class to provide access to the table row.
				class TableRow(object):
					def __init__(self, idxobjs):
						# Create the netsnmp_table_set_storage structure for
						# this row.
						self._table_row = libnsX.netsnmp_table_data_set_create_row_from_defaults(
							dataset.contents.default_row
						)

						# Add the indexes
						for idxobj in idxobjs:
							result = libnsa.snmp_varlist_add_variable(
								ctypes.pointer(self._table_row.contents.indexes),
								None,
								0,
								idxobj._asntype,
								idxobj.cref(is_table_index=True),
								idxobj._data_size
							)
							if result == None:
								raise netsnmpAgentException("snmp_varlist_add_variable() failed!")

					def setRowCell(self, column, snmpobj):
						result = libnsX.netsnmp_set_row_column(
							self._table_row,
							column,
							snmpobj._asntype,
							snmpobj.cref(),
							snmpobj._data_size
						)
						if result != SNMPERR_SUCCESS:
							raise netsnmpAgentException("netsnmp_set_row_column() failed with error code {0}!".format(result))

				row = TableRow(idxobjs)

				libnsX.netsnmp_table_dataset_add_row(
					dataset,        # *table
					row._table_row  # row
				)

				if self._counterobj:
					self._counterobj.update(self._counterobj.value() + 1)

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
							retdict[0][int(col.contents.column)]["value"] = u(ctypes.string_at(col.contents.data.string, col.contents.data_len))
						elif col.contents.type == ASN_IPADDRESS:
							uint_value = ctypes.cast(
								(ctypes.c_int*1)(col.contents.data.integer.contents.value),
								ctypes.POINTER(ctypes.c_uint)
							).contents.value
							retdict[0][int(col.contents.column)]["value"] = socket.inet_ntoa(struct.pack("I", uint_value))
						else:
							retdict[0][int(col.contents.column)]["value"] = col.contents.data.integer.contents.value
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
					for i in range(0, rootoidlen):
						fulloid[i] = self._handler_reginfo.contents.rootoid[i]

					# Entry
					fulloid[rootoidlen] = 1

					# Fake the column number. Unlike the table_data and
					# table_data_set handlers, we do not have one here. No
					# biggie, using a fixed value will do for our purposes as
					# we'll do away with anything left of the first dot below.
					fulloid[rootoidlen + 1] = 2

					# Index data
					indexoidlen = row.contents.index_oid_len
					for i in range(0, indexoidlen):
						fulloid[rootoidlen + 2 + i] = row.contents.index_oid[i]

					# Convert the full OID to its string representation
					oidcstr = ctypes.create_string_buffer(MAX_OID_LEN)
					libnsa.snprint_objid(
						oidcstr,
						MAX_OID_LEN,
						fulloid,
						rootoidlen + 2 + indexoidlen
					)

					# And finally do away with anything left of the first dot
					# so we keep the row index only
					indices = oidcstr.value.split(b".", 1)[1]

					# If it's a string, remove the double quotes. If it's a
					# string containing an integer, make it one
					try:
						indices = int(indices)
					except ValueError:
						indices = u(indices.replace(b'"', b''))

					# Finally, iterate over all columns for this row and add
					# stored data, if present
					retdict[indices] = {}
					data = ctypes.cast(row.contents.data, ctypes.POINTER(netsnmp_table_data_set_storage))
					while bool(data):
						if bool(data.contents.data):
							if data.contents.type == ASN_OCTET_STR:
								retdict[indices][int(data.contents.column)] = u(ctypes.string_at(data.contents.data.string, data.contents.data_len))
							elif data.contents.type == ASN_COUNTER64:
								retdict[indices][int(data.contents.column)] = data.contents.data.counter64.contents.value
							elif data.contents.type == ASN_IPADDRESS:
								uint_value = ctypes.cast((ctypes.c_int*1)(
									data.contents.data.integer.contents.value),
									ctypes.POINTER(ctypes.c_uint)
									).contents.value
								retdict[indices][int(data.contents.column)] = socket.inet_ntoa(struct.pack("I", uint_value))
							else:
								retdict[indices][int(data.contents.column)] = data.contents.data.integer.contents.value
						else:
							retdict[indices] += {}
						data = data.contents.next

					row = row.contents.next

				return retdict

			def clear(self):
				row = self._dataset.contents.table.contents.first_row
				while bool(row):
					nextrow = row.contents.next
					libnsX.netsnmp_table_dataset_remove_and_delete_row(
						self._dataset,
						row
					)
					row = nextrow
				if self._counterobj:
					self._counterobj.update(0)

		# Return an instance of the just-defined class to the agent
		return Table(oidstr, indexes, columns, counterobj, extendable, context)

	def getContexts(self):
		""" Returns the defined contexts. """

		return self._objs.keys()

	def getRegistered(self, context = ""):
		""" Returns a dictionary with the currently registered SNMP objects.

		    Returned is a dictionary objects for the specified "context",
		    which defaults to the default context. """
		myobjs = {}
		try:
			# Python 2.x
			objs_iterator = self._objs[context].iteritems()
		except AttributeError:
			# Python 3.x
			objs_iterator = self._objs[context].items()
		for oidstr, snmpobj in objs_iterator:
			myobjs[oidstr] = {
				"type": type(snmpobj).__name__,
				"value": snmpobj.value()
			}
		return dict(myobjs)

	def start(self):
		""" Starts the agent. Among other things, this means connecting
		    to the master agent, if configured that way. """
		if  self._status != netsnmpAgentStatus.CONNECTED \
		and self._status != netsnmpAgentStatus.RECONNECTING:
			self._status = netsnmpAgentStatus.FIRSTCONNECT
			libnsa.init_snmp(b(self.AgentName))
			if self._status == netsnmpAgentStatus.CONNECTFAILED:
				msg = "Error connecting to snmpd instance at \"{0}\" -- " \
				      "incorrect \"MasterSocket\" or snmpd not running?"
				msg = msg.format(self.MasterSocket)
				raise netsnmpAgentException(msg)

	def check_and_process(self, block=True):
		""" Processes incoming SNMP requests.
		    If optional "block" argument is True (default), the function
		    will block until a SNMP packet is received. """
		return libnsa.agent_check_and_process(int(bool(block)))

	def shutdown(self):
		libnsa.snmp_shutdown(b(self.AgentName))

		# Unfortunately we can't safely call shutdown_agent() for the time
		# being. All net-snmp versions up to and including 5.7.3 are unable
		# to do proper cleanup and cause issues such as double free()s so that
		# one effectively has to rely on the OS to release resources.
		#libnsa.shutdown_agent()

class netsnmpAgentException(Exception):
	pass
