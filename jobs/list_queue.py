# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# List_queue produces a human readable list of what's in the queues.

import log
from upqjob import UpqJob
import upqqueuemngr

class List_queue(UpqJob):
	def check(self):
		qmng = upqqueuemngr.UpqQueueMngr()

		msg = ""
		self.logger.debug("qmng='%s'", qmng)
		self.logger.debug("qmng.queues.iteritems()='%s'", qmng.queues.iteritems())
		queues = qmng.queues.iteritems()

		for queue in queues:
			msg += "Queue '%s' contains %d jobs: "%(queue[0], queue[1].qsize())
			if queue[1].empty():
				msg += "Queue is empty."
				continue
			self.logger.debug("queue[1].queue='%s'", queue[1].queue)
			self.logger.debug("type(queue[1].queue)='%s'", type(queue[1].queue))
			self.logger.debug("list(queue[1].queue)='%s'", list(queue[1].queue))
			for job in queue[1].queue:
				msg += "'%s' : '%s'"%(job.jobname, job.jobdata)
		else:
			if not msg: msg = "No queues."

		self.msg = msg
		return True

