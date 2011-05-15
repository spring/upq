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
        self.enqueue_job()
        return {'queued': True, 'jobid': self.jobid, 'msg': "upload job"}

    def run(self):
        f=open(filename,"rb")
        ftp = ftplib.FTP()
#                db = upqdb.UpqDB()
#                self.filename = db.query(self.fileid, 'filepath')
        try:
            ftp.connect('myserver.com',21)
            ftp.login('login','password')
            ftp.storbinary('STOR '+filename, f)
        finally:
            f.close()
            ftp.quit()
        self.result  = {'success': True, 'msg': 'upload ok' }
