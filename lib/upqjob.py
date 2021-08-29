# This file is part of the "upq" program used on springfiles.springrts.com to manage file
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

import json
from lib import upqconfig

class UpqJob(object):
	def __init__(self, jobname, jobdata):
		# if you add attributes to the UpqJob class that should be carried over
		# through a restart/reschedule, add it to notify_job.jobdata['job']
		# in notify(), if and only if it is (JSON)-serializable!
		self.jobname = jobname
		if jobname in upqconfig.UpqConfig().jobs:
			self.jobcfg  = upqconfig.UpqConfig().jobs[jobname] #settings from config-filea
		else:
			self.jobcfg = {}

		self.jobdata = jobdata #runtime parameters, these are stored into database and restored on re-run

	def __setstate__(self, dict):
		# this is used to unpickle a job
		self.__dict__.update(dict)

	def __str__(self):
		return "Job: "+self.jobname +" jobdata:"+json.dumps(self.jobdata)

