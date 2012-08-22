# This file is part of the "upq" program used on springfiles.com to manage file
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
import urllib
import socket
import json

class my_download(urllib.URLopener):
	def http_error_default(self, url, fp, errcode, errmsg, headers):
		raise Exception("Error retrieving %s %d %s" %(url, errcode, errmsg))

class Versionfetch(UpqJob):
	prefix = "http://springrts.com/dl/buildbot"
	lobby = "lobby.springrts.com"
	lobbyport = 8200
	cats = {}
	def getlobbyversion(self):
		""" connects to the lobby server and returns the current spring version"""
		version = ""
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect((self.lobby, self.lobbyport))
			data = s.recv(1024)
			version = data.split(" ")[2]
			s.send("EXIT")
			s.close()
		except Exception as e:
			self.msg(str(e))
		return version
	def escape(self, string):
		return string.replace("%7b", "{").replace("%7d", "}")
	def getCID(self, category):
		if category in self.cats:
			return self.cats[category]
		res = UpqDB().query("SELECT cid from categories WHERE name='%s'" % (category))
		try:
			self.cats[category]=res.first()[0] # cache result
		except:
			self.logger.error("Invalid category: %s" % category)
		return self.cats[category]

	def update(self, data):
		"""
			data is an array with
				md5
				filectime
				version
				filesize
				os
				path
		"""
		if data['version'] == "testing":
			return
		filename = self.escape(data['path'][data['path'].rfind("/")+1:])
		category = "engine_" + data['os']
		version = data['version']
		url = self.prefix +'/' + data['path']
		cid = self.getCID(category)
		#print "%s %s %s %s" % (filename, version, category, url)
		try:
			fid = UpqDB().insert("file", {
				"filename" : filename,
				"name": category,
				"version": version,
				"cid" : cid,
				"md5" : data['md5'],
				"timestamp": datetime.datetime.fromtimestamp(data['filectime']),
				#"timestamp": data['filectime'],
				"size": data['filesize'],
				"status": 1 })
		except UpqDBIntegrityError:
			res = UpqDB().query("SELECT fid from file WHERE name='%s' AND version='%s' AND md5='%s'" % (category, version, data['md5']))
			fid = res.first()[0]
		res = UpqDB().query("SELECT mid from mirror WHERE url_prefix='%s'" % self.prefix)
		mid = res.first()[0]
		relpath = self.escape(url[len(self.prefix)+1:])
		try:
			id = UpqDB().insert("mirror_file", {"mid" : mid, "path": relpath, "status": 1, "fid": fid })
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
		for row in data:
			self.update(row)
		urllib.urlcleanup()
		return True

