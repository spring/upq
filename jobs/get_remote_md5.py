# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import urllib

import upqdb
from upqjob import UpqJob

class Get_remote_md5(UpqJob):
    """
    Get_remote_md5: retrieve md5 checksum calculated by PHP-script "deamon.php"
    from remote mirror server
    
    either "fmfid" or "fid AND fmid" or "filename AND fmid" must be set 
    
    fid can be set with set_fid()
    fmfid can be set with set_fmfid()
    fmid can be set with set_fmid()
    filename can be set with set_filename()
    
    run() sets result=(str)<retrieved md5 hash>
    """
    fid   = 0
    fmid  = 0
    fmfid = 0
    filename = ""
    where = ""
    
    def set_fid(self, fid):
        self.fid = fid
    
    def set_fmid(self, fmid):
        self.fmid = fmid
    
    def set_fmfid(self, fmfid):
        self.fmfid = fmfid
    
    def set_filename(self, filename):
        self.filename = filename
    
    def check(self):
        if self.fmfid:
            self.where = "fmfid = %s"%self.fmfid
        elif self.fmid and self.fid:
            self.where = "fmid = %s AND fid = %s"%(self.fmid, self.fid)
        elif self.fmid and self.filename:
            pass
        else:
            self.msg = "This module must be used with either fmfid!=0 or fid!=0 AND fmid!=0 or filename!=\"\" AND fmid!=0."
            self.logger.error(self.msg)
            return False
        self.enqueue_job()
        return True
    
    def run(self):
        if not self.filename:
            # get path and mirror id
            result = upqdb.UpqDB().query("SELECT * FROM file_mirror_files WHERE %s"%self.where)
            res = result.first()
            self.filename = res['path']
            self.fmid = res['fmid']
        
        # get http connection params and construct URL
        result = upqdb.UpqDB().query("SELECT url_prefix, url_deamon FROM file_mirror WHERE fmid = %s"%self.fmid)
        res = result.first()
        script_url = res['url_prefix']+"/"+res['url_deamon']
        params     = urllib.urlencode({'p': self.filename})
        hash_url   = script_url+"?%s"%params
        
        # retrieve md5 hash from deamon.php on remote mirror server
        self.logger.debug("retrieving '%s'", hash_url)
        hash_file = urllib.urlopen(hash_url)
        hash = hash_file.read()
        
        self.msg = "received md5 hash for filename=%s on fmid=%s is %s" %(self.filename, self.fmid, hash)
        self.result = hash
        self.logger.debug(self.msg)
        return True
