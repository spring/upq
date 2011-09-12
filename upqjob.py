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
from upqqueuemngr import UpqQueueMngr
import json
from upqconfig import UpqConfig



class UpqJob(object):
    def __init__(self, jobname, jobdata):
        self.jobname = jobname
        self.jobcfg  = UpqConfig().jobs[jobname] #settings from config-fule
        self.jobdata = jobdata #runtime parameters, these are stored into database and restored on re-run
        self.logger  = log.getLogger("upq")
        self.thread  = "T-none-0"
        self.jobid   = -1
        self.msgstr  = ""
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
        self.jobid=UpqQueueMngr().enqueue_job(self)

    def enqueue_newjob(self, jobname, params):
        """
        Add a new job into queue, data a dict, for example:
            { "mail": "user@server.com",user1@server.com", "syslog" }
        """
        job=UpqQueueMngr().new_job(jobname, params)
        UpqQueueMngr().enqueue_job(job)

    def __setstate__(self, dict):
        # this is used to unpickle a job
        self.__dict__.update(dict)
        self.logger = log.getLogger("upq")

    def msg(self, msg):
        self.logger.debug(msg)
        self.msgstr+=str(msg)

    def notify(self, succeed):
        """
        Notify someone responsible about job result.
        """
        params = {}
        if succeed:
            if self.jobcfg['notify_success']:
                params = UpqQueueMngr().getParams(self.jobcfg['notify_success'])
                params['msg'] = self.msgstr
                params['success'] = True
        else:
            if self.jobcfg['notify_fail']:
                params = UpqQueueMngr().getParams(self.jobcfg['notify_fail'])
                params['msg'] = self.msgstr
                params['success'] = False
        if params:
            job=UpqQueueMngr().new_job("notify", params)
            if isinstance(job, UpqJob):
                UpqQueueMngr().enqueue_job(job)

    def __str__(self):
        return "Job: "+self.jobname +" id:"+ str(self.jobid)+" jobdata:"+json.dumps(self.jobdata) +" thread: "+self.thread

    def getcfg(self, name, default):
        """
            returns a config value or default, if config isn't set
        """
        if self.jobcfg.has_key(name):
            return self.jobcfg[name]
        else:
            return default
