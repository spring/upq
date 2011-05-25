# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# Jobs are classes derived from UpqJob
#
# The classes name MUST be the same as the modules filename with
# the first letter upper case!
#

import threading

import log
import module_loader
import upqqueuemngr
import json
import upqconfig

class UpqJob(object):
    def __init__(self, jobname, jobdata):
        self.jobname = jobname
        uc = upqconfig.UpqConfig()
        self.jobcfg  = uc.jobs[jobname]
        self.jobdata = jobdata
        self.logger  = log.getLogger("upq")
        self.thread  = "Thread-new-UpqJob"
        self.paths   = uc.paths
        self.jobid   = -1
        self.msg     = ""
        self.result  = None
        self.finished= threading.Event()

    def check(self):
        """
        Check if job is feasable and possibly queue it.
        Overwrite this method in your job class.

        Returns True + sets jobid
        """
        # check if file is readable (or similar)
        # return True when jobdata is fine to call run(), when returning False sets self.msg
        self.enqueue_job()
        return True

    def run(self):
        """
        Do the actual job work, save result in self.result.
        Overwrite this method in your job class.
        """
        # Save result in self.result.
        return True

    def enqueue_job(self):
        """
        Put this job into the active queue
        """
        self.jobid=upqqueuemngr.UpqQueueMngr().enqueue_job(self)

    def enqueue_newjob(self, data):
        """
        Add a new job into queue, data is the data string, for example:
            notify mail:user@server.com,user1@server.com syslog
        """
        job=upqqueuemngr.UpqQueueMngr().new_job(data)
        if isinstance(job,UpqJob):
            job.check()

    def __setstate__(self, dict):
        # this is used to unpickle a job
        self.__dict__.update(dict)
        self.logger = log.getLogger("upq")

    def notify(self, succeed):
        """
        Notify someone responsable about job result.
        """
        job=None
        if succeed:
            if self.jobcfg.has_key('notify_success'):
                self.enqueue_newjob(self.jobcfg['notify_success']+" msg:"+self.msg)
        else:
            if self.jobcfg.has_key('notify_fail'):
                self.enqueue_newjob(self.jobcfg['notify_fail']+" msg:"+self.msg)
    def __str__(self):
        return "Job: "+self.jobname +"id:"+ str(self.jobid)+" "+json.dumps(self.jobdata) +" thread: "+self.thread

