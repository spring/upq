# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# called with fid, uploads fid to one mirror
#

from upqjob import UpqJob
import ftplib
from upqdb import UpqDB
import os.path

class Upload(UpqJob):
    def check(self):
         #TODO: check if file is already marked in db as uploaded
         #TODO: test + test +test + improve this!
         #TODO: create a job for each ftp-mirror here
         #TODO: create a cron-job or something similar, that creates upload jobs, when a new mirror is added (like a validation for all files/mirrors)
         self.enqueue_job()
         return True

    def run(self):
        fid=int(self.jobdata['fid'])
        results = UpqDB().query("SELECT filepath, filesize FROM files where fid=%d "% fid)
        if results.rowcount!=1:
            self.msg = "Wrong result count with fid %d" % fid
            return False
        res=results.first()
        srcfilename=self.jobcfg['path']+res['filepath']
        dstfilename=res['filepath'][len(self.jobcfg['prefix']):]
        filesize=res['filesize']
        #uploads a fid to all mirrors
        results = UpqDB().query("SELECT m.fmid, ftp_url, ftp_user, ftp_pass, ftp_dir, ftp_port, ftp_passive, ftp_ssl \
FROM file_mirror as m \
LEFT JOIN file_mirror_files as f ON m.fmid=f.fmid \
WHERE m.active=1 \
AND m.dynamic=1 \
AND m.fmid not in ( \
SELECT fmid FROM file_mirror_files WHERE fid=%d \
) \
GROUP by m.fmid"% fid)
        for res in results:
            host=res['ftp_url']
            port=res['ftp_port']
            username=res['ftp_user']
            password=res['ftp_pass']
            passive=int(res['ftp_passive'])>1
            cwddir=res['ftp_dir']
            if not os.path.isfile(srcfilename):
                self.msg="File doesn't exist: " + srcfilename
                return False
            try:
                f=open(srcfilename,"rb")
#springfiles has only python 2.6.4 installed no tls avaiable there :-(
#                ftp = ftplib.FTP_TLS()
                ftp = ftplib.FTP()
                self.logger.debug("connecting to "+host)
                ftp.connect(host,port)
#                if (res['ftp_ssl']):
#                    ftp.auth(username, password)
#                else:
                ftp.login(username, password)
                ftp.set_pasv(passive) #set passive mode
                self.logger.debug("cd into "+cwddir)
                ftp.cwd(cwddir)
                dstdir=os.path.dirname(dstfilename)
                try:
                    self.logger.debug("cd into "+dstdir)
                    ftp.cwd(dstdir)
                except:
                    self.logger.debug("mkdir "+dstdir)
                    ftp.mkd(dstdir)
                    self.logger.debug("cwd "+dstdir)
                    ftp.cwd(dstdir)
                self.logger.info("uploading %s to %s" % (os.path.basename(dstfilename),host))
                ftp.storbinary('STOR '+os.path.basename(dstfilename), f)
                ftp.quit()
                f.close()
                id=UpqDB().insert("file_mirror_files", {"fmid":res['fmid'],"fid":fid, "path":dstfilename, "size":filesize, "active":1, "changed":"now()"})
                self.logger.debug("inserted into db as %d", id)
            except ftplib.all_errors, e:
                self.logger.error("Ftp-Error (%s) %s failed %s" % (host, srcfilename,e))
            except Exception, e:
                self.logger.error("Upload (%s) %s failed %s" % (host, srcfilename,e));
                return False
        return True
