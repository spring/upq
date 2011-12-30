# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# New_file: handle new files on springfiles.com

from upqjob import UpqJob
from upqdb import UpqDB
from upqconfig import UpqConfig
import os
from shutil import move, copy

class New_file(UpqJob):
	"""
	filepath must be set
	"""

	def check(self):
		if 'file' in self.jobdata :
			self.jobdata['filename']=os.path.basename(self.jobdata['file'])
			result=UpqDB().query("SELECT * from file where filename LIKE '%s'" % ('%%'+self.jobdata['filename']))
			res=result.first()
			if res!=None:
				self.jobdata['fid']=res['fid']
				self.msg("File %s already exists: fid: %s"%(self.jobdata['file'], res['fid']))
			if not os.access(self.jobdata['file'], os.R_OK):
				self.msg("Can't access %s"% self.jobdata['file'])
				return False
		elif not 'fid' in self.jobdata:
			self.msg("Either file or fid has to be set!")
			return False
		self.enqueue_job()
		return True

	def run(self):
		"""
			params:
				filepath: absoulte path of file
				filename: filename
				uid: uid
			or:
				fid
		"""
		if 'fid' in self.jobdata: # file already exists in db, set filename
			result=UpqDB().query("SELECT * from file where fid=%s"% (self.jobdata['fid']))
			res=result.first()
			if res==None:
				self.msg("fid not found in db!")
				return False
			self.msg("File already known, Filename: %s Size: %d" % (res['filename'], res['size']))
		return True

