# This file is part of the "upq" program used on springfiles.springrts.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2012 Matthias Ableitner (spring #at# abma #dot# de)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# fetches version information from http://springrts.com/dl/buildbot

from lib import upqdb, download
import datetime
import json
import logging

def escape(string):
	return string.replace("%7b", "{").replace("%7d", "}")


class Versionfetch():
	prefix = "https://springrts.com/dl/buildbot"


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
		filename = escape(data['path'][data['path'].rfind("/")+1:])
		category = "engine_" + data['os']
		branch = data['branch']
		version = data['version']
		if not branch in ('master'):
			version = version + ' ' + branch
		url = self.prefix +'/' + data['path']
		cid = upqdb.getCID(self.db, category)
		#print "%s %s %s %s" % (filename, version, category, url)
		res = self.db.query("SELECT fid, md5, timestamp from file WHERE version='%s' and cid=%s" % (version, cid))
		fileinfo = res.first()
		timestamp = datetime.datetime.fromtimestamp(data['filectime'])
		if fileinfo:
			fid = fileinfo[0]
			assert(fid > 0)
			if data["md5"] != fileinfo[1] or timestamp != fileinfo[2]:
				self.db.query("UPDATE file set md5='%s', timestamp='%s' WHERE fid=%s"%  (data['md5'], timestamp, fid))
		else:
			fid = self.db.insert("file", {
				"filename" : filename,
				"name": "spring",
				"version": version,
				"cid" : cid,
				"md5" : data['md5'],
				"timestamp": timestamp,
				"size": data['filesize'],
				"status": 1,
				})


		res = self.db.query("SELECT mfid FROM mirror_file WHERE mid=%s AND fid=%s" % (mid, fid))
		mfid = res.first()
		if mfid:
			mfid = mfid[0]
			assert(mid > 0)
			self.db.query("UPDATE mirror_file SET lastcheck=NOW(), path='%s' WHERE mfid = %s"% (data['path'], mfid))
		else:
			mfid = self.db.insert("mirror_file", {
				"mid" : mid,
				"path": data['path'],
				"status": 1,
				"fid": fid,
				"lastcheck": upqdb.now()
				})

	def __init__(self, cfg, db):
		url = self.prefix + '/list.php'
		filename = "/tmp/sprinvers.json"
		self.db = db

		if not download.DownloadFile(url, filename):
			logging.info("list.php wasn't changed")
			return

		with open(filename, "r") as f:
			data = json.loads(str(f.read()))
		res = self.db.query("SELECT mid from mirror WHERE url_prefix='%s'" % self.prefix)
		mid = res.first()[0]
		assert(mid > 0)
		for row in data:
			self.update(row, mid)
		#delete files that wheren't updated this run (means removed from mirror)
		self.db.query("DELETE FROM `mirror_file` WHERE `lastcheck` < NOW() - INTERVAL 1 HOUR AND mid = %s" %(mid))

