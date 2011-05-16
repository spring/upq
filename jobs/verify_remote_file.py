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
import tasks.remote_md5
import upqdb

class Verify_remote_file(upqjob.UpqJob):
    def check(self):
        # find file in DB -> OK
        
        if len(self.jobdata) == 1:
            # should be fmfid
            try:
                self.fmfid  = int(self.jobdata['fmfid'])
                self.fileid = 0
                self.fmid   = 0
            except ValueError:
                self.msg = "Expected fmfid in jobdata['fmfid'], jobdata='%s'"%self.jobdata
                return False
        elif len(self.jobdata) == 2:
        # should be fid fmid
            try:
                self.fmfid  = 0
                self.fileid = int(self.jobdata['fid'])
                self.fmid   = int(self.jobdata['fmfid'])
            except ValueError:
                self.msg = "Expected fid in jobdata[0] and fmid in jobdata[1], "+"jobdata='%s'"%self.jobdata
                return False
        else:
            self.msg = "Expected 'fmfid' OR 'fid fmid' in jobdata ('%s')"%self.jobdata
            return False
        
        # get files hash from DB
        db = upqdb.UpqDB().getdb(self.thread)
        self.hash_in_db = db.get_remote_file_hash(self.fmfid, self.fmid, self.fileid)
        if not self.hash_in_db:
            self.msg = "File with fmfid='%s', fmid='%s', fileid='%s' not found in DB."%(self.fmfid, self.fmid, self.fileid)
            return False
        
        # set missing info from db
        if not self.fmfid:  self.fmfid = self.hash_in_db['fmfid']
        if not self.fmid:   self.fmid = self.hash_in_db['fmid']
        if not self.fileid: self.fileid = self.hash_in_db['fid']
        
        self.enqueue_job()
	self.msg=self.hash_in_db['path']
        return True
    
    def run(self):
        rmd5 = self.tasks['remote_md5'](self.hash_in_db['path'], self.fileid, self.jobcfg, self.thread)
        rmd5.set_fmid(self.fmid)
        rmd5.set_fmfid(self.fmfid)
        rmd5.run()
        
        if self.hash_in_db['md5'] == rmd5.result:
            self.msg = 'Remote hash matches hash in DB.'
            return True
        else:
            self.msg  = 'Remote hash does NOT match hash in DB.'
            return False

