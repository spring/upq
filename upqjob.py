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


import log
import upqtask
import module_loader
import upqqueuemngr
import notify

class UpqJob(object):
    def __init__(self, jobname, jobcfg, jobdata, paths):
        self.jobname = jobname
        self.jobcfg  = jobcfg
        self.jobdata = jobdata
        self.paths   = paths
        self.logger  = log.getLogger("upq")
        self.tasks   = {}
        self.jobid   = -1
        self.thread  = "Thread-new-UpqJob"
        self.result  = {'success': False, 'msg': 'Not implemented yet.'}
        
        # load task modules
        for taskname in self.jobcfg['tasks'].split():
            self.tasks[taskname] = module_loader.load_module(taskname,
                                                        self.paths['tasks_dir'])
    
    def check(self):
        """
        Check if job is feasable and possibly queue it.
        Overwrite this method in your job class.
        
        Returns {'queued': BOOL, 'jobid': INT, 'msg': STR}
        """
        # check if file is readable (or similar)
        # jobid = self.enqueue_job()
        # return {'queued': True, 'jobid': self.jobid, 'msg': 'Not implemented yet.'}
        pass
    
    def run(self):
        """
        Do the actual job work, save result in self.result.
        Overwrite this method in your job class.
        """
        # Save result in self.result.
        pass
    
    def enqueue_job(self):
        """
        Put this job into the active queue
        """
        upqqueuemngr.UpqQueueMngr().enqueue_job(self)
    
    def __getstate__(self):
        # this is used to pickle a job
        odict = self.__dict__.copy()
        del odict['tasks']
        del odict['logger']
        return odict

    def __setstate__(self, dict):
        # this is used to unpickle a job
        self.__dict__.update(dict)
        self.tasks = {}
        for taskname in self.jobcfg['tasks'].split():
            self.tasks[taskname] = module_loader.load_module(taskname,
                                                        self.paths['tasks_dir'])
        self.logger = log.getLogger("upq")
    
   
    def notify(self):
        """
        Notify someone responsable about job result.
        """
        
        if self.result['success']:
            if self.jobcfg['notify_success']:
                notify.Notify().success(self.jobname,
                              self.jobcfg['notify_success'].split()[0],
                              self.jobcfg['notify_success'].split()[1:],
                              self.result['msg'])
        else:
            if self.jobcfg['notify_fail']:
                notify.Notify().fail(self.jobname,
                            self.jobcfg['notify_fail'].split()[0],
                            self.jobcfg['notify_fail'].split()[1:],
                            self.result['msg'])
