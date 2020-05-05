# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Matthias Ableitner (spring #at# abma #dot# de)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# sf-sync: syncs file data with springfiles
# can be either initiaded by an updated file
# or maybe by the xml-rpc interface (or cron?)


from upqdb import UpqDB
import upqconfig

import sys
if sys.version_info[0] >= 3:
	from xmlrpc.client import ServerProxy
else:
	from xmlrpclib import ServerProxy
import logging

import json
import os
import upqjob
import upqdb

class Sf_sync(upqjob.UpqJob):

	def download_and_add_file(self, url):
		from jobs import download
		j = download.Download("download", {"url": url, "subjobs": []})
		j.run()
		from jobs import extract_metadata
		print(j.jobdata)


		j = extract_metadata.Extract_metadata("extract_metadata", j.jobdata)
		return j.run()

	def synctosf(self):
		from jobs import sf_sync
		j = sf_sync.Sf_sync("sf_sync", {})
		return j.run()

	def FixPathes(self):
		from jobs import extract_metadata
		rows = UpqDB().query("select filename, fid, name, version, cid, status from file where filename like '/tmp%%'")
		j = extract_metadata.Extract_metadata("extract_metadata", {})
		for row in rows:
			#print(row)
			srcfile = j.normalizeFilename(row[0], row[1], row[2], row[3])
			subdir = j.jobcfg['maps-path'] if row[4] == 1 else j.jobcfg['games-path']

			status = row[5]
	                #self.movefile(filepath, 1, moveto)

			prefix=j.getPathByStatus(status)
			dstfile=os.path.join(prefix, subdir, os.path.basename(srcfile))
			filename=os.path.basename(srcfile)
			UpqDB().query("UPDATE file SET path='%s', status=%d, filename='%s' WHERE fid=%d" %(subdir, status, filename, row[1]))


	def run(self):
		#username=self.jobcfg['username']
		#password=self.jobcfg['password']
		proxy = ServerProxy(self.jobcfg['rpcurl'])

		
		row = UpqDB().query("SELECT MAX(sid) FROM sf_sync2").first()
		if row:
			lastsid = int(row[0]) if row[0] else 0
		else:
			lastsid = 0
		self.logger.info("Syncing %d" %(lastsid))
		files = proxy.springfiles.getfiles(lastsid)
		for data in files:
			sid = int(data["fid"])
			row = UpqDB().query("SELECT sid FROM sf_sync2 WHERE sid=%d" %(int(sid))).first()
			if row: # file found, nothing to do
				self.logger.debug("File mapping found, continue")
				continue
			
			self.logger.debug("%s %s" %(sid, data))
			row= UpqDB().query("SELECT fid FROM file WHERE md5='%s'" %(data["md5"])).first()
			if row:
				#UpqDB().insert("sf_sync", {"sid": sid, "fid": row["fid"]})
				UpqDB().query("INSERT INTO sf_sync2 (sid, fid) VALUES (%d, %d) "% (sid, row["fid"]))
				self.logger.info("Added mapping: %s <-> %s" %(sid, row["fid"]))
				continue
			if not self.download_and_add_file("https://springfiles.com/" + data["filepath"]):
				self.logger.error("Error adding %s"%(data))
			else:
				row = UpqDB().query("SELECT fid FROM file WHERE md5='%s'" %(data["md5"])).first()
				assert(row)
		self.synctosf()
		return True




handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(module)s.%(funcName)s:%(lineno)d %(message)s"))
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.DEBUG)
logging.info("Started sf_sync")


upqconfig.UpqConfig(configfile="upq2.cfg")
upqconfig.UpqConfig().readConfig()
db = upqdb.UpqDB()
db.connect(upqconfig.UpqConfig().db['url'], upqconfig.UpqConfig().db['debug'])

s = Sf_sync("sf_sync", dict())

#s.FixPathes()

s.run()

