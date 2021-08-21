# -*- coding: utf-8 -*-
# This file is part of the "upq" program used on springfiles.springrts.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Matthias Ableitner (spring #at# abma #dot# de)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# sets tags for already known files taken from the file list of the "rapid"
# download system

import gzip
from urllib.parse import urlparse
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
			return
		if not sdp[3]: #without a name, we can't do anything!
			return
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
		for repo in repos:
			sdps=self.fetchListing(repo[1] + "/versions.gz")
			for sdp in sdps:
				self.UpdateSDP(sdp)


	def fetchListing(self, url, cache=True):
		self.logger.debug("Fetching %s" % (url))
		ParseResult = urlparse(url)
		absname=os.path.join(self.getcfg('temppath', '/tmp'), ParseResult.hostname, ParseResult.path.strip("/"))

		if not self.DownloadFile(url, absname, cache):
			return []

		gz = gzip.open(absname)
		lines=gz.readlines()
		gz.close()
		res=[]
		for line in lines:
			res.append(line.decode("utf-8").strip("\n").split(","))
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
