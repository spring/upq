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

import log
from upqjob import UpqJob
import module_loader
import upqdb
import upqconfig


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
            modclass=module_loader.load_module(job, self.paths['jobs_dir'])
            obj=modclass(job, self.jobs[job], json.loads(res['jobdata']), self.paths)
            obj.jobid = res['jobid']
            obj.thread = "Thread-revived-UpqJob"
            jobs.append(obj)
        logger.debug("revived jobs='%s'", jobs)
        return jobs

class UpqRequestHandler(SocketServer.StreamRequestHandler):

    """
         extract params into dict from a string like this:
         key1=value1 key2=value2
    """
    def getParams(self, str):
        keyvals = str.split()
        res = {}
        for k in keyvals:
            tmp = k.split("=", 1)
            res[tmp[0]] = tmp[1]
        return res

    def handle(self):
        logger.debug("new connection from '%s'", self.client_address)
        response=""
        err=""
        uc = upqconfig.UpqConfig()
        jobs = uc.jobs
        paths = uc.paths
        
        while True:
            self.data = self.rfile.readline().strip()
            if not self.data:
                err="ERR no data received"
                break
            logger.info("received: '%s'", self.data)
            
            # parse first word to find job
            try:
                params=self.data.split(" ",1)
                jobname=params[0]
                if jobs.has_key(jobname):
                    if len(params)>1:
                        data=self.getParams(params[1])
                    else:
                        data={}
                    logger.debug(data)
                    # such a job exists, load its module and start it
                    upqjob_class = module_loader.load_module(jobname)
                    upqjob = upqjob_class(jobname, data)
                    logger.debug(upqjob)
                    uj = upqjob.check()
                    if uj:
                        response = "ACK %d %s"%(upqjob.jobid, upqjob.msg)
                    else:
                        response = "ERR %s"%(upqjob.msg)
                else:
                    logger.debug("unknown job '%s'", jobname)
                    err = "ERR unknown command '%s'"%jobname
                    break
            except IndexError:
                err = "ERR error parsing '%s'"%self.data
                break
            
            self.wfile.write(response+'\n')
            logger.info("sent: '%s'", response)
        if len(err)>0:
            self.wfile.write(err+'\n')
        logger.debug("end of transmission")

