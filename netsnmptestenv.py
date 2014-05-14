#!/usr/bin/env python
# encoding: utf-8
#
# python-netsnmpagent module
# Copyright (c) 2013 Pieter Hollants <pieter@hollants.com>
# Licensed under the GNU Public License (GPL) version 3
#
# net-snmp test environment module
#

""" Sets up net-snmp test environments.

This module allows to run net-snmp instances with user privileges that do not
interfere with any system-wide running net-snmp instance. """

import sys, os, tempfile, subprocess, inspect, signal, time, shutil

class netsnmpTestEnv(object):
	""" Implements a net-snmp test environment. """

	def __init__(self, **args):
		""" Initializes a new net-snmp test environment. """

		self.agentport  = 6555
		self.informport = 6556
		self.smuxport   = 6557

		# Create a temporary directory to hold the snmpd files
		self.tmpdir = tempfile.mkdtemp(os.path.basename(sys.argv[0]))

		# Compose paths to files inside the temp dir
		conffile          = os.path.join(self.tmpdir, "snmpd.conf")
		self.mastersocket = os.path.join(self.tmpdir, "snmpd-agentx.sock")
		self.statedir     = os.path.join(self.tmpdir, "state")
		self.pidfile      = os.path.join(self.tmpdir, "snmpd.pid")
		indexesfile       = os.path.join(self.tmpdir, "mib_indexes")

		# Create a minimal snmpd configuration file
		with open(conffile, "w") as f:
			f.write("[snmpd]\n")
			f.write("rocommunity public 127.0.0.1\n")
			f.write("rwcommunity simple 127.0.0.1\n")
			f.write("agentaddress localhost:{0}\n".format(self.agentport))
			f.write("informsink localhost:{0}\n".format(self.informport))
			f.write("smuxsocket localhost:{0}\n".format(self.smuxport))
			f.write("master agentx\n")
			f.write("agentXSocket {0}\n\n".format(self.mastersocket))
			f.write("[snmp]\n")
			f.write("persistentDir {0}\n".format(self.statedir))

		# Create an empty mib_indexes file
		open(indexesfile, "w").close()

		# Start the snmpd instance
		cmd = "/usr/sbin/snmpd -r -LE warning -C -c{0} -p{1}".format(
			conffile, self.pidfile
		)
		subprocess.check_call(cmd, shell=True)

	def __del__(self):
		# Check for existance of snmpd's PID file
		if os.access(self.pidfile, os.R_OK):
			# Read the PID
			with open(self.pidfile, "r") as f:
				pid = int(f.read())

			# First we ask it nicely to quit. If after a second it hasn't, we
			# will kill it the hard way.
			try:
				starttime = time.clock()
				os.kill(pid, signal.SIGTERM)
				while time.clock() == starttime:
					os.kill(pid, 0)
				os.kill(pid, signal.SIGKILL)
				starttime = time.clock()
				while True:
					os.kill(pid, 0)
			except OSError as e:
				pass

		# Recursively remove the temporary directory
		if os.access(self.tmpdir, os.R_OK):
			shutil.rmtree(self.tmpdir)

	@staticmethod
	def snmpcmd(op, oid):
		""" Executes a SNMP client operation in the net-snmp test environment.
		    
		    "op" is either "get", "walk" or "table".
		    "oid" is the OID to run the operation against. """

		# Compose the SNMP client command
		cmd = "/usr/bin/snmp{0} -M+. -r0 -v 2c -c public localhost:6555 {1}"
		cmd = cmd.format(op, oid)

		# Python 2.6 (used eg. in SLES11SP2) does not yet know about
		# subprocess.check_output(), so we wrap subprocess.Popen() instead.
		#
		# Execute the command with stderr redirected to stdout and stdout
		# redirected to a pipe that we capture below
		proc = subprocess.Popen(
			cmd, shell=True, env={ "LANG": "C" },
			stdout=subprocess.PIPE, stderr=subprocess.STDOUT
		)
		output = proc.communicate()[0]
		rc = proc.poll()
		if rc == 0:
			return output.strip()

		# SLES11 SP2's Python 2.6 has a subprocess module whose
		# CalledProcessError exception does not yet know the third "output"
		# argument, so we monkey-patch support into it
		if len(inspect.getargspec(subprocess.CalledProcessError.__init__).args) == 3:
			def new_init(self, returncode, cmd, output=None):
				self.returncode = returncode
				self.cmd        = cmd
				self.output     = output
			subprocess.CalledProcessError.__init__ = new_init

		raise subprocess.CalledProcessError(rc, cmd, output)

	@classmethod
	def snmpget(self, oid):
		""" Executes a "snmpget" operation in the net-snmp test environment.

		    "oid" is the OID to run the operation against. """

		return self.snmpcmd("get", oid)

	@classmethod
	def snmpwalk(self, oid):
		""" Executes a "snmpwalk" operation in the net-snmp test environment.

		    "oid" is the OID to run the operation against. """

		return self.snmpcmd("walk", oid)

	@classmethod
	def snmptable(self, oid):
		""" Executes a "snmpwalk" operation in the net-snmp test environment.

		    "oid" is the OID to run the operation against. """

		return self.snmpcmd("table", oid)
