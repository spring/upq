# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import log
from upqjob import UpqJob

class Archive_file(UpqJob):
	def check(self):
		# check if file is readable (or similar)
		# register_to_queue()
		# return ACK/REJ + optional msg in dict(['queued'], ['jobid'], ['msg'])
		self.msg("Not implemented yet")
		return False

	def run(self):
		# actual work
		pass
