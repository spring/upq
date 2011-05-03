# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# DBQueue: queue with persistant state in DB
#

from Queue import *

import log
import upqdb

class DBQueue(Queue, object):
    def get(self, block=True, timeout=None):
        item = super(DBQueue, self).get(block, timeout)
        # update job state in DB
        updb = upqdb.UpqDB().getdb(item.thread)
        updb.update_state(item, "running")
        updb.set_time(item, "start_time")
        return item
    
    def task_done(self, job):
        # update job state in DB
        updb = upqdb.UpqDB().getdb(job.thread)
        updb.set_time(job, "end_time")
        updb.update_state(job, "done")
        updb.set_result(job)
        super(DBQueue, self).task_done()
    
    def put(self, item, block=True, timeout=None):
        ret = super(DBQueue, self).put(item, block, timeout)
        if item.jobid == -1:
            # add job to DB in state "new"
            upqdb.UpqDB().getdb(item.thread).persist_job(item)
        return ret
