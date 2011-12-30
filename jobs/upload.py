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
from upqdb import UpqDB,UpqDBIntegrityError
from upqconfig import UpqConfig
import os.path
import socket

class Upload(UpqJob):
    def check(self):
        #TODO: merge these TODOS, this can be done simpler, i feel it (at least move stuff into cron) :)
        #TODO: check if file is already marked in db as uploaded
        #TODO: reupload files with invalid md5
        #TODO: test + test +test + improve this!
        #TODO: create a job for each ftp-mirror here
        #TODO: create a cron-job or something similar, that creates upload jobs, when a new mirror is added (like a validation for all files/mirrors)
        #TODO: check files with the same path (or use path from files?)
        #TODO: always spawn upload job for all mirrors + recheck md5

        self.enqueue_job()
        return True

    def run(self):
        fid=int(self.jobdata['fid'])
        results = UpqDB().query("SELECT filename, path, size, md5 FROM file where fid=%d AND status=1"% (fid))
        if results.rowcount!=1:
            self.msg("Wrong result count with fid %d" % fid)
            return False
        res=results.first()
        srcfilename=os.path.join(UpqConfig().paths['files'], res['path'], res['filename'])
        dstfilename=os.path.join(res['path'], res['filename'])
        filesize=res['size']
        md5=res['md5']
        #uploads a fid to all mirrors
        results = UpqDB().query("SELECT m.mid, ftp_url, ftp_user, ftp_pass, ftp_dir, ftp_port, ftp_passive, ftp_ssl \
FROM mirror as m \
LEFT JOIN mirror_file as f ON m.mid=f.mid \
WHERE m.status=1 \
AND m.status=1 \
AND f.status = 1 \
AND m.mid not in ( \
	SELECT mid FROM mirror_file WHERE fid=%d AND status=1\
) \
GROUP by m.mid"% fid)
        uploadcount=0
        for res in results:
            host=res['ftp_url']
            port=res['ftp_port']
            username=res['ftp_user']
            password=res['ftp_pass']
            passive=int(res['ftp_passive'])>1
            cwddir=res['ftp_dir']
            if not os.path.isfile(srcfilename):
                self.msg("File doesn't exist: " + srcfilename)
                return False
            try:
                f=open(srcfilename,"rb")
                ftp = ftplib.FTP_TLS()
                #set global timeout
                socket.setdefaulttimeout(30)
                ftp = ftplib.FTP()
                self.logger.debug("connecting to "+host)
                ftp.connect(host,port)
#                if (res['ftp_ssl']):
#                   ftp.auth(username, password)
#                else:
                ftp.login(username, password)
                ftp.set_pasv(passive) #set passive mode
                if (len(cwddir)>0):
                    self.logger.debug("cd into "+cwddir)
                    ftp.cwd(cwddir)
                dstdir=os.path.dirname(dstfilename)
                try:
                    self.logger.debug("cd into "+dstdir)
                    ftp.cwd(dstdir)
                except:
                    try:
                        self.logger.debug("mkdir "+dstdir)
                        ftp.mkd(dstdir)
                        self.logger.debug("cwd "+dstdir)
                        ftp.cwd(dstdir)
                    except:
                        self.logger.error("couldn't cd/mkdir %s, skipping upload " % (dstdir))
                        continue
                self.logger.info("uploading %s to %s" % (os.path.basename(dstfilename),host))
                ftp.storbinary('STOR '+os.path.basename(dstfilename), f)
                ftp.quit()
                f.close()
                try: #upload succeed, mark in db as uploaded
                    id=UpqDB().insert("mirror_file", {"mid":res['mid'],"fid":fid, "path":dstfilename, "status":1})
                except UpqDBIntegrityError:
					self.logger("file already uploaded: mfid=%d" % (id))
                self.logger.debug("inserted into db as %d", id)
                self.enqueue_newjob("verify_remote_file", {"mfid": id})
            except ftplib.all_errors as e:
                self.logger.error("Ftp-Error (%s) %s failed %s" % (host, srcfilename,e))
            except Exception as e:
                self.logger.error("Upload (%s) %s failed %s" % (host, srcfilename,e));
                return False
            uploadcount+=1
        self.msg("Uploaded to %d mirrors." % (uploadcount))
        return True
