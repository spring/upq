# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Verify_remote_file: check the integrity of a file on a mirror by comparing
# the result of the PHP-script "daemon.php" with the stored hash in the DB


import upqjob
import upqdb
import urllib

class Verify_remote_file(upqjob.UpqJob):

	def check(self):
		# TODO: check if time last file checked is < 1 Year
		self.enqueue_job()
		return True

	def run(self):
		"""
			call this module with argument "<fmfid>"
		"""
		# get files hash from DB
		fmfid=int(self.jobdata['mfid'])
		result = upqdb.UpqDB().query("SELECT md5, mf.fid, url_prefix, url_daemon, mf.path \
			FROM mirror AS m \
			LEFT JOIN mirror_file as mf ON m.mid=mf.mid \
			LEFT JOIN file as f ON f.fid=mf.fid \
			WHERE mfid=%d "%fmfid)
		res = result.first()

		if not res:
			self.msg("File with jobdata='%s' not found in DB."%(self.jobdata))
			return False

		script_url = res['url_prefix']+"/"+res['url_daemon']
		params	 = urllib.urlencode({'p': res['path']})
		hash_url   = script_url+"?%s"%params
		file_path  = res['path']

	        md5 = res['md5']
	        # retrieve md5 hash from deamon.php on remote mirror server
	        self.logger.debug("retrieving '%s'", hash_url)
		try:
	  		hash_file = urllib.urlopen(hash_url)
	 		hash = hash_file.read()
	                hash_file.close()
		except Exception as e:
			self.logger.error(str(e))
			return false

		self.msg("received md5 hash for filename=%s on fmfid=%s is %s" %(file_path, fmfid, hash))
		self.result = hash
	
		if res['md5'] == hash:
			#TODO add notify job here
			upqdb.UpqDB().query("UPDATE mirror_file SET lastcheck=NOW(), status=1 WHERE mfid=%d" %(fmfid))
			self.msg('Remote hash matches hash in DB.')
			return True
		else:
			if len(hash)==32:
				#TODO: delete from db to allow re-upload
				query="UPDATE mirror_file SET status=0 WHERE mfid=%s " %(hash, fmfid)
				upqdb.UpqDB().query(query)
				self.msg('Remote hash does NOT match hash in DB.')
			else:
				self.msg('error retrieving hash from ' + hash_url)
			return False

