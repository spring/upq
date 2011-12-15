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

from upqdb import UpqDB
import json
from re import escape

class DBQueue(Queue, object):

    def __init__(self):
        super(DBQueue, self).__init__()
        self.threads = {}

    """ returns job """
    def get(self, block=True, timeout=None):
        job = super(DBQueue, self).get(block, timeout)
        # update job state in DB
        query="UPDATE upqueue SET status=1, start_time=NOW() WHERE jobid = %d" % (job.jobid)
        UpqDB().query(query)
        return job

    def task_done(self, job):
        # update job state in DB
        msgstr = str(escape(job.msgstr.strip("%")))
        if job.result:
            result=0
        else:
             result=1
        query="UPDATE upqueue SET status=0, end_time=NOW(), result_msg='%s' WHERE jobid = %d" % (msgstr, int(job.jobid))
        UpqDB().query(query)
        super(DBQueue, self).task_done()

    """ returns id of job and sets job.jobid to it """
    def put(self, job, block=True, timeout=None):
        if job.jobid == -1:
            # add job to DB in state "new"
            jobdata = json.dumps(job.jobdata, -1)
            ret=UpqDB().insert("upqueue", {'jobname': job.jobname, 'status': 2, 'jobdata': jobdata, 'ctime': UpqDB().now() })
            job.jobid=ret #set jobid
        super(DBQueue, self).put(job, block, timeout)
        return job.jobid

