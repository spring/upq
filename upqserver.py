# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# UpqServer, UpqRequestHandler: Server and RequestHandler
#

import threading
import SocketServer
import sys
import json
import signal

import log
from upqjob import UpqJob
import upqdb
import module_loader
from upqqueuemngr import UpqQueueMngr


logger = log.getLogger("upq")


class UpqServer(SocketServer.ThreadingMixIn, SocketServer.UnixStreamServer):
    def revive_jobs(self):
        """
            Fetches all jobs from DB that are in state "new" or "running", and
            recreates the objects from its pickled representation.

            returns  : list of alive, unqueued jobs
        """
        results=upqdb.UpqDB().query("SELECT * FROM upqueue WHERE state = 'new' OR state = 'running'")
        jobs = []
        for res in results:
            job=res['jobname']
            modclass=module_loader.load_module(job)
            obj=modclass(job, json.loads(res['jobdata']))
            obj.jobid = res['jobid']
            obj.thread = "Thread-revived-UpqJob"
            jobs.append(obj)
        logger.debug("revived jobs='%s'", jobs)
        return jobs

class UpqRequestHandler(SocketServer.StreamRequestHandler):

    def handle(self):
        logger.debug("new connection from '%s'", self.client_address)
        response=""
        err=""
        
        while True:
            self.data = self.rfile.readline().strip()
            if not self.data:
                break
            logger.debug("received: '%s'", self.data)
            uj=UpqQueueMngr().new_job_by_string(self.data)
            if isinstance(uj,UpqJob):
                if uj.check():
                    self.wfile.write("ACK " + uj.msg + "\n");
                else:
                    self.wfile.write("ERR " + uj.msg + "\n");
            else:
                msg="Unknown command: %s"% self.data
                logger.debug(msg)
                self.wfile.write("ERR "+msg+'\n')
                break
            logger.debug("sent: '%s'", uj.msg)
        logger.debug("end of transmission")
