#
# python-netsnmpagent example agent with threading
#
# Copyright (c) 2013-2020 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Public License (GPL) version 3
#

#
# This script makes running threading_agent.py easier for you because it takes
# care of setting everything up so that the example agent can be run
# successfully.
#

set -u
set -e

# Find path to snmpd executable
SNMPD_BIN=""
for DIR in /usr/local/sbin /usr/sbin
do
	if [ -x $DIR/snmpd ] ; then
		SNMPD_BIN=$DIR/snmpd
		break
	fi
done
if [ -z "$SNMPD_BIN" ] ; then
	echo "snmpd executable not found -- net-snmp not installed?"
	exit 1
fi

# Find path to snmptrapd executable
SNMPTRAPD_BIN=""
for DIR in /usr/local/sbin /usr/sbin
do
	if [ -x $DIR/snmptrapd ] ; then
		SNMPTRAPD_BIN=$DIR/snmptrapd
		break
	fi
done
if [ -z "$SNMPTRAPD_BIN" ] ; then
	echo "snmptrapd executable not found -- net-snmp not installed?"
	exit 1
fi

# Make sure we leave a clean system upon exit
cleanup() {
	if [ -n "$TMPDIR" -a -d "$TMPDIR" ] ; then
		# Terminate snmpd, if running
		if [ -n "$SNMPD_PIDFILE" -a -e "$SNMPD_PIDFILE" ] ; then
			PID="$(cat $SNMPD_PIDFILE)"
			if [ -n "$PID" ] ; then
				kill -TERM "$PID"
			fi
		fi
		# Terminate snmptrapd, if running
		if [ -n "$SNMPTRAPD_PIDFILE" -a -e "$SNMPTRAPD_PIDFILE" ] ; then
			PID="$(cat $SNMPTRAPD_PIDFILE)"
			if [ -n "$PID" ] ; then
				kill -TERM "$PID"
			fi
		fi

		echo "* Cleaning up..."

		# Clean up temporary directory
		rm -rf "$TMPDIR"
	fi

	# Make sure echo is back on
	stty echo
}
trap cleanup EXIT QUIT TERM KILL INT HUP

echo "* Preparing snmpd environment..."

# Create a temporary directory
TMPDIR="$(mktemp --directory --tmpdir threading_agent.XXXXXXXXXX)"
SNMPD_CONFFILE=$TMPDIR/snmpd.conf
SNMPD_PIDFILE=$TMPDIR/snmpd.pid
AGENTX_SOCK=$TMPDIR/snmpd-agentx.sock

# Create a minimal snmpd configuration for our purposes
cat <<EOF >>$SNMPD_CONFFILE
[snmpd]
rocommunity public 127.0.0.1
rwcommunity simple 127.0.0.1
agentaddress localhost:5555
informsink localhost:5556
smuxsocket localhost:5557
master agentx
agentXSocket $AGENTX_SOCK

trapcommunity public
trapsink localhost:5558
trap2sink localhost:5559
informsink localhost:5560

[snmp]
persistentDir $TMPDIR/state
EOF
touch $TMPDIR/mib_indexes

# Start a snmpd instance for testing purposes, run as the current user and
# and independent from any other running snmpd instance
$SNMPD_BIN -r -LE warning -M+./ -C -c$SNMPD_CONFFILE -p$SNMPD_PIDFILE

echo "* Preparing snmptrapd environment..."

SNMPTRAPD_CONFFILE=$TMPDIR/snmptrapd.conf
SNMPTRAPD_PIDFILE=$TMPDIR/snmptrapd.pid
SNMPTRAPD_HANDLE=$TMPDIR/snmptrapd.handle

# Create a minimal snmptrapd configuration for our purposes
cat <<EOF >>$SNMPTRAPD_CONFFILE
snmpTrapdAddr localhost:5558,localhost:5559,localhost:5560

doNotRetainNotificationLogs yes

authCommunity log,execute,net public
#authUser log,execute,net simpleUser noauth

disableAuthorization yes

traphandle default $SNMPTRAPD_HANDLE
EOF

cat <<EOF >>$SNMPTRAPD_HANDLE
#!/bin/sh

PATH=/sbin:/usr/sbin:/bin:/usr/bin

read host
read ip

logger -t \${0##*/} "host:\$host ip:\$ip"

while read oid val
do
    logger -t \${0##*/} "\$oid \$val"
done
EOF
chmod a+x "$SNMPTRAPD_HANDLE"

# Start a snmptrapd instance for testing purposes, run as the current user
# and independent from any other running snmptrapd instance
$SNMPTRAPD_BIN -LE warning -M+./ -C -c$SNMPTRAPD_CONFFILE -p$SNMPTRAPD_PIDFILE -x$AGENTX_SOCK

# Give the user guidance
echo "* Our snmpd instance is now listening on localhost, port 5555."
echo "  From a second console, use the net-snmp command line utilities like this:"
echo ""
echo "    cd `pwd`"
echo "    snmpwalk -v 2c -c public -M+. localhost:5555 THREADING-MIB::threadingMIB"
echo "    snmpget -v 2c -c public -M+. localhost:5555 THREADING-MIB::threadingString.0"
echo ""

# Workaround to have CTRL-C not generate any visual feedback (we don't do any
# input anyway)
stty -echo

# Now start the threading agent
echo "* Starting the threading agent..."
python threading_agent_trap.py -m $AGENTX_SOCK -p $TMPDIR/

# Debug mode
# Remember to comment out 'stty -echo' few lines above
#gdb python -ex "run threading_agent_trap.py -m $AGENTX_SOCK -p $TMPDIR/"
