# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# UpqQueueMngr: queue manager (singleton) for all queues
#

from threading import Thread

import log
import dbqueue
import upqconfig
import module_loader
import traceback
from threading import RLock

class UpqQueueMngr():
    # Borg design pattern (pythons cooler singleton)
    __shared_state = {}

    # this dict holds a queue for each "job type" (job.__module__)
    queues = {}
    qlock = RLock()

    thread_id = 100

    def __init__(self):
        self.__dict__ = self.__shared_state
        self.logger = log.getLogger("upq")

    """ returns id of job """
    def enqueue_job(self, job):
        # add job to its queue
        self.qlock.acquire()
        if self.queues.has_key(job.__module__):
            jobid=self.insert_into_queue(job)
        else:
            jobid=self.new_queue(job)
        self.qlock.release()
        self.logger.info("(%s:%d) added to queue", job.jobname, jobid)
        return jobid

    def worker(self, queue, thread_id):
        while True:
            job = queue.get()
            job.thread = thread_id
            self.logger.info("(%s:%d,%s) starting: %s", job.jobname,job.jobid, thread_id, job.jobdata)
            res=""
            try:
                res=job.run()
                job.notify(res)
            except Exception, e:
                job.msg="Error in job %s %s %s" % (job.__module__, str(e), traceback.format_exc(100))

            self.logger.info("(%s:%d,%s) finished: %s, %s", job.jobname, job.jobid, thread_id, str(res),job.msg)
            queue.task_done(job)
            job.finished.set()

    """ returns id of job """
    def new_queue(self, job):
        queue = dbqueue.DBQueue()
        self.qlock.acquire()
        self.queues[job.__module__] = queue
        self.qlock.release()
        self.logger.info("(%s) created new queue with %d threads", job.__module__,job.jobcfg['concurrent'])
        res=self.insert_into_queue(job)
        for i in range(job.jobcfg['concurrent']):
            self.thread_id += 1
            tname = "Thread-%d" % self.thread_id
            t = Thread(target=self.worker, name=tname, args=(queue, tname))
            t.setDaemon(True)
            t.start()
            self.logger.debug("(%s,%s) started %s'", job.__module__, t.name, t.ident)
        return res

    """ returns id of job """
    def insert_into_queue(self, job):
        self.qlock.acquire()
        ret = self.queues[job.__module__].put(job)
        self.qlock.release()
        return ret
    """
         extract params into dict from a string like this:
         key1=value1 key2=value2
    """
    def getParams(self, stri):
        keyvals = stri.split()
        res = {}
        for k in keyvals:
            tmp = k.split(":", 1)
            if len(tmp)>1:
                res[tmp[0]] = tmp[1]
            else:
                res[tmp[0]] = ""
        return res

    def new_job_by_string(self, jobcmd):
        """
            creates a new job and initializes by command string
            better use new_job if possible as it doesn't need to parse the string
            for example jobcmd="notify mail:user@server1,user@server2 syslog"
        """
        params=jobcmd.split(" ",1)
        jobname=params[0]
        if len(params)>1:
            data=self.getParams(params[1])
        else:
            data={}
        return self.new_job(jobname, data)

    def new_job(self, jobname, params):
        """
            creates a new job and initializes by command array
            for example
                jobname=notify
                params={ "syslog": "", "mail": "user@server1,user@server2" }
        """
        # parse first word to find job
        uc = upqconfig.UpqConfig()
        jobs = uc.jobs
        try:
            if jobs.has_key(jobname):
                upqjob_class = module_loader.load_module(jobname)
                upqjob = upqjob_class(jobname, params)
                self.logger.debug(upqjob)
                return upqjob
            else:
                self.logger.error("(%s) job not found: %s"%(jobname, params))
        except Exception, e:
            self.logger.error("(%s) couldn't load module: %s" % (jobname, traceback.format_exc(100)))
        return None

