# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2012 Matthias Ableitner (spring #at# abma #dot# de)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# fetches version information from http://springrts.com/dl/buildbot

from upqjob import UpqJob
from upqdb import UpqDB
from time import time
import urllib
import os
import shutil
import re
import socket

class my_download(urllib.URLopener):
	def http_error_default(self, url, fp, errcode, errmsg, headers):
		raise Exception("Error retrieving %s %d %s" %(url, errcode, errmsg))

class Versionfetch(UpqJob):
	prefix = "http://springrts.com/dl/buildbot"
	lobby = "lobby.springrts.com"
	lobbyport = 8200
	cats = {}
	def geturls(self, htmldata):
		""" returns an array of urls found in htmldata """
		res = re.findall("href=\s*(?:\"[^\"]*\"|'[^']'|\S+)", htmldata)
		ret = []
		for r in res:
			url = r[5:].strip("\"'")
			if len(url)>0 and url[0]!='?' and url[0]!='/':
				ret.append(url)
		return ret

	def getversion(self, string):
		""" returns branch, version of given string """
		ver = string[0].replace("%7b", "{").replace("%7d", "}")
		branch = "master"
		if ver[0] == "{":
			branch = re.findall("{.*}", ver)[0].strip("{}")
			ver = ver[len(branch)+2:]
		return branch, ver
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

	def update(self, category, versionregex, url):
		version = re.findall(versionregex, url)
		if not version:
			return
		version = self.escape(version[0])
		filename = self.escape(url[url.rfind("/")+1:])
		category = "engine_" + category
		cid = self.getCID(category)
		print "%s %s %s %s" % (filename, version, category, url)
		fid = UpqDB().insert("file", {"filename" : filename, "name":"spring", "version": version, "category" : cid  })
		res = UpqDB().query("SELECT mid from mirror WHERE url_prefix='%s'" % self.prefix)
		mid = res.first()[0]
		relpath = self.escape(url[len(self.prefix):]) 
		UpqDB().insert("mirror_file", {"mid" : mid, "path": relpath, "status": 1 })

	def run(self):
		dled = {}
		urls = [ self.prefix + '/' ]
		print self.getlobbyversion()
		while len(urls)>0:
			cur = urls.pop()
			if not cur.endswith('/'): # file detected
				self.update("windows", "spring_(.*)_minimal-portable.7z", cur)
				self.update("macosx", "[sS]pring_(.*)[_-]MacOSX-.*.zip", cur)
				self.update("linux", "spring_(.*)_minimal-portable-linux-static.7z", cur)
				continue
			if cur in dled:
				raise Exception("File was already downloaded! %s" % (cur))
			f = my_download().open(cur)
			dled[cur] = True
			data = f.read()
			files = self.geturls(data)
			for file in files:
				urls.append(cur + file)
		urllib.urlcleanup()
		return True

