#
# python-netsnmpagent module
# Copyright (c) 2013-2019 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Lesser Public License (LGPL) version 3
#
# net-snmp C API abstraction module
#

import ctypes, ctypes.util, locale

# Helper functions to deal with converting between byte strings (required by
# ctypes) and Unicode strings (possibly used by the Python version in use)
#
# Not really net-snmp stuff but I prefer to avoid introducing yet another
# Python module for the Python 2/3 compatibility stuff.
def b(s):
	""" Encodes Unicode strings to byte strings, if necessary. """

	return s if isinstance(s, bytes) else s.encode(locale.getpreferredencoding())

def u(s):
	""" Decodes byte strings to Unicode strings, if necessary. """

	return s if isinstance("Test", bytes) else s.decode(locale.getpreferredencoding())

c_sizet_p = ctypes.POINTER(ctypes.c_size_t)


def oid2Str(oid, oidLen):
	oidStr = ""
	for idx in range(oidLen):
		oidStr += "." + str(oid[idx])
	return oidStr

# Make libnetsnmpagent available via Python's ctypes module. We do this globally
# so we can define C function prototypes

# Workaround for net-snmp 5.4.x that has a bug with unresolved dependencies
# in its libraries (http://sf.net/p/net-snmp/bugs/2107): load netsnmphelpers
# first
try:
	libnsh = ctypes.cdll.LoadLibrary(ctypes.util.find_library("netsnmphelpers"))
except:
	raise Exception("Could not load libnetsnmphelpers! Is net-snmp installed?")
try:
	libnsa = ctypes.cdll.LoadLibrary(ctypes.util.find_library("netsnmpagent"))
except:
	raise Exception("Could not load libnetsnmpagent! Is net-snmp installed?")

# net-snmp <5.6.x had various functions in libnetsnmphelpers.so that were moved
# to libnetsnmpagent.so in later versions. Use netsnmp_create_watcher_info as
# a test and define a libnsX handle to abstract from the actually used library
# version.
try:
	libnsa.netsnmp_create_watcher_info
	libnsX = libnsa
except AttributeError:
	libnsX = libnsh

# include/net-snmp/library/callback.h

# Callback major types
SNMP_CALLBACK_LIBRARY                   = 0
SNMP_CALLBACK_APPLICATION               = 1

# SNMP_CALLBACK_LIBRARY minor types
SNMP_CALLBACK_LOGGING                   = 4

SNMPCallback = ctypes.CFUNCTYPE(
	ctypes.c_int,                       # result type
	ctypes.c_int,                       # int majorID
	ctypes.c_int,                       # int minorID
	ctypes.c_void_p,                    # void *serverarg
	ctypes.c_void_p                     # void *clientarg
)

for f in [ libnsa.snmp_register_callback ]:
	f.argtypes = [
		ctypes.c_int,                   # int major
		ctypes.c_int,                   # int minor
		SNMPCallback,                   # SNMPCallback *new_callback
		ctypes.c_void_p                 # void *arg
	]
	f.restype = int

# include/net-snmp/agent/agent_callbacks.h
SNMPD_CALLBACK_INDEX_STOP               = 11

# include/net-snmp/library/snmp_logging.h
LOG_EMERG                               = 0 # system is unusable
LOG_ALERT                               = 1 # action must be taken immediately
LOG_CRIT                                = 2 # critical conditions
LOG_ERR                                 = 3 # error conditions
LOG_WARNING                             = 4 # warning conditions
LOG_NOTICE                              = 5 # normal but significant condition
LOG_INFO                                = 6 # informational
LOG_DEBUG                               = 7 # debug-level messages

class snmp_log_message(ctypes.Structure): pass
snmp_log_message_p = ctypes.POINTER(snmp_log_message)
snmp_log_message._fields_ = [
	("priority",            ctypes.c_int),
	("msg",                 ctypes.c_char_p)
]

# counter64 requires some extra work because it can't be reliably represented
# by a single C data type
class counter64(ctypes.Structure):
	@property
	def value(self):
		return self.high << 32 | self.low

	@value.setter
	def value(self, val):
		self.high = val >> 32
		self.low  = val & 0xFFFFFFFF

	def __init__(self, initval=0):
		ctypes.Structure.__init__(self, 0, 0)
		self.value = initval
counter64_p = ctypes.POINTER(counter64)
counter64._fields_ = [
	("high",                ctypes.c_ulong),
	("low",                 ctypes.c_ulong)
]

# include/net-snmp/library/snmp_api.h
SNMPERR_SUCCESS                         = 0

# include/net-snmp/library/default_store.h
NETSNMP_DS_LIBRARY_ID                   = 0
NETSNMP_DS_APPLICATION_ID               = 1
NETSNMP_DS_LIB_PERSISTENT_DIR           = 8

for f in [ libnsa.netsnmp_ds_set_boolean ]:
	f.argtypes = [
		ctypes.c_int,                   # int storeid
		ctypes.c_int,                   # int which
		ctypes.c_int                    # int value
	]
	f.restype = ctypes.c_int

for f in [ libnsa.netsnmp_ds_set_string ]:
	f.argtypes = [
		ctypes.c_int,                   # int storeid
		ctypes.c_int,                   # int which
		ctypes.c_char_p                 # const char *value
	]
	f.restype = ctypes.c_int

# include/net-snmp/agent/ds_agent.h
NETSNMP_DS_AGENT_ROLE                   = 1
NETSNMP_DS_AGENT_X_SOCKET               = 1

# include/net-snmp/library/snmp.h
SNMP_ERR_NOERROR                        = 0
SNMP_ERR_TOO_BIG                        = 1
SNMP_ERR_NOSUCHNAME                     = 2
SNMP_ERR_BADVALUE                       = 3
SNMP_ERR_READONLY                       = 4
SNMP_ERR_GENERR                         = 5
SNMP_ERR_NOACCESS                       = 6
SNMP_ERR_WRONGTYPE                      = 7
SNMP_ERR_RESOURCEUNAVAILABLE            = 13
SNMP_ERR_COMMITFAILED                   = 14
SNMP_ERR_UNDOFAILED                     = 15

for f in [ libnsa.init_snmp ]:
	f.argtypes = [
		ctypes.c_char_p                 # const char *type
	]
	f.restype = None

for f in [ libnsa.snmp_shutdown ]:
	f.argtypes = [
		ctypes.c_char_p                 # const char *type
	]
	f.restype = None

# include/net-snmp/library/oid.h
c_oid   = ctypes.c_ulong
c_oid_p = ctypes.POINTER(c_oid)

# include/net-snmp/types.h
MAX_OID_LEN                             = 128

# include/net-snmp/agent/snmp_vars.h
for f in [ libnsa.init_agent ]:
	f.argtypes = [
		ctypes.c_char_p                 # const char *app
	]
	f.restype = ctypes.c_int

for f in [ libnsa.shutdown_agent ]:
	f.argtypes = None
	f.restype = ctypes.c_int

# include/net-snmp/library/parse.h
class tree(ctypes.Structure): pass

# include/net-snmp/mib_api.h
for f in [ libnsa.netsnmp_init_mib ]:
	f.argtypes = None
	f.restype = None

for f in [ libnsa.read_mib ]:
	f.argtypes = [
		ctypes.c_char_p                 # const char *filename
	]
	f.restype = ctypes.POINTER(tree)

for f in [ libnsa.read_objid ]:
	f.argtypes = [
		ctypes.c_char_p,                # const char *input
		c_oid_p,                        # oid *output
		c_sizet_p                       # size_t *out_len
	]
	f.restype = ctypes.c_int

# include/net-snmp/agent/agent_handler.h
HANDLER_CAN_GETANDGETNEXT               = 0x01
HANDLER_CAN_SET                         = 0x02
HANDLER_CAN_RONLY                       = HANDLER_CAN_GETANDGETNEXT
HANDLER_CAN_RWRITE                      = (HANDLER_CAN_GETANDGETNEXT | \
                                           HANDLER_CAN_SET)

class netsnmp_mib_handler(ctypes.Structure): pass
netsnmp_mib_handler_p = ctypes.POINTER(netsnmp_mib_handler)
netsnmp_mib_handler._fields_ = [
	("handler_name",	ctypes.c_char_p),
	("myvoid", 			ctypes.c_void_p),
	("flags", 			ctypes.c_int),
	("access_method", 	ctypes.c_void_p),
	("data_free", 		ctypes.c_void_p),
	("next", 			netsnmp_mib_handler_p),
	("prev", 			netsnmp_mib_handler_p),
]

class netsnmp_handler_registration(ctypes.Structure): pass
netsnmp_handler_registration_p = ctypes.POINTER(netsnmp_handler_registration)
netsnmp_handler_registration._fields_ = [
	("handlerName",         ctypes.c_char_p),
	("contextName",         ctypes.c_char_p),
	("rootoid",             c_oid_p),
	("rootoid_len",         ctypes.c_size_t),
	("handler",             netsnmp_mib_handler_p),
	("modes",               ctypes.c_int),
	("priority",            ctypes.c_int),
	("range_subid",         ctypes.c_int),
	("range_ubound",        c_oid),
	("timeout",             ctypes.c_int),
	("global_cacheid",      ctypes.c_int),
	("my_reg_void",         ctypes.c_void_p)
]

class netsnmp_agent_request_info(ctypes.Structure): pass
netsnmp_agent_request_info_p = ctypes.POINTER(netsnmp_agent_request_info)
netsnmp_agent_request_info._fields_ = [
	("mode",                ctypes.c_int),
	("asp",                 ctypes.c_void_p),
	("agent_data",          ctypes.c_void_p)
]

# include/net-snmp/types.h
class netsnmp_vardata(ctypes.Union): pass
netsnmp_vardata._fields_ = [
	("integer",				ctypes.POINTER(ctypes.c_long)),
	("string",				ctypes.c_char_p),
	("objid",				c_oid_p),
	("bitstring",			ctypes.POINTER(ctypes.c_ubyte)),
	("counter64",			ctypes.POINTER(counter64)),
	("floatVal",			ctypes.POINTER(ctypes.c_float)),
	("doubleVal",			ctypes.POINTER(ctypes.c_double))
]

class netsnmp_variable_list(ctypes.Structure): pass
netsnmp_variable_list_p = ctypes.POINTER(netsnmp_variable_list)
netsnmp_variable_list_p_p = ctypes.POINTER(netsnmp_variable_list_p)
netsnmp_variable_list._fields_ = [
    ("next_variable",       netsnmp_variable_list_p),
    ("name",                c_oid_p),
    ("name_length",         ctypes.c_size_t),
    ("type",                ctypes.c_ubyte),
    ("val",                 netsnmp_vardata),
    ("val_len",             ctypes.c_size_t),
    ("name_loc",            c_oid * MAX_OID_LEN),
    ("buf",                 ctypes.c_byte * 40),
    ("data",                ctypes.c_void_p),
    ("dataFreeHook",        ctypes.c_void_p),
    ("index",               ctypes.c_int)
]

class netsnmp_request_info(ctypes.Structure): pass
netsnmp_request_info_p = ctypes.POINTER(netsnmp_request_info)
netsnmp_request_info._fields_ = [
	("requestvb",           netsnmp_variable_list_p),
	("parent_data",         ctypes.c_void_p),
	("agent_req_info",      ctypes.c_void_p),
	("range_end",           c_oid_p),
	("range_end_len",       ctypes.c_size_t),
	("delegated",           ctypes.c_int),
	("processed",           ctypes.c_int),
	("inclusive",           ctypes.c_int),
	("status",              ctypes.c_int),
	("index",               ctypes.c_int),
	("repeat",              ctypes.c_int),
	("orig_repeat",         ctypes.c_int),
	("requestvb_start",     ctypes.c_void_p),
	("next",                ctypes.c_void_p),
	("prev",                ctypes.c_void_p),
	("subtree",             ctypes.c_void_p)
]

SNMPNodeHandler = ctypes.CFUNCTYPE(
    ctypes.c_int,                       # return type
	netsnmp_mib_handler_p,              # netsnmp_mib_handler *handler
	netsnmp_handler_registration_p,     # netsnmp_handler_registration *reginfo
	netsnmp_agent_request_info_p,       # netsnmp_agent_request_info *reqinfo
	netsnmp_request_info_p,             # netsnmp_request_info *requests
)

for f in [ libnsa.netsnmp_create_handler ]:
	f.argtypes = [
		ctypes.c_char_p,                # const char *name,
		SNMPNodeHandler                 # Netsnmp_Node_Handler * handler_access_method);
	]
	f.restype = netsnmp_mib_handler_p

for f in [ libnsa.netsnmp_inject_handler ]:
	f.argtypes = [
		netsnmp_handler_registration_p, # netsnmp_handler_registration *reginfo
		netsnmp_mib_handler_p,          # netsnmp_mib_handler *handler
	]
	f.restype = ctypes.c_int

for f in [ libnsa.netsnmp_call_next_handler ]:
	f.argtypes = [
		netsnmp_mib_handler_p,          # netsnmp_mib_handler *current,
		netsnmp_handler_registration_p, # netsnmp_handler_registration *reginfo,
		netsnmp_agent_request_info_p,   # netsnmp_agent_request_info *reqinfo,
		netsnmp_request_info_p,         # netsnmp_request_info *requests);
	]
	f.restype = ctypes.c_int

for f in [ libnsa.netsnmp_create_handler_registration ]:
	f.argtypes = [
		ctypes.c_char_p,                # const char *name
		ctypes.c_void_p,                # Netsnmp_Node_Handler *handler_access_method
		c_oid_p,                        # const oid *reg_oid
		ctypes.c_size_t,                # size_t reg_oid_len
		ctypes.c_int                    # int modes
	]
	f.restype = netsnmp_handler_registration_p

for f in [ libnsa.netsnmp_request_set_error ]:
	f.argtypes = [
		netsnmp_request_info_p,         # netsnmp_request_info *request
		ctypes.c_int                    # int error number
	]
	f.restype = ctypes.c_int

# include/net-snmp/library/asn1.h
ASN_INTEGER                             = 0x02
ASN_OCTET_STR                           = 0x04
ASN_CONSTRUCTOR                         = 0x20
ASN_OPAQUE_TAG2                         = 0x30
ASN_APPLICATION                         = 0x40
ASN_CONTEXT                             = 0x80

ASN_OPAQUE_FLOAT                        = ASN_OPAQUE_TAG2 + (ASN_APPLICATION | 8)

# include/net-snmp/library/snmp_impl.h
ASN_IPADDRESS                           = ASN_APPLICATION | 0
ASN_COUNTER                             = ASN_APPLICATION | 1
ASN_UNSIGNED                            = ASN_APPLICATION | 2
ASN_GAUGE                               = ASN_APPLICATION | 2
ASN_TIMETICKS                           = ASN_APPLICATION | 3
ASN_COUNTER64                           = ASN_APPLICATION | 6

# include/net-snmp/library/snmp-tc.h
TV_TRUE                                 = 1
TV_FALSE                                = 2

# include/net-snmp/agent/watcher.h
WATCHER_FIXED_SIZE                      = 0x01
WATCHER_MAX_SIZE                        = 0x02

class netsnmp_watcher_info(ctypes.Structure): pass
netsnmp_watcher_info_p = ctypes.POINTER(netsnmp_watcher_info)
netsnmp_watcher_info._fields_ = [
	("data",                ctypes.c_void_p),
	("data_size",           ctypes.c_size_t),
	("max_size",            ctypes.c_size_t),
	("type",                ctypes.c_ubyte),
	("flags",               ctypes.c_int)
	# net-snmp 5.7.x knows data_size_p here as well but we ignore it for
	# backwards compatibility with net-snmp 5.4.x.
]

for f in [ libnsX.netsnmp_create_watcher_info ]:
	f.argtypes = [
		ctypes.c_void_p,                # void *data
		ctypes.c_size_t,                # size_t size
		ctypes.c_ubyte,                 # u_char type
		ctypes.c_int                    # int flags
	]
	f.restype = netsnmp_watcher_info_p

for f in [ libnsX.netsnmp_register_watched_instance ]:
	f.argtypes = [
		netsnmp_handler_registration_p, # netsnmp_handler_registration *reginfo
		netsnmp_watcher_info_p          # netsnmp_watcher_info *winfo
	]
	f.restype = ctypes.c_int

for f in [ libnsX.netsnmp_register_watched_scalar ]:
	f.argtypes = [
		netsnmp_handler_registration_p, # netsnmp_handler_registration *reginfo
		netsnmp_watcher_info_p          # netsnmp_watcher_info *winfo
	]
	f.restype = ctypes.c_int

# include/net-snmp/varbind_api.h
for f in [ libnsa.snmp_varlist_add_variable ]:
	f.argtypes = [
		netsnmp_variable_list_p_p,       # netsnmp_variable_list **varlist
		c_oid_p,                         # const oid *name
		ctypes.c_size_t,                 # size_t name_length
		ctypes.c_ubyte,                  # u_char type
		ctypes.c_void_p,                 # const void *value
		ctypes.c_size_t                  # size_t len
	]
	f.restype = netsnmp_variable_list_p

# include/net-snmp/agent/table_data.h
class netsnmp_table_row(ctypes.Structure): pass
netsnmp_table_row_p = ctypes.POINTER(netsnmp_table_row)
netsnmp_table_row._fields_ = [
	("indexes",             netsnmp_variable_list_p),
	("index_oid",           c_oid_p),
	("index_oid_len",       ctypes.c_size_t),
	("data",                ctypes.c_void_p),
	("next",                netsnmp_table_row_p),
	("prev",                netsnmp_table_row_p)
]

class netsnmp_table_data(ctypes.Structure): pass
netsnmp_table_data_p = ctypes.POINTER(netsnmp_table_data)
netsnmp_table_data._fields_ = [
	("indexes_template",	netsnmp_variable_list_p),
	("name",				ctypes.c_char_p),
	("flags",				ctypes.c_int),
	("store_indexes",		ctypes.c_int),
	("first_row",			netsnmp_table_row_p),
	("last_row",			netsnmp_table_row_p)
]

# include/net-snmp/agent/table_dataset.h
class netsnmp_table_data_set_storage_udata(ctypes.Union): pass
netsnmp_table_data_set_storage_udata._fields_ = [
	("voidp",				ctypes.c_void_p),
	("integer",				ctypes.POINTER(ctypes.c_long)),
	("string",				ctypes.c_char_p),
	("objid",				c_oid_p),
	("bitstring",			ctypes.POINTER(ctypes.c_ubyte)),
	("counter64",			ctypes.POINTER(counter64)),
	("floatVal",			ctypes.POINTER(ctypes.c_float)),
	("doubleVal",			ctypes.POINTER(ctypes.c_double))
]

class netsnmp_table_data_set_storage(ctypes.Structure): pass
netsnmp_table_data_set_storage_p = ctypes.POINTER(netsnmp_table_data_set_storage)
netsnmp_table_data_set_storage._fields_ = [
	("column",              ctypes.c_uint),
	("writable",            ctypes.c_byte),
	("change_ok_fn",        ctypes.c_void_p),
	("my_change_data",      ctypes.c_void_p),
	("type",                ctypes.c_ubyte),
	("data",                netsnmp_table_data_set_storage_udata),
	("data_len",            ctypes.c_ulong),
	("next",                netsnmp_table_data_set_storage_p)
]

class netsnmp_table_data_set(ctypes.Structure): pass
netsnmp_table_data_set_p = ctypes.POINTER(netsnmp_table_data_set)
netsnmp_table_data_set._fields_ = [
	("table",               netsnmp_table_data_p),
	("default_row",         netsnmp_table_data_set_storage_p),
	("allow_creation",      ctypes.c_int),
	("rowstatus_column",    ctypes.c_uint)
]

for f in [ libnsX.netsnmp_create_table_data_set ]:
	f.argtypes = [
		ctypes.c_char_p                 # const char *table_name
	]
	f.restype = netsnmp_table_data_set_p

for f in [ libnsX.netsnmp_table_dataset_add_row ]:
	f.argtypes = [
		netsnmp_table_data_set_p,       # netsnmp_table_data_set *table
		netsnmp_table_row_p,            # netsnmp_table_row *row
	]
	f.restype = None

for f in [ libnsX.netsnmp_table_data_set_create_row_from_defaults ]:
	f.argtypes = [
		netsnmp_table_data_set_storage_p # netsnmp_table_data_set_storage *defrow
	]
	f.restype = netsnmp_table_row_p

for f in [ libnsX.netsnmp_table_set_add_default_row ]:
	f.argtypes = [
		netsnmp_table_data_set_p,       # netsnmp_table_data_set *table_set
		ctypes.c_uint,                  # unsigned int column
		ctypes.c_int,                   # int type
		ctypes.c_int,                   # int writable
		ctypes.c_void_p,                # void *default_value
		ctypes.c_size_t                 # size_t default_value_len
	]
	f.restype = ctypes.c_int

for f in [ libnsX.netsnmp_register_table_data_set ]:
	f.argtypes = [
		netsnmp_handler_registration_p, # netsnmp_handler_registration *reginfo
		netsnmp_table_data_set_p,       # netsnmp_table_data_set *data_set
		ctypes.c_void_p                 # netsnmp_table_registration_info *table_info
	]
	f.restype = ctypes.c_int

for f in [ libnsX.netsnmp_set_row_column ]:
	f.argtypes = [
		netsnmp_table_row_p,            # netsnmp_table_row *row
		ctypes.c_uint,                  # unsigned int column
		ctypes.c_int,                   # int type
		ctypes.c_void_p,                # const void *value
		ctypes.c_size_t                 # size_t value_len
	]
	f.restype = ctypes.c_int

for f in [ libnsX.netsnmp_table_dataset_add_index ]:
	f.argtypes = [
		netsnmp_table_data_set_p,       # netsnmp_table_data_set *table
		ctypes.c_ubyte                  # u_char type
	]
	f.restype = None

for f in [ libnsX.netsnmp_table_dataset_remove_and_delete_row ]:
	f.argtypes = [
		netsnmp_table_data_set_p,       # netsnmp_table_data_set *table
		netsnmp_table_row_p             # netsnmp_table_row *row
	]

# include/net-snmp/agent/snmp_agent.h
for f in [ libnsa.agent_check_and_process ]:
	f.argtypes = [
		ctypes.c_int                    # int block
	]
	f.restype = ctypes.c_int

# include/net-snmp/agent/agent_trap.h
# void            send_easy_trap(int trap, int specific);
for f in [ libnsa.send_easy_trap ]:
	f.argtypes = [
		ctypes.c_int,                  # int trap
		ctypes.c_int                   # int specific
	]
	f.restype = None                   # void
# void            send_v2trap(netsnmp_variable_list *vars);
for f in [ libnsa.send_v2trap ]:
	f.argtypes = [
		netsnmp_variable_list_p        # netsnmp_variable_list *vars
	]
	f.restype = None                   # void
# void            send_v3trap(netsnmp_variable_list *vars, char *context);
for f in [ libnsa.send_v3trap ]:
	f.argtypes = [
		netsnmp_variable_list_p,       # netsnmp_variable_list *vars
		ctypes.c_char_p                # char *context
	]
	f.restype = None                   # void

# pdu definition
c_ipaddr = (ctypes.c_ubyte * 4)
c_ubyte_p = ctypes.POINTER(ctypes.c_ubyte)

# include/net-snmp/types.h
class netsnmp_pdu(ctypes.Structure): pass
netsnmp_pdu_p = ctypes.POINTER(netsnmp_pdu)
netsnmp_pdu._fields_ = [
	("version",               ctypes.c_long), # snmp version
	("command",               ctypes.c_int), # Type of this PDU
	("reqid",                 ctypes.c_long), # Request id
	("msgid",                 ctypes.c_long), # Message id for V3 messages
	("transid",               ctypes.c_long), # Unique ID for incoming transactions
	("sessid",                ctypes.c_long), # Session id for AgentX messages
	("errstat",               ctypes.c_long), # Error status
	("errindex",              ctypes.c_long), # Error index
	("time",                  ctypes.c_ulong), # uptime
	("flags",                 ctypes.c_ulong), #
	("securityModel",         ctypes.c_int), #
	# noAuthNoPriv, authNoPriv, authPriv
	("securityLevel",         ctypes.c_int), #
	("msgParseModel",         ctypes.c_int), #
	# Transport-specific opaque data.  This replaces the IP-centric address
	("transport_data",        ctypes.c_void_p ), #
	("transport_data_length", ctypes.c_int ), #
	# The actual transport domain.  This SHOULD NOT BE FREE()D.
	("tDomain",               c_oid_p), #
	("tDomainLen",            ctypes.c_size_t ), #
	("variables",             netsnmp_variable_list_p ), #
	# SNMPv1 & SNMPv2c fields
	("community",             c_ubyte_p ), # community for outgoing requests.
	("community_len",         ctypes.c_size_t ), #
	# Trap information
	("enterprise",            c_oid_p), # System OID
	("enterprise_length",     ctypes.c_size_t ), #
	("trap_type",             ctypes.c_long ), # trap type
	("specific_type",         ctypes.c_long ), # specific type
	("agent address",         c_ipaddr ), # This is ONLY used for v1 TRAPs
	# SNMPv3 fields
	("contextEngineID",       c_ubyte_p ), # context snmpEngineID
	("contextEngineIDLen",    ctypes.c_size_t ), # Length of contextEngineID
	("contextName",           ctypes.c_char_p), # authoritative contextName
	("contextNameLen",        ctypes.c_size_t ), # Length of contextName
	("securityEngineID",      c_ubyte_p ), # authoritative snmpEngineID for security
	("securityEngineIDLen",   ctypes.c_size_t ), # Length of securityEngineID
	("securityName",          ctypes.c_char_p ), # on behalf of this principal
	("securityNameLen",       ctypes.c_size_t ), # Length of securityName
	# AgentX fields (also uses SNMPv1 community field)
	("priority",              ctypes.c_int ), #
	("range_subid",           ctypes.c_int ), #
	("securityStateRef",      ctypes.c_void_p), #
]

# include/net-snmp/snmp.h
SNMP_MSG_TRAP                           = ASN_CONTEXT | ASN_CONSTRUCTOR | 0x4
SNMP_MSG_TRAP2                          = ASN_CONTEXT | ASN_CONSTRUCTOR | 0x7

# include/net-snmp/pdu_api.h
#netsnmp_pdu    *snmp_pdu_create(int type);
for f in [ libnsX.snmp_pdu_create ]:
	f.argtypes = [
		ctypes.c_int
	]
	f.restype = netsnmp_pdu_p

#void            snmp_free_pdu( netsnmp_pdu *pdu);
for f in [ libnsX.snmp_free_pdu ]:
	f.argumets = [
		netsnmp_pdu_p
	]
	f.restype = None

# int snmp_add_var(netsnmp_pdu *pdu,
#                  const oid * name, size_t name_length, char type, const char *value)
for f in [ libnsX.snmp_add_var ]:
	f.arguments = [
		netsnmp_pdu_p,   # netsnmp_pdu *pdu
		c_oid_p,         # const oid *name
		ctypes.c_size_t, # size_t name_length
		ctypes.c_char,   # char type('=' to get type from OID tree)
		ctypes.c_char_p  # const char *value
		
	]
	f.restype = ctypes.c_int


MODE_GET                                = 160 # SNMP_MSG_GET
MODE_GET_NEXT                           = 161 # SNMP_MSG_GET_NEXT
MODE_SET_BEGIN                          = -1  # SNMP_MSG_INTERNAL_SET_BEGIN
MODE_SET_RESERVE1                       = 0   # SNMP_MSG_INTERNAL_SET_RESERVE1
MODE_SET_RESERVE2                       = 1   # SNMP_MSG_INTERNAL_SET_RESERVE2
MODE_SET_ACTION                         = 2   # SNMP_MSG_INTERNAL_SET_ACTION
MODE_SET_COMMIT                         = 3   # SNMP_MSG_INTERNAL_SET_COMMIT
MODE_SET_FREE                           = 4   # SNMP_MSG_INTERNAL_SET_FREE
MODE_SET_UNDO                           = 5   # SNMP_MSG_INTERNAL_SET_UNDO
