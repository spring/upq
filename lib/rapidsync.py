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
import logging

from lib import download, upqdb

def UpdateSDP(db, sdp):
	"""
	values = {
			"tag"=sdp[0],
			"md5"=sdp[1],
			"depends"=sdp[2],
			"name"=sdp[3],
	}
	"""
	#check if file is already known
	res=db.query("SELECT f.fid FROM file f \
		LEFT JOIN tag t ON t.fid=f.fid \
		WHERE sdp='%s'" % (sdp[1]))
	row=res.first()
	if row: #file is already known
		#delete tag from existing files
		db.query("DELETE FROM tag WHERE tag='%s'" % (sdp[0]))
		#insert updated tag
		db.query("INSERT INTO tag (fid, tag) VALUES (%s, '%s')" % (row['fid'], sdp[0]))
		#logging.info("updated %s %s %s %s",sdp[3],sdp[2],sdp[1],sdp[0])
		return
	if not sdp[3]: #without a name, we can't do anything!
		return
	cid = upqdb.getCID(db, "game")
	try:
		fid = db.insert("file", {
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
		db.query("INSERT INTO tag (fid, tag) VALUES (%s, '%s')" % (fid, sdp[0]))
		#logging.info("inserted %s %s %s %s",sdp[3],sdp[2],sdp[1],sdp[0])
	except Exception as e:
		logging.error(str(e))
		logging.error("Error from sdp: %s %s %s %s", sdp[3], sdp[2],sdp[1],sdp[0])
		res = db.query("SELECT * FROM file f WHERE name='%s'" % sdp[3])
		if res:
			row=res.first()
			logging.error("a file with this name already exists, fid=%s, sdp=%s" % (row['fid'], row['sdp']))

def fetchListing(cfg, url, cache=True):
	logging.debug("Fetching %s" % (url))
	ParseResult = urlparse(url)
	absname=os.path.join(cfg.paths['tmp'], ParseResult.hostname, ParseResult.path.strip("/"))

	if not download.DownloadFile(url, absname, cache):
		return []

	gz = gzip.open(absname)
	lines=gz.readlines()
	gz.close()
	res=[]
	for line in lines:
		res.append(line.decode("utf-8").strip("\n").split(","))
	return res

def Rapidsync(cfg, db):
	repos = fetchListing(cfg, "https://repos.springrts.com/repos.gz", False)
	for repo in repos:
		sdps = fetchListing(cfg, repo[1] + "/versions.gz")
		for sdp in sdps:
			self.UpdateSDP(db, sdp)



