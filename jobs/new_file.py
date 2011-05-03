# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# New_file: handle new files on springfile.com
#

import log
import tasks.upqtask
from jobs.upqjob import UpqJob

class New_file(UpqJob):
    """
    filepath must be set
    """
    
    #def __init__(self, jobname, jobcfg, jobdata):
    #    super(New_file, self).__init__(jobname, jobcfg, jobdata)
    #    
    #    self.logger.debug("__name__='%s'", __name__)


    def check(self):
        # check if file is readable
        self.enqueue_job()
        # return ACK/REJ + optional msg in dict(['queued'], ['jobid'], ['msg'])
        return {'queued': True, 'jobid': self.jobid, 'msg': 'Not implemented yet.'}
    
    def run(self):
        self.fileid = None
        self.filename = None
        
        # try to guess if we have a filename or a fileid
        self.logger.debug("self.jobdata='%s'", self.jobdata)
        try:
            self.fileid = int(self.jobdata[0])
        except ValueError:
            self.filename = self.jobdata[0]
        
        for task in self.tasks:
            t = task(self.filename, self.fileid, self.jobcfg, self.thread)
            t.run()
            self.logger.debug("tasks result is: '%s'", t.get_result())
        
        self.result = {'success': False, 'msg': 'Not implemented yet.'}
