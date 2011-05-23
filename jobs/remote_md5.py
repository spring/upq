# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import urllib

import upqdb

class Remote_md5(UpqJob):
    def check(self):
		"""

		"""
		for file in self.jobdata['fmfid'] do:
			res = upqdb.UpqDB().query("SELECT * FROM file_mirror_files as f LEFT JOIN file_mirror as m ON f.fmid=m.fmid WHERE f.fmfid=%s" % file)

		return True
    """
    Remote_md5: retreive md5 checksum calculated by PHP-script "deamon.php" from
    remote mirror server
    
    either "fmfid" or "fid AND fmid" or "filename AND fmid" must be set 
    
    run() sets result=(str)<retrieved md5 hash>
    """

    def run(self):

        # get http connection params from DB and construct URL
        self.hash_in_db = db.get_remote_file_hash(self.fmfid, self.fmid, self.fileid)
        script_url = db.get_remote_hash_url(self.hash_in_db['fmid'])
        params     = urllib.urlencode({'p': self.hash_in_db['path']})
        hash_url   = script_url+"?%s"%params

        # retrieve md5 hash from deamon.php on remote mirror server
        hash_file = urllib.urlopen(hash_url)
        hash = hash_file.read()
        self.logger.debug("received md5 hash for fid='%s' on fmid='%s' is '%s'", self.fileid, self.fmid, hash)

        self.result = hash
