# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from upqjob import UpqJob
from upqdb import UpqDB,UpqDBIntegrityError
from upqconfig import UpqConfig

import sys
import os
import shutil

class Movefile(UpqJob):


	def run(self):
		"""
			moves a file to a different directory
			parameters:
				status: status of the file, 0=disabled, 1=active, 2=broken
				subdir: subdir to move to (usally games|maps)
			
		"""
		fid=int(self.jobdata['fid'])
		results=UpqDB().query("SELECT * FROM file WHERE fid=%d" % fid)
		res=results.first()
		if self.jobdata.has_key('status'):
			status=self.jobdata['status']
			del self.jobdata['status'] #delete param, as its only used in this job
		else:
			status=1
		if self.jobdata.has_key('subdir'):
			subdir=self.jobdata['subdir']
			del self.jobdata['subdir'] #delete param, as its only used in this job
		else:
			subdir=""
		if status==1:
			prefix = UpqConfig().paths['files']
		elif status==3:
			prefix = UpqConfig().paths['broken']
		else:
			self.logger.error("Invalid status")
			return False
		if os.path.exists(res['filename']): #filename can be an absolute path
			filename=res['filename']
		else:
			filename = os.path.join(prefix, res['path'], res['filename']) #construct source filename from db
		if not os.path.exists(filename):
			self.logger.error("File doesn't exist: %s" % (filename));
			return False
		source=filename
		filename=os.path.basename(source)
		dstfile=os.path.join(prefix, subdir, filename)
		if source!=dstfile:
			if os.path.exists(dstfile):
				self.msg("Destination file already exists: dst: %s src: %s" %(dstfile, filepath))
				return False
			shutil.move(source, dstfile)
			UpqDB().query("UPDATE file SET path='%s', status=%d, filename='%s' WHERE fid=%d" %(subdir,status, filename, fid))
			self.logger.debug("moved file to (abs)%s %s:(rel)%s" %(source, prefix,subdir))
		elif filename!=source: #file is already in the destination dir, make filename relative
			UpqDB().query("UPDATE file SET filename='%s' WHERE fid=%d" %(filename, fid))
		try:
			os.chmod(dstfile, int("0444",8))
		except OSError:
			pass
		return True
