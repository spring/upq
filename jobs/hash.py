# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# calculate hash, called with fileid
# calls metadata extraction
#

import hashlib
import os.path

from upqjob import UpqJob
from upqdb import UpqDB
from upqdb import UpqDBIntegrityError

class Hash(UpqJob):
	"""
		requirements to run hash:
			file is in db + file has to exist
	"""
	#TODO: allow recheck hash if last check of hash is older than one year (time taken from config)
	def check(self):
		results = UpqDB().query("SELECT filepath,md5 FROM files as f LEFT JOIN filehash as h ON f.fid=h.fid WHERE f.fid=%d " % int(self.jobdata['fid']))
		if results.rowcount > 1:
			self.msg = "Integry check failed, more than 1 file to hash in result"
			return False
		for res in results:
			if len(res['md5']) > 0: #md5 already present, don't hash again
				self.msg = "MD5 already present: " + res['md5']
				return False
			self.enqueue_job()
			if not os.path.isfile(self.jobcfg['path'] + res['filepath']):
				self.msg = "File not found " + self.jobcfg['path'] + res['filepath']
				return False;
			return True
		self.msg = "File not found"
		return False

	def run(self):
		"""
			class Hash must be initialized with fileid!
		"""
		fid = int(self.jobdata['fid'])
		results = UpqDB().query("SELECT * FROM files f LEFT JOIN filehash h ON f.fid=h.fid WHERE f.fid=%d  " % int(fid))
		for res in results:
			file = self.jobcfg['path'] + res['filepath']
			hashes = self.hash(file)

			try:
				UpqDB().insert("filehash", { "fid": fid, "md5": hashes['md5'], "sha1": hashes['sha1'], "sha256": hashes['sha256'] })
			except UpqDBIntegrityError:
				self.msg = "Hash already exists in db, not updating"
		self.enqueue_newjob("extract_metadata",{"fid": fid})
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
