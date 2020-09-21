# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Matthias Ableitner (spring #at# abma #dot# de)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# uploads fid to one mirror

from upqjob import UpqJob
import ftplib
from upqdb import UpqDB,UpqDBIntegrityError
from upqconfig import UpqConfig
import os.path
import socket

class Upload(UpqJob):
	def check(self):
		self.enqueue_job()
		return True

	def deleteOldFiles(self):
		"""
			deletes files from ftpmirror when:
				file is older than 100 days
				it is known in rapid
				it is not a stable|test tag (no number at the end in tag)
		"""
		results = UpqDB().query("SELECT m.mid, ftp_url, ftp_user, ftp_pass, ftp_dir, ftp_port, ftp_passive, ftp_ssl \
FROM mirror as m \
WHERE m.status=1")
		for mirror in results:
			results2 = UpqDB().query("SELECT f.fid,tag FROM `file` f \
LEFT JOIN tag t ON f.fid=t.fid \
WHERE (t.fid>0) \
AND f.status=1 \
AND timestamp < NOW() - INTERVAL 100 DAY \
GROUP BY f.fid HAVING count(f.fid) = 1")
			ftp = None
			for filetodel in results2:
				if not ftp:
					try:
						ftp = self.ftpconnect(mirror['ftp_url'], mirror['ftp_port'], mirror['ftp_user'], mirror['ftp_pass'], mirror['ftp_passive'], mirror['ftp_dir'], mirror['ftp_ssl'])
					except Exception as e:
						self.logger.error("Couldn't connect to %s: %s",mirror['ftp_url'], e)
						break
				res2 = UpqDB().query("SELECT * FROM mirror_file WHERE fid = %d AND mid = %d AND status=1" % (filetodel['fid'], mirror['mid']))
				curfile = res2.first()
				if curfile and filetodel['tag'][-1].isdigit():
					try:
						self.logger.error("deleting %s" % (curfile['path']))
						ftp.delete(curfile['path'])
					except:
						pass
					UpqDB().query("UPDATE mirror_file SET status=4 WHERE mfid = %d" % (int(curfile['mfid'])))
			if ftp:
				ftp.close()
	def ftpconnect(self, host, port, username, password, passive, cwddir, ssl):
		"""return the ftp connection handle"""
		if ssl:
			try:
				self.logger.debug("Using tls")
				ftp = ftplib.FTP_TLS()
			except Exception as e:
				self.logger.error("TLS not supported")
				ftp = ftplib.FTP()
		else:
			ftp = ftplib.FTP()
		#set global timeout
		socket.setdefaulttimeout(30)
		self.logger.debug("connecting to "+host)
		ftp.connect(host,port)
		if ssl:
			try:
				ftp.auth()
			except Exception as e:
				self.logger.error("Setting up tls connection failed: %s", e)
		ftp.login(username, password)
		if (passive):
			self.logger.debug("Enabling passive mode")
		ftp.set_pasv(passive) #set passive mode
		if (len(cwddir)>0):
			self.logger.debug("cd into "+cwddir)
			ftp.cwd(cwddir)
		return ftp

	def run(self):
		fid=int(self.jobdata['fid'])
		results = UpqDB().query("SELECT filename, path, size, md5 FROM file where fid=%d AND status=1"% (fid))
		if results.rowcount!=1:
			self.msg("Wrong result count with fid %d" % fid)
			return False
		res=results.first()
		srcfilename=os.path.join(UpqConfig().paths['files'], res['path'], res['filename'])
		dstfilename=os.path.join(res['path'], res['filename'])
		#uploads a fid to all mirrors
		results = UpqDB().query("SELECT m.mid, ftp_url, ftp_user, ftp_pass, ftp_dir, ftp_port, ftp_passive, ftp_ssl \
						from file f  \
						left join mirror m on m.status=f.status \
						where f.fid=%d and f.status=1 and m.status=1 \
						and m.mid not in (select mid from mirror_file where fid=%d and status = 1)"% (fid, fid))
		uploadcount=0
		for res in results:
			try:
				ftp = self.ftpconnect(res['ftp_url'], res['ftp_port'], res['ftp_user'], res['ftp_pass'], res['ftp_passive'], res['ftp_dir'], res['ftp_ssl'])
			except Exception as e:
				self.logger.error("Couldn't connect to the ftp server: %s", e)
				continue
			if not os.path.isfile(srcfilename):
				self.msg("File doesn't exist: " + srcfilename)
				return False
			try:
				f=open(srcfilename,"rb")

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
				self.logger.info("uploading %s to %s" % (os.path.basename(dstfilename),(res['ftp_url'])))
				ftp.storbinary('STOR '+os.path.basename(dstfilename), f)

				ftp.quit()
				f.close()
				try: #upload succeed, mark in db as uploaded
					id=UpqDB().insert("mirror_file", {"mid":res['mid'],"fid":fid, "path":dstfilename, "status":1})
				except UpqDBIntegrityError:
					res=UpqDB().query("SELECT mfid FROM mirror_file WHERE mid=%s AND fid=%s" % (res['mid'], fid))
					id=res.first()
					self.logger.info("file already uploaded: mfid=%d" % (id))
					UpqDB().query("UPDATE mirror_file SET status=1 path='%s' WHERE mfid=%s" % (dstfilename, id))
				self.logger.debug("inserted into db as %d", id)
				self.enqueue_newjob("verify_remote_file", {"mfid": id})
			except ftplib.all_errors as e:
				self.logger.error("Ftp-Error (%s) %s failed %s" % ((res['ftp_url'], srcfilename,e)))
			except Exception as e:
				self.logger.error("Upload (%s) %s failed %s" % ((res['ftp_url'], srcfilename,e)))
				return False
			uploadcount+=1
		self.msg("Uploaded to %d mirrors." % (uploadcount))
		self.deleteOldFiles()
		return True

