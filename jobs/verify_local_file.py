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
from upqjob import UpqJob
import upqdb
import upqconfig
import hashlib


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
        query="SELECT filepath FROM files WHERE fid = %d" % self.fileid
        res = upqdb.UpqDB().query(query)
        self.filename = res.first()['filepath']
        if not self.filename:
            self.msg = "File with fileid='%d' not found in DB."%self.fileid
            return False
        try:
            open(self.filename, "rb")
        except IOError, ex:
            self.msg = "File is not readable: '%s'"%ex
            self.logger.error(self.msg)
            return False
        
        self.enqueue_job()
        return True
    
    def run(self):
        ondisk = self.hash(self.filename)
        
        # compare with hashes stored in DB
        query="SELECT md5, sha1, sha256 FROM filehash WHERE fid = %d" % self.fileid
        res = upqdb.UpqDB().query(query)
        db_hashes = res.first()
        
        for hash in db_hashes.keys():
            if not db_hashes[hash] == ondisk[hash]:
                self.msg = "Hash %s of file (fid) %s (%d) does not match."%(hash, self.filename, self.fileid)
                self.logger.info(self.msg)
                return False
        
        # all hashes must have matched
        self.msg = "Hashes of file (fid) %s (%d) on-disk match those in DB."%(self.filename, self.fileid)
        self.logger.info(self.msg)
        return True

    def hash(self, filename):
        """
        Calculate hashes (md5, sha1, sha256) of a given file
        
        filename is absolute path to file
        
        returns: {'md5': 'x', 'sha1': 'y', 'sha256': 'z'}
        """
        
        logger = log.getLogger()
        
        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        sha256 = hashlib.sha256()
        
        try:
            fd = open(filename, "rb", 4096)
        except IOError, ex:
            msg = "Unable to open the file for reading: '%s'."%ex
            logger.error(msg)
            raise Exception(msg)
        while True:
            data = fd.read(4096)
            if not data: break
            md5.update(data)
            sha1.update(data)
            sha256.update(data)
        
        fd.close()
        
        return {'md5': md5.hexdigest(), 'sha1': sha1.hexdigest(), 'sha256': sha256.hexdigest()}
