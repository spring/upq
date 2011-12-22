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
	def getFileName(self):
		""" returns absolute filename """
		if self.jobdata.has_key('file'):
			return self.jobdata['file']
		fid=int(self.jobdata['fid'])
		results=UpqDB().query("SELECT * FROM file WHERE fid=%d" % fid)
		res=results.first()
		if os.path.exists(res['filename']): #filename can be an absolute path
			filename=res['filename']
		else:
			filename = os.path.join(prefix, res['path'], res['filename']) #construct source filename from db
	def getDstName(self, prefix, srcfile, subdir):
		""" returns absolute destination filename """
		return os.path.join(prefix, subdir, os.path.basename(srcfile))

	def run(self):
		"""
			moves a file to a different directory
			parameters:
				file: absolute filename
			or	
				fid:
				status: status of the file, 0=disabled, 1=active, 2=broken
				subdir: subdir to move to (usally games|maps)
			
		"""
		if self.jobdata.has_key('file'):
			srcfile=self.jobdata['file']
		else:
			fid=int(self.jobdata['fid'])
			srcfile=self.getFileName()
			results=UpqDB().query("SELECT * FROM file WHERE fid=%d" % fid)
			res=results.first()
		status=1
		if self.jobdata.has_key('status'):
			status=self.jobdata['status']
			del self.jobdata['status'] #delete param, as its only used in this job
		if status==1:
			prefix = UpqConfig().paths['files']
		elif status==3:
			prefix = UpqConfig().paths['broken']
		else:
			self.logger.error("Invalid status")
			return False
		subdir=""
		if self.jobdata.has_key('subdir'):
			subdir=self.jobdata['subdir']
			del self.jobdata['subdir'] #delete param, as its only used in this job

		dstfile=self.getDstName(prefix, srcfile, subdir)

		if not os.path.exists(srcfile):
			self.logger.error("File doesn't exist: %s" % (srcfile));
			return False
		filename=os.path.basename(srcfile)
		if srcfile!=dstfile:
			if os.path.exists(dstfile):
				self.msg("Destination file already exists: dst: %s src: %s" %(dstfile, srcfile))
				return False
			try:
				shutil.move(srcfile, dstfile)
			except: #move failed, try to copy
				shutil.copy(srcfile, dstfile)
			if fid!=0 :
				UpqDB().query("UPDATE file SET path='%s', status=%d, filename='%s' WHERE fid=%d" %(subdir, status, filename, fid))
			self.logger.debug("moved file to (abs)%s %s:(rel)%s" %(srcfile, prefix,subdir))
		elif filename!=srcfile: #file is already in the destination dir, make filename relative
			UpqDB().query("UPDATE file SET path='%s', status=%d, filename='%s' WHERE fid=%d" %(subdir, status, filename, fid))
		try:
			os.chmod(dstfile, int("0444",8))
		except OSError:
			pass
		return True

