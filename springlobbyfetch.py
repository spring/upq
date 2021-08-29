# This file is part of the "upq" program used on springfiles.springrts.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2012 Matthias Ableitner (spring #at# abma #dot# de)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# fetches version information from 

from lib import log, upqdb, download
from lib.upqjob import UpqJob
import datetime
import socket
import json
import logging

prefix = "https://springlobby.springrts.com/dl"
stablever = prefix + "/stable/current.txt"
stabledl =  prefix + "/stable/springlobby-%s-win32.zip"
develver =  prefix + "/develop/version-develop.txt"
develdl =   prefix + "/develop/springloby-%s-win32.zip"

class Springlobbyfetch(UpqJob):

	def update(self, data, mid):
		"""
			data is an array with
				md5
				filectime
				version
				branch
				filesize
				os
				path
		"""
		if data['version'] == "testing":
			return
		filename = self.escape(data['path'][data['path'].rfind("/")+1:])
		category = "engine_" + data['os']
		branch = data['branch']
		version = data['version']
		if not data['branch'] in ('master'):
			version = data['version'] + ' ' + data['branch']
		url = self.prefix +'/' + data['path']
		cid = upqdb.getCID(category)
		#print "%s %s %s %s" % (filename, version, category, url)
		try:
			fid = upqdb.UpqDB().insert("file", {
				"filename" : filename,
				"name": "spring",
				"version": version,
				"cid" : cid,
				"md5" : data['md5'],
				"timestamp": datetime.datetime.fromtimestamp(data['filectime']),
				#"timestamp": data['filectime'],
				"size": data['filesize'],
				"status": 1 })
		except upqdb.UpqDBIntegrityError as e:
			try:
				res = upqdb.UpqDB().query("SELECT fid from file WHERE version='%s' and cid=%s" % (version, cid))
				fid = res.first()[0]
				upqdb.UpqDB().query("UPDATE file set md5='%s' WHERE fid=%s"%  (data['md5'], fid))
			except Exception as e:
				logging.error("Error %s %s %s", version, cid, e)
				return
		relpath = self.escape(url[len(self.prefix)+1:])
		try:
			id = upqdb.UpqDB().insert("mirror_file", {
				"mid" : mid,
				"path": relpath,
				"status": 1,
				"fid": fid,
				"lastcheck": upqdb.UpqDB().now()
				})
		except upqdb.UpqDBIntegrityError:
			res = upqdb.UpqDB().query("SELECT mfid FROM mirror_file WHERE mid=%s AND fid=%s" % (mid, fid))
			id = res.first()[0]
			upqdb.UpqDB().query("UPDATE mirror_file SET lastcheck=NOW() WHERE mfid = %s"% (id))

	def run(self):
		dled = {}
		#print self.getlobbyversion()
		f = download.DownloadFile(stablever, os.path.basename(stablever) )
		data = json.loads(str(f.read()))
		res = upqdb.UpqDB().query("SELECT mid from mirror WHERE url_prefix='%s'" % self.prefix)
		mid = res.first()[0]
		for row in data:
			self.update(row, mid)
		#delete files that wheren't updated this run (means removed from mirror)
		upqdb.UpqDB().query("DELETE FROM `mirror_file` WHERE `lastcheck` < NOW() - INTERVAL 1 HOUR AND mid = %s" %(mid))
		return True

#FIXME: implement this!

#l = Springlobbyfetch("springlobbyfetch", dict())
#l.run()
