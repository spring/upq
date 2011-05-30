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

import upqconfig
import log
import upqserver
import upqdb



class Upq():
    # don't use this class before upqconfig.UpqConfig().readConfig() ran!

    def __init__(self):
        self.uc = upqconfig.UpqConfig()
        self.logger = log.getLogger("upq")
    
    def signal_handler(self, signal, frame):
        self.logger.debug("SIGINT / Ctrl+C received.")
    
    def start_server(self):
        if os.path.exists(self.uc.paths['socket']):
            self.logger.debug("File '%s' exists - removing it.", self.uc.paths['socket'])
            os.remove(self.uc.paths['socket'])
        
        server = upqserver.UpqServer(self.uc.paths['socket'], upqserver.UpqRequestHandler)
        os.chmod(self.uc.paths['socket'], int(self.uc.paths['socket_chmod'],8))
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
        
        signal.signal(signal.SIGINT, self.signal_handler)
        self.logger.debug("Server waiting for SIGINT / Ctrl+C.")
        signal.pause()

        self.logger.info("Good bye.")
        upqdb.UpqDB().cleanup()
        server.shutdown()


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
    if argv is None:
        argv = sys.argv

    usage = "usage: %prog -c CONFIGFILE [options]"
    parser = OptionParser(usage)
    parser.add_option("-c", "--config", dest="configfile",
                      help="path to config file CONFIGFILE")
    parser.add_option("-l", "--logfile", dest="logfile",
                      help="path to logfile LOGFILE")
    (options, argv) = parser.parse_args()
    if not options.configfile:
        parser.print_help()
        parser.error("Please supply the path to the configuration file.")

    try:
        # read ini file
        uc = upqconfig.UpqConfig()
        uc.readConfig(options)
        # setup and test DB
        db = upqdb.UpqDB()
        db.connect(uc.db['url'])
        db.version()
        # start server
        Upq().start_server()
    except Exception:
        print >>sys.stderr, "Could not initialize system, please see log."
        traceback.print_exc(file=sys.stderr)
        db.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
