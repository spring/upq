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
import cPickle

class DBQueue(Queue, object):
    def get(self, block=True, timeout=None):
        item = super(DBQueue, self).get(block, timeout)
        # update job state in DB
        query="UPDATE upqueue SET state = '%s', start_time=NOW() WHERE jobid = %d" % ("running", item.jobid)
        upqdb.UpqDB().query(query)
        return item

    def task_done(self, job):
        # update job state in DB
        query="UPDATE upqueue SET state = '%s', end_time=NOW(), result_msg='%s' WHERE jobid = %d" % ("done", item.jobid, item.result_msg)
        upqdb.UpqDB().query(query)
        super(DBQueue, self).task_done()

    def put(self, item, block=True, timeout=None):
        ret = super(DBQueue, self).put(item, block, timeout)
        if item.jobid == -1:
            # add job to DB in state "new"
            pickled = cPickle.dumps(item, -1)
            ret=upqdb.UpqDB().insert("upqueue", {'jobname': item.jobname, 'state': 'new', 'pickle_blob': pickled})
            return ret
        return ret

