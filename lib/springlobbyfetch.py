# This file is part of the "upq" program used on springfiles.springrts.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2012 Matthias Ableitner (spring #at# abma #dot# de)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# fetches version information from 

from upqjob import UpqJob
from upqdb import UpqDB, UpqDBIntegrityError
import datetime
import urllib
import socket
import json
import logging

class my_download(urllib.URLopener):
	def http_error_default(self, url, fp, errcode, errmsg, headers):
		raise Exception("Error retrieving %s %d %s" %(url, errcode, errmsg))

class Springlobbyfetch(UpqJob):
	stablever = "http://version.springlobby.info/current.txt"
	stabledl = "http://springlobby.info/windows/springlobby-%s-win32.zip"
	develver = "http://springlobby.info/temp/builds/abma/current.txt"
	develdl = "http://springlobby.info/temp/builds/abma/sl_master.zip"

	def getCID(self, category):
		if category in self.cats:
			return self.cats[category]
		res = UpqDB().query("SELECT cid from categories WHERE name='%s'" % (category))
		try:
			self.cats[category]=res.first()[0] # cache result
		except:
			logging.error("Invalid category: %s" % category)
		return self.cats[category]

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
		cid = self.getCID(category)
		#print "%s %s %s %s" % (filename, version, category, url)
		try:
			fid = UpqDB().insert("file", {
				"filename" : filename,
				"name": "spring",
				"version": version,
				"cid" : cid,
				"md5" : data['md5'],
				"timestamp": datetime.datetime.fromtimestamp(data['filectime']),
				#"timestamp": data['filectime'],
				"size": data['filesize'],
				"status": 1 })
		except UpqDBIntegrityError, e:
			try:
				res = UpqDB().query("SELECT fid from file WHERE version='%s' and cid=%s" % (version, cid))
				fid = res.first()[0]
				UpqDB().query("UPDATE file set md5='%s' WHERE fid=%s"%  (data['md5'], fid))
			except Exception, e:
				logging.error("Error %s %s %s", version, cid, e)
				return
		relpath = self.escape(url[len(self.prefix)+1:])
		try:
			id = UpqDB().insert("mirror_file", {
				"mid" : mid,
				"path": relpath,
				"status": 1,
				"fid": fid,
				"lastcheck": UpqDB().now()
				})
		except UpqDBIntegrityError:
			res = UpqDB().query("SELECT mfid FROM mirror_file WHERE mid=%s AND fid=%s" % (mid, fid))
			id = res.first()[0]
			UpqDB().query("UPDATE mirror_file SET lastcheck=NOW() WHERE mfid = %s"% (id))

	def run(self):
		dled = {}
		url = self.prefix + '/list.php'
		#print self.getlobbyversion()
		f = my_download().open(url)
		data = json.loads(str(f.read()))
		res = UpqDB().query("SELECT mid from mirror WHERE url_prefix='%s'" % self.prefix)
		mid = res.first()[0]
		for row in data:
			self.update(row, mid)
		#delete files that wheren't updated this run (means removed from mirror)
		UpqDB().query("DELETE FROM `mirror_file` WHERE `lastcheck` < NOW() - INTERVAL 1 HOUR AND mid = %s" %(mid))
		urllib.urlcleanup()
		return True

