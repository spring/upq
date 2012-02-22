# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Matthias Ableitner (spring #at# abma #dot# de)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# extracts metadata from a spring map / game and adds it into the db

from upqjob import UpqJob
from upqdb import UpqDB,UpqDBIntegrityError
from upqconfig import UpqConfig

import sys
import os
import ctypes
import Image
import shutil
import getopt
import base64
import tempfile
import gzip
import hashlib
import json
import gc
import StringIO

unitsyncpath=os.path.join(UpqConfig().paths['jobs_dir'],'unitsync')
sys.path.append(unitsyncpath)

import unitsync

class Extract_metadata(UpqJob):

	"""
		setup temporary directory.
		creates <tempdir>/games and symlinks archive file into that directory
	"""
	def setupdir(self, filepath):
		if not os.path.exists(filepath):
			self.msg("error setting up temp dir, file doesn't exist %s" %(filepath))
			raise Exception(self.msgstr)
		temppath=tempfile.mkdtemp(dir=UpqConfig().paths['tmp'])
		archivetmp=os.path.join(temppath, "games")
		os.mkdir(archivetmp)
		self.tmpfile=os.path.join(archivetmp, os.path.basename(filepath))
		self.logger.debug("symlinking %s %s" % (filepath,self.tmpfile))
		os.symlink(filepath,self.tmpfile)
		return temppath

	def savedelete(self,file):
		try:
			os.remove(file)
		except:
			pass
		try:
			os.rmdir(file)
		except:
			pass


	"""
		cleans up temporary directory, removes also files created by unitsync
	"""
	def cleandir(self, temppath):
		self.savedelete(self.tmpfile)
		self.savedelete(os.path.join(temppath,"games"))
		self.savedelete(os.path.join(temppath,"cache","ArchiveCacheV9.lua"))
		self.savedelete(os.path.join(temppath,"cache","ArchiveCache.lua"))
		self.savedelete(os.path.join(temppath,"cache","CACHEDIR.TAG"))
		self.savedelete(os.path.join(temppath,"cache"))
		self.savedelete(os.path.join(temppath,"unitsync.log"))
		self.savedelete(os.path.join(temppath,".springrc"))
		self.savedelete(temppath)
		if os.path.exists(temppath):
			dirList=os.listdir(temppath)
			files=""
			for fname in dirList:
				files+=fname
			self.logger.warn("Didn't clean temp directory %s: %s" % (temppath, files))
	def getMapIdx(self, usync, filename):
		mapcount = usync.GetMapCount()
		for i in range(0, mapcount):
			usync.GetMapArchiveCount(usync.GetMapName(i)) # initialization for GetMapArchiveName()
			mapfilename = os.path.basename(usync.GetMapArchiveName(0))
			if filename==mapfilename:
				return i
		return -1
	def getGameIdx(self, usync, filename):
		gamecount=usync.GetPrimaryModCount()
		for i in range(0, gamecount):
			gamename=usync.GetPrimaryModArchive(i)
			if filename==gamename:
				return i
		return -1
	def escape(self, string):
		string=string.replace("'","''")
#		string=string.replace('"','\"')
		string=string.replace("%", "%%")
		return string

	def decodeString(self, string):
		if string is None:
			return ""
		try:
			string=string.decode('utf-8')
			return self.escape(string)
		except:
			pass
		try:
			string=string.decode('cp850')
			return self.escape(string)
		except:
			self.logger.error("Error decoding string %s" % (string))
			return ""
		return self.escape(string)

	def insertData(self, data, filename):
		metadata=data.copy()
		del metadata['Depends'] #remove redundant entries
		del metadata['sdp']
		del metadata['Version']
		del metadata['Name']
		metadata=json.dumps(metadata)
		if 'fid' in self.jobdata: # detect already existing files
			fid=self.jobdata['fid']
		else:
			results=UpqDB().query("SELECT fid FROM file WHERE sdp='%s'"% (data['sdp']))
			res=results.first()
			if res:
				fid=res['fid']
			else:
				fid=0

		if fid<=0:
			fid=UpqDB().insert("file", {
				"name": self.escape(data['Name']),
				"version": self.escape(data['Version']),
				"sdp": data['sdp'],
				"cid": self.getCid(data['Type']),
				"metadata": metadata,
				"uid": 0,
				"path": "",
				"filename": filename,
				"timestamp": UpqDB().now(), #fixme: use file timestamp
				"size": os.path.getsize(filename),
				"status": 1,
				})
		else:
			UpqDB().query("UPDATE file SET name='%s', version='%s', sdp='%s', cid=%s, metadata='%s' WHERE fid=%s" %(
				self.escape(data['Name']),
				data['Version'],
				data['sdp'],
				self.getCid(data['Type']),
				metadata,
				fid
				))
		# remove already existing depends
		UpqDB().query("DELETE FROM file_depends WHERE fid = %s" % (fid) )
		for depend in data['Depends']:
			res=UpqDB().query("SELECT fid FROM file WHERE CONCAT(name,' ',version)='%s'" % (depend))
			row=res.first()
			if not row:
				id=0
			else:
				id=row['fid']
			try:
				UpqDB().insert("file_depends", {"fid":fid, "depends_string": depend, "depends_fid": id})
				self.msg("Added %s '%s' version '%s' to the mirror-system" % (data['Type'], data['Name'], data['Version']))
			except UpqDBIntegrityError:
				pass
		self.msg("Updated %s '%s' version '%s' sdp '%s' in the mirror-system" % (data['Type'], data['Name'], data['Version'], data['sdp']))
		return fid
	def initUnitSync(self, tmpdir, filename):
		libunitsync=self.jobcfg['unitsync']
		os.environ["SPRING_DATADIR"]=tmpdir
		os.environ["HOME"]=tmpdir
		os.environ["SPRING_LOG_SECTIONS"]="unitsync,ArchiveScanner,VFS"
		usync = unitsync.Unitsync(libunitsync)
		usync.Init(True,1)
		version = usync.GetSpringVersion()
		self.logger.debug("using unitsync version %s" %(version))
		usync.RemoveAllArchives()
		usync.AddArchive(filename)
		usync.AddAllArchives(filename)
		return usync
	def openArchive(self, usync, filename):
		archiveh=usync.OpenArchive(filename)
		if archiveh==0:
			self.logger.error("OpenArchive(%s) failed: %s" % (filename, usync.GetNextError()))
			return False
		return archiveh
	def saveImage(self, image, size):
		""" store a image, called with an Image object, returns the filename """
		m = hashlib.md5()
		m.update(image.tostring())
		if (size[0]>1024): # shrink if to big
			sizey=int((1024.0/size[0])*size[1])
			self.logger.debug("image to big %dx%d, resizing... to %dx%d" % (size[0], size[1], 1024, sizey))
			image=image.resize((1024, sizey))
		else:
			image=image.resize((size[0], size[1]))
		#use md5 as filename, so it can be reused
		filename=m.hexdigest()+".jpg"
		absname=os.path.join(UpqConfig().paths['metadata'], filename)
		image.save(absname)
		os.chmod(absname,int("0644",8))
		self.logger.debug("Wrote " + absname)
		return filename

	def createSplashImages(self, usync, archiveh, filelist):
		res = []
		count=0
		for f in filelist:
			if f.lower().startswith('bitmaps/loadpictures'):
				self.logger.debug("Reading %s" % (f))
				buf=self.getFile(usync, archiveh, f)
				ioobj=StringIO.StringIO()
				ioobj.write(buf)
				ioobj.seek(0)
				del buf
				try:
					im=Image.open(ioobj)
					res.append(self.saveImage(im, im.size))
					count=count+1
				except:
					self.logger.error("Invalid image %s" % (f))
					pass
		return res
	def check(self):
		if 'file' in self.jobdata:
			if not os.path.exists(self.jobdata['file']):
				self.logger.error("File %s doesn't exist" % self.jobdata['file'])
				return False
		elif 'fid' in self.jobdata:
			results=UpqDB().query("SELECT filename, path, status FROM file WHERE fid=%s" % (int(self.jobdata['fid'])))
			res=results.first()
			if not res:
				self.logger.error("Fid not found in db")
				return False
			prefix=self.getPathByStatus(res['status'])
			self.jobdata['file']=os.path.join(prefix, res['path'], res['filename'] )
			if not os.path.exists(self.jobdata['file']):
				self.logger.error("filepath from db doesn't exist %s" %(self.jobdata['file']))
				return False
		else:
			self.logger.error("Either fid or file has to be set")
			return False
		self.enqueue_job()
		return True
	def run(self):
		gc.collect()
		#filename of the archive to be scanned
		filepath=self.jobdata['file']
		filename=os.path.basename(filepath) # filename only (no path info)
		metadatapath=UpqConfig().paths['metadata']

		if not os.path.exists(filepath):
			self.msg("File doesn't exist: %s" %(filepath))
			return False
		tmpdir=self.setupdir(filepath) #temporary directory for unitsync
		usync=self.initUnitSync(tmpdir, filename)
		archiveh=self.openArchive(usync, os.path.join("games",filename))
		filelist=self.getFileList(usync, archiveh)
		try:
			sdp = self.getSDPName(usync, archiveh)
		except:
			self.movefile(filepath, 3, "")
			self.msg("couldn't get sdp hash")
			usync.CloseArchive(archiveh)
			return False
		idx=self.getMapIdx(usync,filename)
		if idx>=0: #file is map
			archivepath=usync.GetArchivePath(filename)+filename
			springname = usync.GetMapName(idx)
			data=self.getMapData(usync, filename, idx, archiveh)
			try:
				data['mapimages']=self.dumpmap(usync, springname, metadatapath, filename,idx)
			except:
				self.movefile(filepath, 3, "")
				usync.CloseArchive(archiveh)
				return False
			moveto=self.jobcfg['maps-path']
		else: # file is a game
			idx=self.getGameIdx(usync,filename)
			if idx<0:
				self.logger.error("Invalid file detected: %s %s %s"% (filename,usync.GetNextError(), idx))
				self.movefile(filepath, 3, "")
				usync.CloseArchive(archiveh)
				return False
			self.logger.debug("Extracting data from "+filename)
			archivepath=usync.GetArchivePath(filename)+filename
			gamearchivecount=usync.GetPrimaryModArchiveCount(idx) # initialization for GetPrimaryModArchiveList()
			data=self.getGameData(usync, idx, gamearchivecount, archivepath, archiveh)
			moveto=self.jobcfg['games-path']
		data['sdp']=sdp
		if (sdp == "") or (data['Name'] == ""): #mark as broken because sdp / name is missing
			self.movefile(filepath, 3, "")
			usync.CloseArchive(archiveh)
			return False
		data['splash']=self.createSplashImages(usync, archiveh, filelist)
		self.jobdata['fid']=self.insertData(data, filepath)
		filepath = self.normalizeFilename(filepath, self.jobdata['fid'], data['Name'], data['Version'])
		self.jobdata['file']=filepath
		self.movefile(filepath, 1, moveto)
		err=usync.GetNextError()
		while not err==None:
			self.logger.error(err)
			err=usync.GetNextError()
		usync.CloseArchive(archiveh)
		usync.UnInit()
		del usync
		if not 'keeptemp' in  self.jobcfg:
			self.cleandir(tmpdir)
		return True

	def getMapPositions(self, usync, idx, Map):
		startpositions = usync.GetMapPosCount(idx)
		res = []
		for i in range(0, startpositions):
			x=usync.GetMapPosX(idx, i)
			z=usync.GetMapPosZ(idx, i)
			res.append({'x': x, 'z': z})
		return res

	def dumpLuaTree(self, usync, depth = 0):
		""" dumps a lua tree into a python dict """
		if depth > 5:
			self.logger.error("max depth reached!")
			return {}
		tables = []
		inttables = []
		res = {}
		# str tables
		count = usync.lpGetStrKeyListCount()
		for i in range(0, count):
			key = usync.lpGetStrKeyListEntry(i)
			typ = usync.lpGetStrKeyType(key)
			if typ == 1: #int
				res[key] = usync.lpGetStrKeyIntVal(key, "")
			elif typ == 2:#string
				res[key] = usync.lpGetStrKeyStrVal(key, "")
			elif typ == 3:#bool
				res[key] = usync.lpGetStrKeyBoolVal(key, "")
			elif typ == 4:#table
				val = "table"
				tables.append(key)
		# int tables
		count = usync.lpGetIntKeyListCount()
		for i in range(0, count):
			key = usync.lpGetIntKeyListEntry(i)
			typ = usync.lpGetIntKeyType(key)
			if typ == 1: #int
				res[key] = usync.lpGetIntKeyIntVal(key, "")
			elif typ == 2:#string
				res[key] = usync.lpGetIntKeyStrVal(key, "")
			elif typ == 3:#bool
				res[key] = usync.lpGetIntKeyBoolVal(key, "")
			elif typ == 4:#table
				val = "table"
				inttables.append(key)
		count = usync.lpGetStrKeyListCount()
		for table in tables:
			usync.lpSubTableStr(table)
			res[table] = self.dumpLuaTree(usync, depth + 1)
			usync.lpPopTable()
		count = usync.lpGetIntKeyListCount()
		for table in inttables:
			usync.lpSubTableInt(table)
			res[table] = self.dumpLuaTree(usync, depth + 1)
			usync.lpPopTable()
		return res

	def luaToPy(self, usync, archiveh, filename):
		""" laods filename from archiveh, parses it and returns lua-tables as dict """
		try:
			luafile = self.getFile(usync, archiveh, filename)
		except:
			self.logger.error("file doesn't exist in archive: %s" %(filename))
			return {}
		usync.lpOpenSource(luafile, "r")
		usync.lpExecute()
		res = self.dumpLuaTree(usync)
		err = usync.lpErrorLog()
		if err:
			self.logger.error(err)
		return res

	def getDepends(self, usync, archiveh, filename):
		filterdeps = [ 'bitmaps.sdz', 'springcontent.sdz', 'maphelper.sdz', 'cursors.sdz', 'Map Helper v1' ]
		res = self.luaToPy(usync, archiveh, filename)
		if 'depend' in res:
			vals = []
			for i in res['depend'].values():
				if i not in filterdeps:
					vals.append(i)
			self.logger.error(vals)
			return vals
		return []

	def getMapResources(self, usync,idx,Map):
		res=[]
		resourceCount=usync.GetMapResourceCount(idx)
		for i in range (0, resourceCount):
			res.append({"Name": usync.GetMapResourceName(idx, i),
				"Max": usync.GetMapResourceMax(idx, i),
				"ExtractorRadius": usync.GetMapResourceExtractorRadius(idx, i)})
		return res

	# extracts minimap from given file
	def createMapImage(self, usync, mapname, size):
		data=ctypes.string_at(usync.GetMinimap(mapname, 0), 1024*1024*2)
		im = Image.frombuffer("RGB", (1024, 1024), data, "raw", "BGR;16")
		del data
		return self.saveImage(im, size)

	def createMapInfoImage(self, usync, mapname, maptype, byteperpx, decoder,decoderparm, size):
		width = ctypes.pointer(ctypes.c_int())
		height = ctypes.pointer(ctypes.c_int())
		usync.GetInfoMapSize(mapname, maptype, width, height)
		width = width.contents.value
		height = height.contents.value
		data = ctypes.create_string_buffer(int(width*height*byteperpx*2))
		data.restype = ctypes.c_void_p
		ret=usync.GetInfoMap(mapname, maptype, data, byteperpx)
		if (ret<>0):
			im = Image.frombuffer(decoder, (width, height), data, "raw", decoderparm)
			im=im.convert("L")
			res=self.saveImage(im, size)
			del data
			return res
		del data
		self.msg("Error creating image %s" % (usync.usync.GetNextError()))
		raise Exception("Error creating image")

	def dumpmap(self, usync, springname, outpath, filename, idx):
		mapwidth=float(usync.GetMapWidth(idx))
		mapheight=float(usync.GetMapHeight(idx))
		if mapwidth>mapheight:
			scaledsize=(1024, int(((mapheight/mapwidth) * 1024)))
		else:
			scaledsize=(int(((mapwidth/mapheight) * 1024)), 1024)
		res = []
		res.append(self.createMapImage(usync,springname, scaledsize))
		res.append(self.createMapInfoImage(usync,springname, "height",2, "RGB","BGR;15", scaledsize))
		res.append(self.createMapInfoImage(usync,springname, "metal",1, "L","L;I", scaledsize))
		return res

	def getUnits(self, usync, archive):
		while usync.ProcessUnits()>0:
			err=usync.GetNextError()
			if err:
				self.logger.error("Error processing units: %s" % (err));
		res = []
		count=usync.GetUnitCount()
		for i in range(0, count):
			res.append({ "UnitName": self.decodeString(usync.GetUnitName(i)),
				"FullUnitName": self.decodeString(usync.GetFullUnitName(i))})
		return res
	def getFileList(self, usync, archiveh):
		""" returns a list of all files in an archive """
		files = []
		pos=0
		#get a list of all files
		while True:
			name=ctypes.create_string_buffer(1024)
			size=ctypes.c_int(1024)
			res=usync.FindFilesArchive(archiveh, pos, name, ctypes.byref(size))
			if res==0: #last file
				break
			fileh=usync.OpenArchiveFile(archiveh, name.value)
			if fileh<0:
				self.logger.error("Invalid handle for '%s' '%s': %s" % (name.value, fileh,  ""+usync.GetNextError()))
				return []
			files.append(name.value)
			del name
			pos=pos+1
		return files
	def getFile(self, usync, archivehandle, filename):
		""" returns the content of an archive"""
		fileh=usync.OpenArchiveFile(archivehandle, filename)
		if (fileh<0):
			self.logger.error("Couldn't open %s" %(filename))
			raise Exception("Couldn't open %s" %(filename))
		size=usync.SizeArchiveFile(archivehandle, fileh)
		if (size<0):
			self.logger.error("Error getting size of %s" % (filename))
			raise Exception("Error getting size of %s" % (filename))
		buf = ctypes.create_string_buffer(size)
		bytes=usync.ReadArchiveFile(archivehandle, fileh, buf, size)
		usync.CloseArchiveFile(archivehandle, fileh)
		return ctypes.string_at(buf,size)

	def getSDPName(self, usync, archiveh):
		files=self.getFileList(usync, archiveh)
		m=hashlib.md5()
		files.sort(cmp = lambda a, b: cmp(a.lower(), b.lower()))
		if len(files)<=0:
			raise Exception("Zero files found!")
		i=0
		for f in files:
			# ignore directory entries
			if f[-1] == '/': continue
			try:
				content = self.getFile(usync, archiveh, f)
			except:
				return ""
			m.update(hashlib.md5(f.lower()).digest())
			m.update(hashlib.md5(content).digest())
			del content
			i=i+1
		self.logger.debug("SDP %s" % m.hexdigest())
		return m.hexdigest()
	""" returns the category id specified by name"""
	def getCid(self, name):
		result=UpqDB().query("SELECT cid from categories WHERE name='%s'" % name)
		res=result.first()
		if res:
			cid=res['cid']
		else:
			cid=UpqDB().insert("categories", {"name": name})
		return cid

	def getGameData(self, usync, idx, gamesarchivecount, archivename, archiveh):
		res={}
		springname=usync.GetPrimaryModName(idx)
		version=usync.GetPrimaryModVersion(idx)
		if version==springname:
			version=""
		elif springname.endswith(version) : # Hack to get version independant string
			springname=springname[:len(springname)-len(version)]
			if springname.endswith(" ") : #remove space at end (added through unitsync hack)
				springname=springname[:len(springname)-1]

		res['Type']= "Game"
		res['Name']= springname
		res['Description']= self.decodeString(usync.GetPrimaryModDescription(idx))
		res['Version']= version
		res['Depends']=self.getDepends(usync, archiveh, "modinfo.lua")
		res['Units']=self.getUnits(usync, archivename)
		return res

	def getMapData(self, usync, filename, idx, archiveh):
		res={}
		res['Type'] = "Map"
		mapname=usync.GetMapName(idx)
		res['Name'] = mapname

		res['Author'] = usync.GetMapAuthor(idx)
		res['Description'] = self.decodeString(usync.GetMapDescription(idx))
		res['Gravity'] = usync.GetMapGravity(idx)
		res['MaxWind'] = usync.GetMapWindMax(idx)
		res['MinWind'] = usync.GetMapWindMin(idx)
		res['TidalStrength'] = usync.GetMapTidalStrength(idx)

		res['Height'] = usync.GetMapHeight(idx) / 512
		res['Width'] = usync.GetMapWidth(idx) / 512

		res['Gravity'] = usync.GetMapGravity(idx)
		res['MapFileName'] = usync.GetMapFileName(idx)
		res['MapMinHeight'] = usync.GetMapMinHeight(mapname)
		res['MapMaxHeight'] = usync.GetMapMaxHeight(mapname)

		res['Resources'] = self.getMapResources(usync, idx,filename)
		res['Units'] = self.getUnits(usync, filename)

		res['StartPos']=self.getMapPositions(usync,idx,filename)
		res['Depends']=self.getDepends(usync, archiveh, "mapinfo.lua")
		version="" #TODO: add support
		res['Version']=version
		return res

	def getPathByStatus(self, status):
		if status==1:
			return UpqConfig().paths['files']
		elif status==3:
			return UpqConfig().paths['broken']
		raise Exception("Unknown status %s" %(status))

	def movefile(self, srcfile, status, subdir):
		prefix=self.getPathByStatus(status)
		dstfile=os.path.join(prefix, subdir, os.path.basename(srcfile))
		filename=os.path.basename(srcfile)
		if 'fid' in self.jobdata:
			fid=int(self.jobdata['fid'])
		else:
			fid=0
		if srcfile!=dstfile:
			if os.path.exists(dstfile):
				self.msg("Destination file already exists: dst: %s src: %s" %(dstfile, srcfile))
				return False
			try:
				shutil.move(srcfile, dstfile)
			except: #move failed, try to copy + delete
				shutil.copy(srcfile, dstfile)
				try:
					os.remove(srcfile)
				except:
					self.log.warn("Removing src file failed: %s" % (srcfile))
			if fid>0:
				UpqDB().query("UPDATE file SET path='%s', status=%d, filename='%s' WHERE fid=%s" %(subdir, status, filename, int(fid)))
			self.logger.debug("moved file to (abs)%s %s:(rel)%s" %(srcfile, prefix,subdir))
		elif filename!=srcfile: #file is already in the destination dir, make filename relative
			UpqDB().query("UPDATE file SET path='%s', status=%d, filename='%s' WHERE fid=%d" %(subdir, status, filename, fid))
		try:
			os.chmod(dstfile, int("0444",8))
		except OSError:
			pass
		self.logger.info("moved file to %s" % (dstfile))
		return True
	def normalizeFilename(self, srcfile, fid, name, version):
		""" normalize filename + renames file + updates filename in database """
		name=name.lower()
		if len(version)>0:
			name = str(name[:200] +"-" + version.lower())[:255]
		_, extension = os.path.splitext(srcfile)
		name += extension

		res=""
		for c in name:
			if c in "abcdefghijklmnopqrstuvwxyz-_.01234567890":
				res+=c
			else:
				res+="_"
		dstfile=os.path.join(os.path.dirname(srcfile), res)
		if srcfile!=dstfile:
			results=UpqDB().query("SELECT fid FROM file WHERE BINARY filename='%s' AND status=1" % (res))
			row=results.first()
			if row or os.path.exists(dstfile):
				self.logger.error("Error renaming file: %s to %s already exists, deleting source + using dst!" % (srcfile, dstfile))
				os.remove(srcfile)
			else:
				shutil.move(srcfile, dstfile)
			
			UpqDB().query("UPDATE file SET filename='%s' WHERE fid=%s" %(res, fid))
			self.logger.info("Normalized filename to %s "%(dstfile))
		return dstfile

