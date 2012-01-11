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


from upqjob import UpqJob
from upqdb import UpqDB
from upqconfig import UpqConfig
from xmlrpclib import ServerProxy

import json
import os

class Sf_sync(UpqJob):
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
			self.msg("xmlrpc  springfiles.sync() error: %s" %(e))
			return False
		self.logger.debug("received from springfiles: %s", rpcres)
		return True

	def run(self):
		if self.jobdata.has_key('fid'): #fid set, add change to db
			fid=int(self.jobdata['fid'])
			command=0 #default to update command
			if self.jobdata.has_key('command'):
				command=self.jobdata['command']
				if command=="update":
					command=0
				elif command=="delete":
					command=1
				else: #unknown command
					self.logger.error("Invalid command: %s, only update or delete are valid"% (command))
					return False
			self.updatefile(fid, command)

		username=self.jobcfg['username']
		password=self.jobcfg['password']
		proxy = ServerProxy(self.jobcfg['rpcurl'])
		if self.jobdata.has_key('sid'): #sid set, update to springfiles requested
			sid=int(self.jobdata['sid'])
		else: #sid not set, request from springfiles
			try:
				sid=int(proxy.springfiles.getlastsyncid(username, password))
				self.logger.debug("Fetched sid from springfiles: %d" % (sid));
			except Exception as e:
				self.msg("xmlrpc springfiles.getlastsyncid() error: %s"%(e))
				return False
		if sid>0:
			results=UpqDB().query("SELECT fid, command FROM sf_sync WHERE sid>%d ORDER BY sid " %(sid)) #get all changes from db
		else:
			results=UpqDB().query("SELECT fid FROM file WHERE status=1 ORDER BY fid") #full sync, get all fids
			self.logger.debug("springfiles returned %d, doing full sync" % (sid))
		lastfid=-1
		lastcmd=-1
		requests = []
		maxsid=UpqDB().query("SELECT MAX(sid) as sid FROM sf_sync").first()['sid']
		for res in results: #fixme: use yield
			data = {}

			if sid==0: #full sync, all commands are update
				data['command']="update"
				data['metadata']=self.getmetadata(res['fid'])
			else:
				if lastfid==res['fid'] and lastcmd==res['command']: #skip if the same command was already done before
					continue
				lastfid=res['fid']
				lastcmd=data['command']
				if res['command']==1: # delete
					data['command']="delete"
				elif res['command']==0: # update
					data['metadata']=self.getmetadata(res['fid'])
					data['command']="update"
				else:
					self.logger.error("unknown command %d for fid %d", res['command'], res['fid'])
					continue

			self.logger.debug("adding sid %d to requests" % (res['fid']))
			data['fid']=res['fid']
			data['sid']=maxsid
			requests.append(data)
			if len(requests)>int(self.jobcfg['maxrequests']): #more then maxrequests queued, flush them
				self.logger.debug("flushing %d requests" % (len(requests)))
				if not self.rpc_call_sync(proxy, username, password, requests):
					return False
				requests = []
		if len(requests)>0: #update remaining requests
			 return self.rpc_call_sync(proxy, username, password, requests)
		return True
