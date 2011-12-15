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
from upqqueuemngr import UpqQueueMngr
import json
from upqconfig import UpqConfig



class UpqJob(object):
    def __init__(self, jobname, jobdata):
        # if you add attributes to the UpqJob class that should be carried over
        # through a restart/reschedule, add it to notify_job.jobdata['job']
        # in notify(), if and only if it is (JSON)-serializable!
        self.jobname = jobname
        self.jobcfg  = UpqConfig().jobs[jobname] #settings from config-file
        if jobdata.has_key('subjobs'): # use runtime subjobs if set
            jobdata['subjobs'] = jobdata['subjobs']
        elif self.jobcfg.has_key('subjobs'): # next subjobs from config
            jobdata['subjobs'] = self.jobcfg['subjobs']
        else:
            jobdata['subjobs'] = [] # no subjobs defined, initialize empty
        self.jobdata = jobdata #runtime parameters, these are stored into database and restored on re-run
        self.logger  = log.getLogger("upq")
        self.thread  = "T-none-0"
        self.jobid   = -1
        self.msgstr  = ""
        self.result  = False
        self.finished= threading.Event()
        self.retries = 0

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
        Returning boolean indicates success or failure for notification system.

        Overwrite this method in your job class.
        """
        # Save result in self.result.
        return True

    def enqueue_job(self):
        """
        Put this job into the active queue
        """
        UpqQueueMngr().enqueue_job(self)

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
        if len(self.msgstr)+len(msg)<=500:
			self.msgstr+=str(msg)
        else:
			self.logger.error("msg to long: --------%s-------" %(msg))

    def start_subjobs(self,job):
        """
            checks if a job has a subjob and runs it
        """
        if self.jobdata.has_key('subjobs') and len(job.jobdata['subjobs'])>0:
            jobname=job.jobdata['subjobs'].pop()
            newjob=UpqQueueMngr().new_job(jobname, job.jobdata)
            newjob.check()

    def append_job(self, job, params={}):
        """
            append job, will be added as the first job
        """
        self.jobdata['subjobs'].append(job)
        for name in params:
            self.jobdata[name]=params[name]

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
            notify_job = UpqQueueMngr().new_job("notify", params)
            if isinstance(notify_job, UpqJob):
                # data of this job carried over to Notify job
                notify_job.jobdata['job'] = {"jobname": self.jobname,
                                  "jobcfg" : self.jobcfg,
                                  "jobdata": self.jobdata,
                                  "jobid"  : self.jobid,
                                  "msgstr" : self.msgstr,
                                  "result" : self.result,
                                  "retries": self.retries}
                UpqQueueMngr().enqueue_job(notify_job)

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
