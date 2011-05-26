# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# New_file: handle new files on springfiles.com
# inserts file into db + forks hash job
#

from upqjob import UpqJob

class New_file(UpqJob):
	"""
	filepath must be set
	"""

	def check(self):
		if not 'fid' in self.jobdata:
			return False
		self.jobdata['fid']=int(self.jobdata['fid'])
		self.enqueue_job()
		return True

	def run(self):
		self.enqueue_newjob("hash", self.jobdata)
		return True
