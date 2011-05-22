# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# Verify_remote_file: check the integrity of a file on a mirror by comparing
# the result of the PHP-script "deamon.php" with the stored hash in the DB
# 

#
# call this module with argument "<fmfid>" OR "<fid> <fmid>"
#

import upqjob
import jobs.get_remote_md5
import upqdb

class Verify_remote_file(upqjob.UpqJob):
    
    where = ""

    def check(self):
        # set fmfid OR fid and fmid -> OK
        
        if self.jobdata.has_key('fmfid'):
            self.where = "fmfid = %s"%self.jobdata['fmfid']
        elif self.jobdata.has_key('fid') and self.jobdata.has_key('fmid'):
            self.where = "fmid = %s AND fid = %s"%(self.jobdata['fmid'], self.jobdata['fid'])
        else:
            self.msg = "This module must be used with either fmfid!=0 or fid!=0 AND fmid!=0"
            self.logger.error(self.msg)
            return False
        
        self.enqueue_job()
        return True
    
    def run(self):    
        # get files hash from DB
        result = upqdb.UpqDB().query("SELECT * FROM file_mirror_files WHERE %s"%self.where)
        res = result.first()
        
        if not res:
            self.msg = "File with jobdata='%s' not found in DB."%(self.jobdata)
            self.logger.debug(self.msg)
            return False
        
        grmd5 = jobs.get_remote_md5.Get_remote_md5("get_remote_md5", self.jobdata)
        grmd5.set_fid(res['fid'])
        grmd5.set_fmid(res['fmid'])
        grmd5.set_fmfid(res['fmfid'])
        grmd5.check()
        grmd5.finished.wait()
        if res['md5'] == grmd5.result:
            self.msg = 'Remote hash matches hash in DB.'
            return True
        else:
            self.msg  = 'Remote hash does NOT match hash in DB.'
            return False

