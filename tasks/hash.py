# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# Hash: compute has of a file (either filename or fileid must not be None)
#

import hashlib

import upqtask
import upqdb

class Hash(upqtask.UpqTask):
    """
    class Hash must be initialized with either filepath or fileid!
    """
    def run(self):
        self.logger.debug("lets go")
        
        if not self.filename:
            if not self.fileid:
                self.result['msg'] = "class Hash must be initialized with "\
                +"either filepath or fileid."
                self.logger.error(self.result['msg'])
                return False
            else:
                # get filepath from DB
                db = upqdb.UpqDB().getdb(self.thread)
                self.filename = db.get_from_files(self.fileid, 'filepath')
        
        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        sha256 = hashlib.sha256()
        
        try:
            fd = open(self.filename, "rb", 4096)
        except IOError, ex:
            self.result['msg'] = "Unable to open the file for reading: '%s'."%ex
            self.logger.error(self.result['msg'])
            raise Exception(self.result['msg'])
        while True:
            data = fd.read(4096)
            if not data: break
            md5.update(data)
            sha1.update(data)
            sha256.update(data)
        
        fd.close()
        
        self.result = {}
        self.result['md5']    = md5.hexdigest()
        self.result['sha1']   = sha1.hexdigest()
        self.result['sha256'] = sha256.hexdigest()
        #self.logger.debug("result='%s'", self.result)
        
        return True
    
