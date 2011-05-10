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

import log
import upqtask
import upqjob

class Verify_remote_file(UpqJob):
    def check():
        # find file in DB
        if len(self.jobdata) == 1:
            # should be fmfid
            try:
                self.fmfid = int(self.jobdata[0])
            except ValueError:
                msg = "Expected fmfid in jobdata[0], jobdata='%s'"%self.jobdata
                self.logger.error(msg)
                return {'queued': False, 'jobid': -1, 'msg': msg}
        elif len(self.jobdata) == 2:
        # should be fid fmid
            try:
                self.fileid = int(self.jobdata[0])
                self.fmid = int(self.jobdata[1])
            except ValueError:
                msg = "Expected fid in jobdata[0] and fmid in jobdata[1], "\
                      +"jobdata='%s'"%self.jobdata
                self.logger.error(msg)
                return {'queued': False, 'jobid': -1, 'msg': msg}
        else:
            msg = "Expected 'fmfid' OR 'fid fmid' in jobdata ('%s')"%self.jobdata
            self.logger.error(msg)
            return {'queued': False, 'jobid': -1, 'msg': msg}
        
        ## get filepath from DB
        #db = upqdb.UpqDB().getdb("main")
        #self.filename = db.get_from_files(self.fileid, 'filepath')
        #if not self.filename:
        #    msg = "File with fileid='%d' not found in DB."%self.fileid
        #    self.logger.error(msg)
        #    return {'queued': False, 'jobid': -1, 'msg': msg}
        
        self.enqueue_job()
        return {'queued': True, 'jobid': self.jobid, 'msg': self.filename}
    
    def run():
        
        
        
        
        
        
        
        pass
