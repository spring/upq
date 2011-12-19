# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#called with fileid, extracts/inserts metadata
#calls upload

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
			self.logger.warn("Didn't clean temp directory %s: %s" % (temppath, files));
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

	def insertData(self, data, filename):
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
		metadata=data.copy()
		del metadata['Depends'] #remove redundant entries
		del metadata['sdp']
		del metadata['Version']
		del metadata['Name']
		try:
			metadata=json.dumps(metadata)
			metadata=metadata.replace("'","\\'")
			metadata=metadata.replace('"','\\"')
			metadata=metadata.replace("%", "%%")
		except:	
			metadata=""
			self.msg("error encoding metadata")
			pass
		res=UpqDB().query("SELECT fid FROM file WHERE sdp='%s'" % (data['sdp']))
		row=res.first()
		if not row:
			fid=UpqDB().insert("file", {
				"name": data['Name'],
				"version": data['Version'],
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
			fid=row['fid']
			UpqDB().query("UPDATE file SET name='%s', version='%s', sdp='%s', cid=%s, metadata='%s' WHERE fid=%s" %(
				data['Name'],
				data['Version'],
				data['sdp'],
				self.getCid(data['Type']),
				metadata,
				fid
				))
		self.msg("Updated %s '%s' version '%s' in the mirror-system" % (data['Type'], data['Name'], data['Version']))
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
                        self.logger.error("OpenArchive(%s) failed" % filename)
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
		self.logger.info("Wrote " + absname)
		return filename

	def createSplashImages(self, usync, archiveh, filelist):
		res = []
		count=0
		for f in filelist:
			if f.lower().startswith('bitmaps/loadpictures'):
				self.logger.info("Reading %s" % (f))
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
		sdp = self.getSDPName(usync, archiveh)

		idx=self.getMapIdx(usync,filename)
		if idx>=0: #file is map
			archivepath=usync.GetArchivePath(filename)+filename
			springname = usync.GetMapName(idx)
			data=self.getMapData(usync, filename, idx)
			data['mapimages']=self.dumpmap(usync, springname, metadatapath, filename,idx)
			moveto=self.jobcfg['maps-path']
		else: # file is a game
			idx=self.getGameIdx(usync,filename)
			if idx<0:
				self.logger.error("Invalid file detected: %s %s %s"% (filename,usync.GetNextError(), idx))
				self.append_job("movefile", { "status": 3 }) #mark file as broken
				return False
			self.logger.debug("Extracting data from "+filename)
			archivepath=usync.GetArchivePath(filename)+filename
			gamearchivecount=usync.GetPrimaryModArchiveCount(idx) # initialization for GetPrimaryModArchiveList()
			data=self.getGameData(usync, idx, gamearchivecount, archivepath)
			moveto=self.jobcfg['games-path']
		data['sdp']=sdp
		data['splash']=self.createSplashImages(usync, archiveh, filelist)
		self.jobdata['fid']=self.insertData(data, filepath)
		self.append_job("movefile", {"subdir": moveto})
		err=usync.GetNextError()
		while not err==None:
			self.logger.error(err)
			err=usync.GetNextError()
		usync.UnInit()
		del usync
		if not self.jobcfg.has_key('keeptemp'):
			self.cleandir(tmpdir)
		return True

	springcontent = [ 'bitmaps.sdz', 'springcontent.sdz', 'maphelper.sdz', 'cursors.sdz' ]
	def getMapPositions(self, usync, idx, Map):
		startpositions = usync.GetMapPosCount(idx)
		res = []
		for i in range(0, startpositions):
			x=usync.GetMapPosX(idx, i)
			z=usync.GetMapPosZ(idx, i)
			res.append({'x': x, 'z': z})
		return res

	def getMapDepends(self, usync,Map):
		res=[]
		count=usync.GetMapArchiveCount(Map)
		for i in range (1, count): # get depends for file, idx=0 is filename itself
			deps=os.path.basename(usync.GetMapArchiveName(i))
			if not deps in self.springcontent:
				res.append(deps)
		return res
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

	def getGameDepends(self, usync, idx, gamearchivecount, game):
		res=[]
		for i in range (1, gamearchivecount): # get depends for file, idx=0 is filename itself
			deps=os.path.basename(usync.GetPrimaryModArchiveList(i))
			if not deps in self.springcontent:
				res.append(depend)
		return res

	def getUnits(self, usync, archive):
		while usync.ProcessUnits()>0:
			err=usync.GetNextError()
			if err:
				self.logger.error("Error processing units: %s" % (err));
		res = []
		count=usync.GetUnitCount()
		for i in range(0, count):
			res.append({ "UnitName": usync.GetUnitName(i),
				"FullUnitName": usync.GetFullUnitName(i)})
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
                                break
                        files.append(name.value)
			del name
                        pos=pos+1
		return files
	def getFile(self, usync, archivehandle, filename):
		""" returns the content of an archive"""
		fileh=usync.OpenArchiveFile(archivehandle, filename)
		size=usync.SizeArchiveFile(archivehandle, fileh)
		buf = ctypes.create_string_buffer(size)
		bytes=usync.ReadArchiveFile(archivehandle, fileh, buf, size)
		usync.CloseArchiveFile(archivehandle, fileh)
		return ctypes.string_at(buf,size)

	def getSDPName(self, usync, archiveh):
		files=self.getFileList(usync, archiveh)
		m=hashlib.md5()
		files.sort(cmp = lambda a, b: cmp(a.lower(), b.lower()))
		if len(files)<=0:
			self.logger.error("Zero files found!")
		i=0
		for f in files:
			# ignore directory entries
			if f[-1] == '/': continue
			content = self.getFile(usync, archiveh, f)
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

	def getGameData(self, usync, idx, gamesarchivecount, archivename):
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
		res['Description']= usync.GetPrimaryModDescription(idx)
		res['Version']= version
		res['Depends']=self.getGameDepends(usync, idx, gamesarchivecount, archivename)
		res['Units']=self.getUnits(usync, archivename)
		return res

	def getMapData(self, usync, filename, idx):
		res={}
		res['Type'] = "Map"
		mapname=usync.GetMapName(idx)
		res['Name'] = mapname

		res['Author'] = usync.GetMapAuthor(idx)
		res['Description'] = usync.GetMapDescription(idx)
		res['Gravity'] = usync.GetMapGravity(idx)
		res['MaxWind'] = usync.GetMapWindMax(idx)
		res['MinWind'] = usync.GetMapWindMin(idx)
		res['TidalStrength'] = usync.GetMapTidalStrength(idx)

		res['Height'] = usync.GetMapHeight(idx)
		res['Width'] = usync.GetMapWidth(idx)

		res['Gravity'] = usync.GetMapGravity(idx)
		res['MapFileName'] = usync.GetMapFileName(idx)
		res['MapMinHeight'] = usync.GetMapMinHeight(mapname)
		res['MapMaxHeight'] = usync.GetMapMaxHeight(mapname)

		res['Resources'] = self.getMapResources(usync, idx,filename)
		res['Units'] = self.getUnits(usync, filename)

		res['StartPos']=self.getMapPositions(usync,idx,filename)
		res['Depends']=self.getMapDepends(usync,filename)
		version="" #TODO: add support
		res['Version']=version
		return res

