#!/usr/bin/env python
#
# python-netsnmpagent module
#
# Copyright (c) 2012 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Public License (GPL) version 3
#

import ctypes, ctypes.util

c_sizet_p = ctypes.POINTER(ctypes.c_size_t)

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

# include/net-snmp/library/snmp_api.h
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

# include/net-snmp/library/snmp_impl.h
ASN_IPADDRESS                           = ASN_APPLICATION | 0
ASN_COUNTER                             = ASN_APPLICATION | 1
ASN_UNSIGNED                            = ASN_APPLICATION | 2
ASN_TIMETICKS                           = ASN_APPLICATION | 3

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

# include/net-snmp/agent/snmp_agent.h
for f in [ libnsa.agent_check_and_process ]:
	f.argtypes = [
		ctypes.c_int                    # int block
	]
	f.restype = ctypes.c_int
