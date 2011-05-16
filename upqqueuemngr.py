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
            return self.insert_into_queue(job)
        else:
            return self.new_queue(job)

    def worker(self, queue, thread_id):
        while True:
            job = queue.get()
            job.thread = thread_id
            self.logger.info("starting job '%d' ('%s') in thread '%s'", job.jobid, job.__module__, thread_id)
            res=job.run()
            job.notify(res)
            self.logger.info("finnished job '%d' ('%s') in thread '%s' with result '%s'", job.jobid, job.__module__, thread_id, res)
            queue.task_done(job)

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

