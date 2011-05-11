# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# List_queue produces a human readable list of what's in the queues.
#

import log
from upqjob import UpqJob

class List_queue(UpqJob):
    def check(self):
        lq = self.tasks['list_queue_t']("", 0, self.jobcfg, self.thread)
        lq.run()
        
        # return queue list immediately as 'msg'
        # we return True for queued, so that callers don't parse/interpret
        # this as an error... don't know if that makes sense...
        return {'queued': True, 'jobid': 0, 'msg': lq.get_result()}
    
    def run(self):
        # This job does nothing in run(), because it returns its result
        # immediately in check() to the caller.
        pass
