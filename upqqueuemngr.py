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

class UpqQueueMngr():
    # Borg design pattern (pythons cooler singleton)
    __shared_state = {}

    # this dict holds a queue for each "job type" (job.__module__)
    queues = {}

    thread_id = 100

    def __init__(self):
        self.__dict__ = self.__shared_state
        self.logger = log.getLogger("upq")

    """ returns id of job """
    def enqueue_job(self, job):
        # add job to its queue
        if self.queues.has_key(job.__module__):
            jobid=self.insert_into_queue(job)
        else:
            jobid=self.new_queue(job)
        self.logger.info("added job %s with jobid %s to queue", job.__module__, jobid)
        return jobid

    def worker(self, queue, thread_id):
        while True:
            job = queue.get()
            job.thread = thread_id
            self.logger.info("starting job '%d' ('%s') in thread '%s'", job.jobid, job.__module__, thread_id)
            res=""
            try:
                res=job.run()
                job.notify(res)
            except Exception, e:
                job.msg="Error in job %s %s %s" % (job.__module__, str(e), traceback.format_exc(100))

            self.logger.info("finnished job '%d' ('%s') in thread '%s' with result '%s'", job.jobid, job.__module__, thread_id, job.msg)
            queue.task_done(job)
            job.finished.set()

    """ returns id of job """
    def new_queue(self, job):
        queue = dbqueue.DBQueue()
        self.queues[job.__module__] = queue
        self.logger.info("created new queue with %d threads for '%s'", job.jobcfg['concurrent'], job.__module__)
        res=self.insert_into_queue(job)
        for i in range(job.jobcfg['concurrent']):
            self.thread_id += 1
            tname = "Thread-%d" % self.thread_id
            t = Thread(target=self.worker, name=tname, args=(queue, tname))
            t.setDaemon(True)
            t.start()
            self.logger.debug("started thread '%s' / '%s' for queue '%s'", t.name, t.ident, job.__module__,)
        return res

    """ returns id of job """
    def insert_into_queue(self, job):
        return self.queues[job.__module__].put(job)
    """
         extract params into dict from a string like this:
         key1=value1 key2=value2
    """
    def getParams(self, str):
        keyvals = str.split()
        res = {}
        for k in keyvals:
            tmp = k.split(":", 1)
            if len(tmp)>1:
                res[tmp[0]] = tmp[1]
            else:
                res[tmp[0]] = ""
        return res

    """ creates a new job and initializes by command string"""
    def new_job(self, data):
        uc = upqconfig.UpqConfig()
        jobs = uc.jobs
        jobname=""
        # parse first word to find job
        try:
            params=data.split(" ",1)
            jobname=params[0]
            if jobs.has_key(jobname):
                if len(params)>1:
                    data=self.getParams(params[1])
                else:
                    data={}
                # such a job exists, load its module and start it
                upqjob_class = module_loader.load_module(jobname)
                upqjob = upqjob_class(jobname, data)
                self.logger.debug(upqjob)
                return upqjob
        except Exception, e:
            self.logger.error("couldn't load module '%s': %s" % (jobname, traceback.format_exc(100)))
        return None

