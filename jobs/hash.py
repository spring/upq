# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# calculate hashes

import hashlib
import os.path

from upqjob import UpqJob
from upqdb import UpqDB
from upqdb import UpqDBIntegrityError
from upqconfig import UpqConfig

class Hash(UpqJob):
	"""
		requirements to run hash:
			file is in db + file has to exist
	"""
	def check(self):
		results = UpqDB().query("SELECT fid, filename,path FROM file WHERE fid=%d " % int(self.jobdata['fid']))
		res=results.first()
		filename = os.path.join(UpqConfig().paths['files'], res['path'], res['filename'])
		if not os.path.exists(filename):
			self.logger.error("file %d doesn't exist: %s"%(res['fid'], filename))
			return False
		self.enqueue_job()
		return True

	def run(self):
		"""
			class Hash must be initialized with fileid!
		"""
		fid = int(self.jobdata['fid'])
		results = UpqDB().query("SELECT filename, path, md5, sha1, sha256  FROM file WHERE fid=%d  " % int(fid))
		res=results.first()
		filename = os.path.join(UpqConfig().paths['files'], res['path'], res['filename'])
		if not os.path.exists(filename):
			self.msg("File %s doesn't exist" % (filename))
			return False
		hashes = self.hash(filename)
		if res['md5']!=None  and res['md5']!=hashes['md5']:
			return False
		if res['sha1']!=None and res['sha1']!=hashes['sha1']:
			return False
		if res['sha256']!=None and res['sha256']!=hashes['sha256']:
			return False
		UpqDB().query("UPDATE file set md5='%s', sha1='%s', sha256='%s' WHERE fid=%d" %
			(hashes['md5'], hashes['sha1'], hashes['sha256'], fid))
		self.msg("md5: %s sha1: %s sha256: %s" % (hashes['md5'], hashes['sha1'], hashes['sha256']))
		return True

	def hash(self, filename):
		"""
        Calculate hashes (md5, sha1, sha256) of a given file

        filename is absolute path to file

        returns: {'md5': 'x', 'sha1': 'y', 'sha256': 'z'}
        """

		md5 = hashlib.md5()
		sha1 = hashlib.sha1()
		sha256 = hashlib.sha256()

		try:
			fd = open(filename, "rb", 4096)
		except IOError, ex:
			msg = "Unable to open '%s' for reading: '%s'." % (filename, ex)
			self.logger.error(msg)
			raise Exception(msg)
		
		while True:
			data = fd.read(4096)
			if not data: break
			md5.update(data)
			sha1.update(data)
			sha256.update(data)

		fd.close()

		return {'md5': md5.hexdigest(), 'sha1': sha1.hexdigest(), 'sha256': sha256.hexdigest()}
