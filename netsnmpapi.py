#!/usr/bin/env python
#
# python-netsnmpagent module
#
# Copyright (c) 2012 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Public License (GPL) version 3
#

import ctypes, ctypes.util

c_sizet_p = ctypes.POINTER(ctypes.c_size_t)

# <limits.h>
UINT_MAX = 4294967295

# Make libnetsnmpagent available via Python's ctypes module. We do this globally
# so we can define C function prototypes
try:
	libnsa = ctypes.cdll.LoadLibrary(ctypes.util.find_library("netsnmpagent"))
except:
	raise Exception("Could not load libnetsnmpagent! Is net-snmp installed?")

# include/net-snmp/library/snmp_logging.h
for f in [ libnsa.snmp_enable_stderrlog ]:
	f.argtypes = None
	f.restype  = None

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

# include/net-snmp/library/parse.h
class tree(ctypes.Structure): pass

# include/net-snmp/mib_api.h
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

class netsnmp_handler_registration(ctypes.Structure): pass
netsnmp_handler_registration_p = ctypes.POINTER(netsnmp_handler_registration)

for f in [ libnsa.netsnmp_create_handler_registration ]:
	f.argtypes = [
		ctypes.c_char_p,                # const char *name
		ctypes.c_void_p,                # Netsnmp_Node_Handler *handler_access_method
		c_oid_p,                        # const oid *reg_oid
		ctypes.c_size_t,                # size_t reg_oid_len
		ctypes.c_int                    # int modes
	]
	f.restype = netsnmp_handler_registration_p

# include/net-snmp/library/asn1.h
ASN_INTEGER                             = 0x02
ASN_OCTET_STR                           = 0x04
ASN_APPLICATION                         = 0x40

# counter64 requires some extra work because it can't be reliably represented
# by a single C data type
class counter64(ctypes.Structure):
	@property
	def value(self):
		return self.high * UINT_MAX + self.low

	@value.setter
	def value(self, val):
		self.high = val / UINT_MAX
		self.low  = val - self.high * UINT_MAX

	def __init__(self, initval=0):
		ctypes.Structure.__init__(self, 0, 0)
		self.value = initval
counter64_p = ctypes.POINTER(counter64)
counter64._fields_ = [
	("high",                ctypes.c_ulong),
	("low",                 ctypes.c_ulong)
]

# include/net-snmp/library/snmp_impl.h
ASN_IPADDRESS                           = ASN_APPLICATION | 0
ASN_COUNTER                             = ASN_APPLICATION | 1
ASN_UNSIGNED                            = ASN_APPLICATION | 2
ASN_TIMETICKS                           = ASN_APPLICATION | 3
ASN_COUNTER64                           = ASN_APPLICATION | 6

# include/net-snmp/agent/watcher.h
WATCHER_FIXED_SIZE                      = 0x01
WATCHER_SIZE_STRLEN                     = 0x08

class netsnmp_watcher_info(ctypes.Structure): pass
netsnmp_watcher_info_p = ctypes.POINTER(netsnmp_watcher_info)

for f in [ libnsa.netsnmp_create_watcher_info6 ]:
	f.argtypes = [
		ctypes.c_void_p,                # void *data
		ctypes.c_size_t,                # size_t size
		ctypes.c_ubyte,                 # u_char type
		ctypes.c_int,                   # int flags
		ctypes.c_size_t,                # size_t max_size
		c_sizet_p                       # size_t *size_p
	]
	f.restype = netsnmp_watcher_info_p

for f in [ libnsa.netsnmp_register_watched_instance ]:
	f.argtypes = [
		netsnmp_handler_registration_p, # netsnmp_handler_registration *reginfo
		netsnmp_watcher_info_p          # netsnmp_watcher_info *winfo
	]
	f.restype = ctypes.c_int

# include/net-snmp/types.h
class netsnmp_variable_list(ctypes.Structure): pass
netsnmp_variable_list_p = ctypes.POINTER(netsnmp_variable_list)
netsnmp_variable_list_p_p = ctypes.POINTER(netsnmp_variable_list_p)

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

# include/net-snmp/agent/table_dataset.h
class netsnmp_table_data_set_storage(ctypes.Structure): pass
netsnmp_table_data_set_storage_p = ctypes.POINTER(netsnmp_table_data_set_storage)

class netsnmp_table_data_set(ctypes.Structure): pass
netsnmp_table_data_set_p = ctypes.POINTER(netsnmp_table_data_set)
netsnmp_table_data_set._fields_ = [
	("table",               netsnmp_table_data_p),
	("default_row",         netsnmp_table_data_set_storage_p),
	("allow_creation",      ctypes.c_int),
	("rowstatus_column",    ctypes.c_uint)
]

for f in [ libnsa.netsnmp_create_table_data_set ]:
	f.argtypes = [
		ctypes.c_char_p                 # const char *table_name
	]
	f.restype = netsnmp_table_data_set_p

for f in [ libnsa.netsnmp_table_dataset_add_row ]:
	f.argtypes = [
		netsnmp_table_data_set_p,       # netsnmp_table_data_set *table
		netsnmp_table_row_p,            # netsnmp_table_row *row
	]
	f.restype = None

for f in [ libnsa.netsnmp_table_data_set_create_row_from_defaults ]:
	f.argtypes = [
		netsnmp_table_data_set_storage_p # netsnmp_table_data_set_storage *defrow
	]
	f.restype = netsnmp_table_row_p

for f in [ libnsa.netsnmp_table_set_add_default_row ]:
	f.argtypes = [
		netsnmp_table_data_set_p,       # netsnmp_table_data_set *table_set
		ctypes.c_uint,                  # unsigned int column
		ctypes.c_int,                   # int type
		ctypes.c_int,                   # int writable
		ctypes.c_void_p,                # void *default_value
		ctypes.c_size_t                 # size_t default_value_len
	]
	f.restype = ctypes.c_int

for f in [ libnsa.netsnmp_register_table_data_set ]:
	f.argtypes = [
		netsnmp_handler_registration_p, # netsnmp_handler_registration *reginfo
		netsnmp_table_data_set_p,       # netsnmp_table_data_set *data_set
		ctypes.c_void_p                 # netsnmp_table_registration_info *table_info
	]
	f.restype = ctypes.c_int

for f in [ libnsa.netsnmp_set_row_column ]:
	f.argtypes = [
		netsnmp_table_row_p,            # netsnmp_table_row *row
		ctypes.c_uint,                  # unsigned int column
		ctypes.c_int,                   # int type
		ctypes.c_void_p,                # const void *value
		ctypes.c_size_t                 # size_t value_len
	]
	f.restype = ctypes.c_int

for f in [ libnsa.netsnmp_table_dataset_add_index ]:
	f.argtypes = [
		netsnmp_table_data_set_p,       # netsnmp_table_data_set *table
		ctypes.c_ubyte                  # u_char type
	]
	f.restype = None

# include/net-snmp/agent/snmp_agent.h
for f in [ libnsa.agent_check_and_process ]:
	f.argtypes = [
		ctypes.c_int                    # int block
	]
	f.restype = ctypes.c_int
