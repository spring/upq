# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# Remote_md5: retreive md5 checksum calculated by PHP-script "deamon.php" from
# remote mirror server
#

#
# fid must be set as "fileid" when calling __init__(filename, fileid, config, thread)
# fmid is set by calling set_fmid(fmid)   (fmid must be of type int)
# run() sets result=(str)<retrieved md5 hash>
#

import urllib

import tasks.upqtask
import upqdb

class Remote_md5(tasks.upqtask.UpqTask):
    
    def set_fmid(fmid):
        """
        fmid is of type int!
        """
        self.fmid = fmid
    
    def run(self):
        # get http connection params from DB
        db = upqdb.UpqDB().getdb(self.thread)
        script_url = db.get_remote_hash_url(self.set_fmid)
        
        # retrieve md5 hash from deamon.php on remote mirror server
        params = urllib.urlencode({'p': self.fileid})
        hash_url = script_url+"?%s"%params
        hash_file = urllib.urlopen(hash_url)
        hash = hash_file.read()
        logger.debug("received md5 hash for fid='%d' on fmid='%d' is '%s'",
                     self.fileid, self.fmid, hash)
        
        self.result = hash
