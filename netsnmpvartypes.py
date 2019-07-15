#
# python-netsnmpagent module
# Copyright (c) 2013-2019 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Lesser Public License (LGPL) version 3
#
# SNMP scalar variable types
#

import ctypes, socket, struct
from netsnmpapi import *

# Maximum string size supported by python-netsnmpagent
MAX_STRING_SIZE = 1024

# Helper function to determine if "x" is a number
def isnum(x):
	try:
		x + 1
		return True
	except TypeError:
		return False

# Base class for scalar SNMP variables.
# This class is not supposed to be instantiated directly.
class _VarType(object):
	def value(self):
		val = self._cvar.value

		if isnum(val):
			if not isinstance(val, float):
				# Python 2.x will automatically switch from the "int"
				# type to the "long" type, if necessary. Python 3.x
				# has no limits on the "int" type anymore.
				val = int(val)
		else:
			val = u(val)

		return val

# Intermediate class for scalar SNMP variables of fixed size.
# This class is not supposed to be instantiated directly.
class _FixedSizeVarType(_VarType):
	def __init__(self, initval):
		# Create the ctypes class instance representing the variable
		# for handling by the net-snmp C API. self._ctype is supposed
		# to have been set by an inheriting class.
		self._cvar      = self._ctype(initval if isnum(initval) else b(initval))
		self._data_size = ctypes.sizeof(self._cvar)
		self._max_size  = self._data_size

		# Flags for the netsnmp_watcher_info structure
		self._watcher_flags = WATCHER_FIXED_SIZE

		return self

	def cref(self, **kwargs):
		return ctypes.byref(self._cvar)

	def update(self, val):
		self._cvar.value = val

class Integer32(_FixedSizeVarType):
	def __init__(self, initval = 0):
		self._asntype = ASN_INTEGER
		self._ctype   = ctypes.c_long
		super(Integer32, self).__init__(initval)

class Unsigned32(_FixedSizeVarType):
	def __init__(self, initval = 0):
		self._asntype = ASN_UNSIGNED
		self._ctype   = ctypes.c_ulong
		super(Unsigned32, self).__init__(initval)

class Counter32(_FixedSizeVarType):
	def __init__(self, initval = 0):
		self._asntype = ASN_COUNTER
		self._ctype   = ctypes.c_ulong
		super(Counter32, self).__init__(initval)

	def update(self, val):
		# Cut off values larger than 32 bits
		if val >> 32:
			val = val & 0xFFFFFFFF
		super(Counter32, self).update(val)

	def increment(self, count=1):
		self.update(self.value() + count)

class Counter64(_FixedSizeVarType):
	def __init__(self, initval = 0):
		self._asntype = ASN_COUNTER64
		self._ctype   = counter64
		super(Counter64, self).__init__(initval)

	def update(self, val):
		# Cut off values larger than 64 bits
		if val >> 64:
			val = val & 0xFFFFFFFFFFFFFFFF
		super(Counter64, self).update(val)

	def increment(self, count=1):
		self.update(self.value() + count)

class Gauge32(_FixedSizeVarType):
	def __init__(self, initval = 0):
		self._asntype = ASN_GAUGE
		self._ctype   = ctypes.c_ulong
		super(Gauge32, self).__init__(initval)

	def update(self, val):
		# Restrict values larger than 32 bits to ULONG_MAX
		if val >> 32:
			val = 0xFFFFFFFF
		super(Gauge32, self).update(val)

	def increment(self, count=1):
		self.update(self.value() + count)

class TimeTicks(_FixedSizeVarType):
	def __init__(self, initval = 0):
		self._asntype = ASN_TIMETICKS
		self._ctype   = ctypes.c_ulong
		super(TimeTicks, self).__init__(initval)

# RFC 2579 TruthValues should offer a bool interface to Python but
# are stored as Integers using the special constants TV_TRUE and TV_FALSE
class TruthValue(_FixedSizeVarType):
	def __init__(self, initval = False):
		self._asntype = ASN_INTEGER
		self._ctype   = ctypes.c_int
		super(TruthValue, self).__init__(TV_TRUE if initval else TV_FALSE)

	def value(self):
		return True if self._cvar.value == TV_TRUE else False

	def update(self, val):
		if isinstance(val, bool):
			self._cvar.value = TV_TRUE if val == True else TV_FALSE
		else:
			raise netsnmpAgentException("TruthValue must be True or False")

class Float(_FixedSizeVarType):
	def __init__(self, initval = 0.0):
		self._asntype = ASN_OPAQUE_FLOAT
		self._ctype   = ctypes.c_float
		super(Float, self).__init__(initval)

# IP v4 addresses are stored as unsigned integers but we want the Python
# interface to use strings.
class IpAddress(_FixedSizeVarType):
	def __init__(self, initval = "0.0.0.0"):
		self._asntype   = ASN_IPADDRESS
		self._ctype     = ctypes.c_uint
		super(IpAddress, self).__init__(0)
		self.update(initval)

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

# Intermediate class for scalar SNMP variables of variable size.
# This class is not supposed to be instantiated directly.
class _MaxSizeVarType(_VarType):
	def __init__(self, initval, max_size):
		# Create the ctypes class instance representing the variable
		# for handling by the net-snmp C API. self._ctype is supposed
		# to have been set by an inheriting class. Since it is assumed to
		# have no fixed size, we pass the maximum size as second
		# argument to the constructor.
		self._cvar      = self._ctype(initval if isnum(initval) else b(initval), max_size)
		self._data_size = len(self._cvar.value)
		self._max_size  = max(self._data_size, max_size)

		# Flags for the netsnmp_watcher_info structure
		self._watcher_flags = WATCHER_MAX_SIZE

		return self

	def cref(self, **kwargs):
		return self._cvar

	def update(self, val):
		self._cvar.value = val
		if len(val) > self._max_size:
			raise netsnmpAgentException(
				"Value passed to update() truncated: {0} > {1} "
				"bytes!".format(len(val), self._max_size)
			)
		self._data_size = self._watcher.contents.data_size = len(val)

class _String(_MaxSizeVarType):
	def __init__(self, initval = ""):
		self._asntype = ASN_OCTET_STR

		# Note we can't use ctypes.c_char_p here since that creates an immutable
		# type and net-snmp _can_ modify the buffer (unless writable is False).
		self._ctype   = ctypes.create_string_buffer

		# Also note that while net-snmp 5.5 introduced a WATCHER_SIZE_STRLEN flag,
		# we have to stick to WATCHER_MAX_SIZE for now to support net-snmp 5.4.x
		# (used eg. in SLES 11 SP2 and Ubuntu 12.04 LTS).
		self._flags   = WATCHER_MAX_SIZE

		super(_String, self).__init__(initval, MAX_STRING_SIZE)

# Whereas an OctetString can contain all byte values, a DisplayString is
# restricted to ASCII characters only.
class OctetString(_String):
	def __init__(self, initval = ""):
		super(OctetString, self).__init__(initval)
		self._data_size = len(b(initval))

	def value(self):
		val = self._cvar.raw
		if hasattr(self, "_watcher"):
			size = self._watcher.contents.data_size
		else:
			size = self._data_size
		return b(val[:size])

class DisplayString(_String):
	pass
