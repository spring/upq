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
			result=UpqDB().query("SELECT * from file where filename LIKE '%s'" % (self.jobdata['filename']))
			res=result.first()
			if res!=None:
				self.msg("File %s already exists: fid: %s"%(self.jobdata['file'], res['fid']))
				return False
			if not os.access(self.jobdata['file'], os.R_OK):
				self.msg("Can't access %s"% self.jobdata['file'])
				return False
		elif not 'fid' in self.jobdata:
			self.msg("Either file or fid has to be set!")
			return False
		id=self.enqueue_job()
		self.msg("Enqueued job")
		return True
	def movefile(self, filepath):
		"""
			check if file is already in paths[files] directory, if not, move it there
			@return the path where the file is, for example
			paths[files]=/tmp
			filepath = /tmp/path/somefile.sd7
			returns path

			paths[files]=/tmp
			filepath = /bla/somefile.sd7
			returns ""
		"""
		destination = filepath
		if not filepath.startswith(UpqConfig().paths['files']): #file outside files dir
			destination = os.path.join(UpqConfig().paths['files'], os.path.basename(filepath))
			if filepath==destination:
				return ""
			try:
				move(filepath, destination)
			except:
				copy(filepath, destination)
			return ""
		#file already in files dir, return subdirs
		return os.path.dirname(filepath)[len(UpqConfig().paths['files']):]

	def run(self):
		"""
			params:
				filepath: absoulte path of file
				filename: filename
				uid: uid
			or:
				fid
		"""
		if 'fid' in self.jobdata: # file already exists in db
			result=UpqDB().query("SELECT * from file where fid=%s"% (self.jobdata['fid']))
			res=result.first()
			if res==None:
				self.msg("fid not found in db!")
				return False
			fid=self.jobdata['fid']
		else: # file doesn't exist in db, add it
			filename=os.path.basename(self.jobdata['file'])
			filepath=self.movefile(self.jobdata['file'])
			abspath = os.path.join(UpqConfig().paths['files'], filepath, filename)
			filesize=os.path.getsize(abspath)
			if 'uid' in self.jobdata:
				uid=self.jobdata['uid']
			else:
				uid=0
			fid=UpqDB().insert("file", {
					"uid": uid,
					"filename": filename,
					"path": filepath,
					"size": filesize,
					"status": 1,
					"timestamp": UpqDB().now()
				})
		self.enqueue_newjob("hash", { "fid": fid})
		return True

