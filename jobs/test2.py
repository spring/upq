# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# test2 to be created by test

from upqjob import UpqJob
import random
import pprint
from time import sleep

class Test2(UpqJob):
	def check(self):
		self.enqueue_job()
		return True

	def run(self):
		sleep(random.uniform(4, 6))
		pprint.pprint("%d - %s - test -" % (self.jobid, self.thread))
		sleep(random.uniform(0, 5))
		pprint.pprint("%d - %s - test --" % (self.jobid, self.thread))
		sleep(random.uniform (0, 5))
		pprint.pprint("%d - %s - test ---" % (self.jobid, self.thread))
		sleep(random.uniform (0, 5))
		pprint.pprint("%d - %s - test ----" % (self.jobid, self.thread))
		self.msg("finished '%s'" % self.jobdata)
		return self.jobdata
