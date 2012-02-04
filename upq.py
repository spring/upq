#!/usr/bin/env python

# "upq" program used on springfiles.com to manage file uploads, mirror
# distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# main()
#

from optparse import OptionParser
import signal
import sys, os, os.path
import threading
import traceback
import daemon
#from daemon import pidlockfile

from upqconfig import UpqConfig
import log
import upqserver
import upqdb



class Upq():
	# don't use this class before upqconfig.UpqConfig().readConfig() ran!

	def __init__(self):
		self.logger = log.getLogger("upq")

	def start_server(self):
		if os.path.exists(UpqConfig().paths['socket']):
			self.logger.debug("File '%s' exists - removing it.", UpqConfig().paths['socket'])
			os.remove(UpqConfig().paths['socket'])
		try:
			server = upqserver.UpqServer(UpqConfig().paths['socket'], upqserver.UpqRequestHandler)
		except Exception as e:
		   msg="Couldn't create socket %s %s" %(UpqConfig().paths['socket'], e)
		   self.logger.error(msg)
		   print >>sys.stderr, msg
		   sys.exit(1)
		os.chmod(UpqConfig().paths['socket'], int(str(UpqConfig().paths['socket_chmod']),8))
		self.logger.info("Server listening on '%s'.", server.server_address)

		# Start a thread with the server -- that thread will then start one
		# more thread for each request
		server_thread = threading.Thread(target=server.serve_forever)
		# Exit the server thread when the main thread terminates
		server_thread.setDaemon(True)
		server_thread.start()
		self.logger.debug("Server main thread is '%s'.", server_thread.getName())

		# everything should be fine now, so let's revive unfinnished jobs
		unfinnished_business = server.revive_jobs()
		self.logger.debug("unfinnished_business='%s'", unfinnished_business)
		self.logger.info("Starting %d unfinnished jobs found in DB.", len(unfinnished_business))
		for job in unfinnished_business:
			self.logger.info("Starting unfinnished job '%s' with jobid '%d'", job.jobname, job.jobid)
			job.enqueue_job()

		return server


class Usage(Exception):
	def __init__(self, msg):
		self.msg = msg

def main(argv=None):
	if argv is None:
		argv = sys.argv

	server = None

# SIGINT signal handler
	def program_cleanup(sig_num, frame):
		logger = log.getLogger("upq")
		logger.info("Shutting down socket server...")
		server.shutdown()
		logger.info("Disconnecting from DB...")
		upqdb.UpqDB().cleanup()
		log.getLogger("upq").info("Good bye.")
		sys.exit(0)

	usage = "usage: %prog -c CONFIGFILE [options]"
	parser = OptionParser(usage)
	parser.add_option("-c", "--config", dest="configfile", default="",
			  help="path to config file CONFIGFILE")
#TODO: use this to en/disable daemonization
#		parser.add_option("-d", "--daemonize",
#		help="detach from terminal etc")
	parser.add_option("-l", "--logfile", dest="logfile", default="",
			  help="path to logfile LOGFILE")
	(options, argv) = parser.parse_args()

	try:
		# read ini file
		UpqConfig(options.configfile, options.logfile)
		UpqConfig().readConfig()

		#FIXME: remove following line + how does this $%$!" work?
		del UpqConfig().daemon['pidfile']
	#	 if UpqConfig().daemon.has_key('pidfile'):
	#		 lockfile=UpqConfig().daemon['pidfile']
	#		 UpqConfig().daemon['pidfile']=pidlockfile.TimeoutPIDLockFile(lockfile, acquire_timeout=1)
		context = daemon.DaemonContext(**UpqConfig().daemon)
		# daemonize
		context.stdout = sys.stderr
		context.stderr = sys.stderr

		upq = Upq()
		with context:
			# initialize logging
			logger = log.init_logging(UpqConfig().logging)
			logger.info("Starting logging...")
			logger.debug(UpqConfig().config_log)
			# setup and test DB
			logger.info("Connecting to DB...")
			db = upqdb.UpqDB()
			db.connect(UpqConfig().db['url'], UpqConfig().db['debug'])
			db.version()
			# start server
			logger.info("Starting socket server...")
			server = upq.start_server()

		# ignore all signals
		for sig in dir(signal):
			if sig.startswith("SIG"):
				try:
					signal.signal(signal.__getattribute__(sig), signal.SIG_IGN)
				except:
					# some signals cannot be ignored or are unknown on diff platforms
					pass
		# except SIGINT and SIGTERM
		signal.signal(signal.SIGINT, program_cleanup)
		signal.signal(signal.SIGTERM, program_cleanup)

		log.getLogger("upq").info("Server running until receiving SIGTERM or SIGINT / Ctrl+C.")
		signal.pause()

	except Exception:
		traceback.print_exc(file=sys.stderr)
	try:
		db.cleanup()
	except:
		pass
	sys.exit(1)

if __name__ == "__main__":
	sys.exit(main())
