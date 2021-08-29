# This file is part of the "upq" program used on springfiles.springrts.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2012 Matthias Ableitner (spring #at# abma #dot# de)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# fetches version information from http://springrts.com/dl/buildbot

from upqjob import UpqJob
from upqdb import UpqDB, UpqDBIntegrityError
import datetime
import json
import logging

class Versionfetch(UpqJob):
	prefix = "https://springrts.com/dl/buildbot"
	cats = {}
	def escape(self, string):
		return string.replace("%7b", "{").replace("%7d", "}")

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
		if not branch in ('master'):
			version = version + ' ' + branch
		url = self.prefix +'/' + data['path']
		cid = self.getCID(category)
		#print "%s %s %s %s" % (filename, version, category, url)
		res = UpqDB().query("SELECT fid, md5 from file WHERE version='%s' and cid=%s" % (version, cid))
		fileinfo = res.first()
		if fileinfo:
			fid = fileinfo[0]
			assert(fid > 0)
			if data["md5"] != fileinfo[1]:
				UpqDB().query("UPDATE file set md5='%s' WHERE fid=%s"%  (data['md5'], fid))
		else:
			fid = UpqDB().insert("file", {
				"filename" : filename,
				"name": "spring",
				"version": version,
				"cid" : cid,
				"md5" : data['md5'],
				"timestamp": datetime.datetime.fromtimestamp(data['filectime']),
				#"timestamp": data['filectime'],
				"size": data['filesize'],
				"status": 1,
				})


		res = UpqDB().query("SELECT mfid FROM mirror_file WHERE mid=%s AND fid=%s" % (mid, fid))
		mfid = res.first()
		if mfid:
			mfid = mfid[0]
			assert(mid > 0)
			UpqDB().query("UPDATE mirror_file SET lastcheck=NOW(), path='%s' WHERE mfid = %s"% (data['path'], mfid))
		else:
			mfid = UpqDB().insert("mirror_file", {
				"mid" : mid,
				"path": data['path'],
				"status": 1,
				"fid": fid,
				"lastcheck": UpqDB().now()
				})

	def run(self):
		url = self.prefix + '/list.php'

		filename = "/tmp/sprinvers.json"

		if not self.DownloadFile(url, filename):
			logging.info("list.php wasn't changed")
			return True

		with open(filename, "r") as f:
			data = json.loads(str(f.read()))
		res = UpqDB().query("SELECT mid from mirror WHERE url_prefix='%s'" % self.prefix)
		mid = res.first()[0]
		assert(mid > 0)
		for row in data:
			self.update(row, mid)
		#delete files that wheren't updated this run (means removed from mirror)
		UpqDB().query("DELETE FROM `mirror_file` WHERE `lastcheck` < NOW() - INTERVAL 1 HOUR AND mid = %s" %(mid))
		return True

