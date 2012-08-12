# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# downloads a file

#from upqjob import UpqJob
#from upqdb import UpqDB
from time import time
import urllib
import os
import shutil
import re

class my_download(urllib.URLopener):
	def http_error_default(self, url, fp, errcode, errmsg, headers):
		raise Exception("Error retrieving %s %d %s" %(url, errcode, errmsg))

class Download():
	"""
		"download url:$url"
	"""
	def check(self):
		if not 'url' in self.jobdata:
			return False
		self.enqueue_job()
		self.msg("Downloading " + self.jobdata['url'])
		return True

	def geturls(self, htmldata):
		res = re.findall("href=\s*(?:\"[^\"]*\"|'[^']'|\S+)", htmldata)
		ret = []
		for r in res:
			url = r[5:].strip("\"'")
			if len(url)>0 and url[0]!='?' and url[0]!='/':
				ret.append(url)
		return ret

	def getversion(self, string):
		ver = string[0].replace("%7b", "{").replace("%7d", "}")
		branch = "master"
		if ver[0] == "{":
			branch = re.findall("{.*}", ver)[0].strip("{}")
			ver = ver[len(branch)+2:]
		return branch, ver

	def run(self):
#		url=self.jobdata['url']
#		self.jobdata['file']=tmpfile
#		self.logger.debug("going to download %s", url)
		dled = {}
		urls = [ "http://springrts.com/dl/buildbot/" ]
		while len(urls)>0:
			cur = urls.pop()
#			print cur
			if not cur.endswith('/'): # file detected
				verstring = re.findall("spring_(.*)_minimal-portable.7z", cur)
				if verstring:
					branch, version = self.getversion(verstring)
					print "branch: " + branch + " version: " + version
					print cur
				verstring = re.findall("[sS]pring_(.*)[_-]MacOSX-.*.zip", cur)
				if verstring:
					branch, version = self.getversion(verstring)
					print "branch: " + branch + " version: " + version
					print cur
				continue
			if cur in dled:
				raise Exception("File was already downloaded! %s" % (cur))
			f = my_download().open(cur)
			dled[cur] = True
			data = f.read()
			files = self.geturls(data)
			for file in files:
				urls.append(cur + file)
		#except Exception as e:
#			self.msg(str(e))
		#	print str(e)
		#	return False
		urllib.urlcleanup()
		return True

dl = Download()
dl.run()
