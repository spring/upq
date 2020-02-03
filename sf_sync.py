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
from xmlrpc.client import ServerProxy
import logging

import json
import os
import upqjob
import upqdb

class Sf_sync(upqjob.UpqJob):
	"""
		no params required, if
			sid>=0:
				sync, starting from this id
			sid<0:
				full sync

			fid>=0:
				file was changed, requires
			command=update|delete
				to be set
	"""
	def check(self):
		self.enqueue_job()
		return True

	def updatefile(self, fid, command):
		UpqDB().insert("sf_sync", {'fid': fid, 'command': command})

	def getmetadata(self, fid):
		"""
			returns the metadata, that is required for springfiles in a struct
			required data:
				link to images
				mirror urls
				file size
				md5
		"""
		data={}
		data['mirror']=[]
		results=UpqDB().query("SELECT CONCAT(m.url_prefix, f.path) as url FROM mirror_file f LEFT JOIN mirror m ON f.mid=m.mid WHERE f.fid=%d" % (fid))
		for res in results:
			data['mirror'].append(res['url'])
		results=UpqDB().query("SELECT f.filename, f.size, f.timestamp, f.md5, f.name, f.version, c.name as category, f.metadata FROM file f LEFT JOIN categories c ON f.cid=c.cid WHERE f.fid=%d" %(fid))
		res=results.first()
		for value in ["filename", "size", "timestamp", "md5", "name", "version", "category"]:
			data[value]=res[value]
		if res['metadata']!=None and len(res['metadata'])>0:
			data['metadata']=json.loads(res['metadata'])
		else:
			data['metadata']=[]
		return data


	def rpc_call_sync(self, proxy, username, password, data):
		"""
			make the xml-rpc call
		"""
		try:
			rpcres=proxy.springfiles.sync(username, password, data)
			for rpc in rpcres: #set description url received from springfiles
				UpqDB().query("UPDATE file SET descriptionuri='%s' WHERE fid=%d" % (rpc['url'], rpc['fid']))
		except Exception as e:
			self.msg("xmlrpc springfiles.sync() error: %s" %(e))
			return True # fixme
		self.logger.debug("received from springfiles: %s", rpcres)
		return True

	def download_and_add_file(url):
		from . import extract_metadata


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
				self.logger.debug("Added mapping: %s <-> %s" %(sid, row["fid"]))
				continue
			assert(False)


		return True

logging.getLogger().addHandler(logging.StreamHandler())
logging.getLogger().setLevel(logging.DEBUG)
logging.info("Started sf_sync")
upqconfig.UpqConfig(configfile="upq.cfg")
upqconfig.UpqConfig().readConfig()
db = upqdb.UpqDB()
db.connect(upqconfig.UpqConfig().db['url'], upqconfig.UpqConfig().db['debug'])

s = Sf_sync("sf_sync", dict())


s.run()

