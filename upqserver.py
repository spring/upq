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

import log
from upqjob import UpqJob
import module_loader

logger = log.getLogger("upq")

#
# Protocol:
#
# "new_file <absolut path>" -> "ACK <jobid> <new_file>" / "REJ <error msg>"
# "archive_file <absolut path>" -> "ACK <jobid> <archive_file>" / "REJ <error msg>"
# "verify_local_file <fid>" -> "ACK <jobid> <filename>" / "REJ <error msg>"
# "verify_remote_file <fmfid>" -> "ACK <jobid> <filename>" / "REJ <error msg>"
# "verify_remote_file <fmid> <fmid>" -> "ACK <jobid> <filename>" / "REJ <error msg>"
# "list_queue" -> ACK <jobid> <a human readable list of running jobs>
# <unknown> -> "ERR unknown command"
#


class UpqServer(SocketServer.ThreadingMixIn, SocketServer.UnixStreamServer):
    def set_jobs_tasks_paths(self, jobs, tasks, paths):
        self.jobs, self.tasks, self.paths= jobs, tasks, paths
    
    def get_jobs_tasks_paths(self):
        return self.jobs, self.tasks, self.paths

class UpqRequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        logger.debug("new connection from '%s'", self.client_address)
        
        self.jobs, self.tasks, self.paths =  self.server.get_jobs_tasks_paths()
        
        while True:
            self.data = self.rfile.readline().strip()
            if not self.data: break
            logger.info("received: '%s'", self.data)
            
            # parse first word to find job
            try:
                job = self.data.split()[0]
                if self.jobs.has_key(job):
                    # such a job exists, load its module and start it
                    upqjob_class = module_loader.load_module(job,
                                                             self.paths['jobs_dir'])
                    upqjob = upqjob_class(job,
                                          self.jobs[job],
                                          self.data.split()[1:],
                                          self.paths)
                    uj = upqjob.check()
                    if uj['queued']:
                        self.response = "ACK %d %s"%(uj['jobid'], uj['msg'])
                    else:
                        self.response = "REJ %s"%(uj['msg'])
                    del sys.modules[job]
                else:
                    logger.debug("unknown job '%s'", job)
                    self.response = "ERR unknown command '%s'"%job
            except IndexError:
                self.response = "ERR error parsing '%s'"%self.data
            
            self.wfile.write(self.response+'\n')
            logger.info("sent: '%s'", self.response)
        
        logger.debug("end of transmission")
    










