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
from upqdb import UpqDB
import os

class New_file(UpqJob):
	"""
	filepath must be set
	"""

	def check(self):
		if 'fid' or 'filepath' in self.jobdata:
			self.enqueue_job()
			self.msg="enqueued job"
			return True
		self.msg="Either fid or filepath has to be set!"
		return False
	"""
		params:
			filepath: absoulte path of file
			filename: filename
			uid: uid
		or:
			fid
	"""
	def run(self):
		if 'fid' in self.jobdata: # file already exists in db
			result=UpqDB().query("SELECT * from files where fid=%s"% (self.jobdata['fid']))
			res=result.first()
			filepath=os.path.abspath(res['filepath'])
		else: # file doesn't exist in db, add it
			filepath=self.jobdata['filepath']
			filename=self.jobdata['filename']
			filesize=os.path.getsize(filepath)
			if 'uid' in self.jobdata:
				uid=self.jobdata['uid']
			else:
				uid=0
			fid=UpqDB().insert("files", { "uid": uid, "filename": filename, "filepath": filepath, "filemime": "application/octet-stream", "filesize":filesize, "status":1, "timestamp":UpqDB().now()})
			filepath=os.path.abspath(self.jobdata['filepath'])
		if not os.access(filepath, os.R_OK):
			self.msg="can't read %s" % (filepath)
			return False
		self.enqueue_newjob("hash", { "fid": fid})
		return True

