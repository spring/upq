# -*- coding: utf-8 -*-
# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Matthias Ableitner (spring #at# abma #dot# de)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# sets tags for already known files taken from the file list of the "rapid"
# download system

import gzip
import urlparse
import requests
import os.path
import datetime
import time

from upqjob import UpqJob
from upqdb import UpqDB, UpqDBIntegrityError

class Rapidsync(UpqJob):
	cats = {}

	def UpdateSDP(self, sdp):
		"""
		values = {
				"tag"=sdp[0],
				"md5"=sdp[1],
				"depends"=sdp[2],
				"name"=sdp[3],
		}
		"""
		#check if file is already known
		res=UpqDB().query("SELECT f.fid FROM file f \
			LEFT JOIN tag t ON t.fid=f.fid \
			WHERE sdp='%s'" % (sdp[1]))
		row=res.first()
		if row: #file is already known
			#delete tag from existing files
			UpqDB().query("DELETE FROM tag WHERE tag='%s'" % (sdp[0]))
			#insert updated tag
			UpqDB().query("INSERT INTO tag (fid, tag) VALUES (%s, '%s')" % (row['fid'], sdp[0]))
			#self.logger.info("updated %s %s %s %s",sdp[3],sdp[2],sdp[1],sdp[0])
		else:
			if not sdp[3]: #without a name, we can't do anything!
				continue
			cid = self.getCid("game")
			try:
				fid = UpqDB().insert("file", {
					"filename" : sdp[3] + " (not available as sdz)",
					"name": sdp[3],
					"cid" : cid,
					"md5" : sdp[1],
					"sdp" : sdp[1],
					"size" : 0,
					"status" : 4, # special status for files that can only be downloaded via rapid
					"uid" : 0,
					"path" : "",
					})
				UpqDB().query("INSERT INTO tag (fid, tag) VALUES (%s, '%s')" % (fid, sdp[0]))
				#self.logger.info("inserted %s %s %s %s",sdp[3],sdp[2],sdp[1],sdp[0])
			except Exception as e:
				self.logger.error(str(e))
				self.logger.error("Error from sdp: %s %s %s %s", sdp[3], sdp[2],sdp[1],sdp[0])
				res=UpqDB().query("SELECT * FROM file f WHERE name='%s'" % sdp[3])
				if res:
					row=res.first()
					self.logger.error("a file with this name already exists, fid=%s, sdp=%s" % (row['fid'], row['sdp']))

	def run(self):
		repos=self.fetchListing(self.getcfg('mainrepo', "http://repos.springrts.com/repos.gz"), False)
		i=0
		for repo in repos:
			sdps=self.fetchListing(repo[1] + "/versions.gz")
			for sdp in sdps:
				self.UpdateSDP(sdp)

	def httpdate(self, dt):
		"""Return a string representation of a date according to RFC 1123
		(HTTP/1.1).

		The supplied date must be in UTC.

		"""
		weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
		month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
		     "Oct", "Nov", "Dec"][dt.month - 1]
		return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, dt.day, month,	dt.year, dt.hour, dt.minute, dt.second)


	def fetchListing(self, url, cache=True):
		self.logger.debug("Fetching %s" % (url))
		ParseResult=urlparse.urlparse(url)
		absname=os.path.join(self.getcfg('temppath', '/tmp'), ParseResult.hostname, ParseResult.path.strip("/"))
		dirname = os.path.dirname(absname)
		if not os.path.exists(dirname):
			os.makedirs(dirname)

		headers = {}
		if cache and os.path.isfile(absname):
			file_time = datetime.datetime.fromtimestamp(os.path.getmtime(absname))
			headers["If-Modified-Since"] = self.httpdate(file_time)

		r = requests.get(url, timeout=10, headers=headers)
		if r.status_code == 304:
			self.logger.debug("Not modified")
			return []
		with open(absname, "w") as f:
			f.write(r.content)
		url_date = datetime.datetime.strptime(r.headers["last-modified"], '%a, %d %b %Y %H:%M:%S GMT')
		ts = int((time.mktime(url_date.timetuple()) + url_date.microsecond/1000000.0))
		os.utime(absname, (ts, ts))
		gz = gzip.open(absname)
		lines=gz.readlines()
		gz.close()
		res=[]
		for line in lines:
			res.append(line.strip("\n").split(","))
		return res

	def getCid(self, name):
		if name in self.cats:
			return self.cats[name]
		result=UpqDB().query("SELECT cid from categories WHERE name='%s'" % name)
		res=result.first()
		if res:
			cid=res['cid']
		else:
			cid=UpqDB().insert("categories", {"name": name})
		self.cats[name] = cid
		return cid
