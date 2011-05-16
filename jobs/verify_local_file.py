# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# Verify_local_file: check a files integrity by comparing the hash of the
# on-disk file with the stored hash in the DB
# 

#
# call module with <fid>
#

import log
import upqtask
from upqjob import UpqJob
import upqdb

class Verify_local_file(UpqJob):
    def check(self):
        # we need a fileid
        try:
            self.fileid = int(self.jobdata['fid'])
        except ValueError:
            self.msg = "Expected fid in jobdata['fid'], jobdata='%s'"%self.jobdata
            return False
        
        # check if file is readable
        # get filepath from DB
        db = upqdb.UpqDB().getdb("main")
        self.filename = db.get_from_files(self.fileid, 'filepath')
        if not self.filename:
            self.msg = "File with fileid='%d' not found in DB."%self.fileid
            return False
        try:
            open(self.filename, "rb")
        except IOError, ex:
            msg = "File is not readable: '%s'"%ex
            self.logger.error(msg)
            return False
        
        self.enqueue_job()
        return True
    
    def run(self):
        h = self.tasks['hash']("", self.fileid, self.jobcfg, self.thread)
        # compute hashes
        h.run()
        ondisk = h.get_result()
        self.logger.debug("tasks result is: '%s'", ondisk)
        
        # compare with hashes stored in DB
        db = upqdb.UpqDB().getdb(self.thread)
        db_hashes = db.get_from_filehashes(self.fileid)
        
        for hash in db_hashes.keys():
            if hash == "fid": continue
            if not db_hashes[hash] == ondisk[hash]:
                self.logger.info("Hash '%s' of fileid '%s' does not match."%(hash, self.fileid))
                return False
        
        # all hashes must have matched
        self.logger.info("Hashes of fileid '%s' on-disk match those in DB."%(self.fileid))
        return True

