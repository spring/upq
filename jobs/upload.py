# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# upload_file

from upqjob import UpqJob
import ftplib

class Upload(UpqJob):
    def check(self):
	print self.jobdata
        try:
		self.filename=self.jobdata['filename']
	except:
		self.msg="invalid filename"
		return False
        self.enqueue_job()
        return True

    def run(self):
        try:
            f=open(self.filename,"rb")
            ftp = ftplib.FTP()
            db = upqdb.UpqDB()
            self.filename = db.query(self.fileid, 'filepath')
            ftp.connect('myserver.com',21)
            ftp.login('login','password')
            ftp.storbinary('STOR '+filename, f)
            ftp.quit()
        finally:
            f.close()
            raise Exception
        return True

