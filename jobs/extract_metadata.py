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
	def check(self):
		if self.jobdata['fid']<=0:
			self.msg("no id specified")
			return False

		results=UpqDB().query("SELECT * FROM file WHERE fid=%d AND status=1" % int(self.jobdata['fid']))
		res=results.first()
		if res == None:
			self.msg("fid not found")
			return False
		id=self.enqueue_job()
		return True
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

	def insertData(self, data, fid):
		for depend in data['Depends']:
			res=UpqDB().query("SELECT fid FROM files WHERE CONCAT(name,' ',version)='%s'" % (depend))
			row=res.first()
			if not row:
				id=0
			else:
				id=row['fid']
			try:
				UpqDB().insert("file_depends", {"fid":fid, "depends_string": depend, "depends_fid": id})
			except UpqDBIntegrityError:
				pass
		UpqDB().query("UPDATE file SET name='%s', version='%s', sdp='%s', cid=%s WHERE fid=%s" %(
				data['Name'],
				data['Version'],
				data['sdp'],
				self.getCid(data['Type']),
				fid
			))

	def run(self):
		fid=int(self.jobdata['fid'])
		results=UpqDB().query("SELECT * FROM file WHERE fid=%d" % fid)
		res=results.first()
		#filename of the archive to be scanned
		filename=res['filename'] # filename only (no path info)
		filepath=os.path.join(UpqConfig().paths['files'], res['path'], res['filename']) # absolute filename
		libunitsync=self.jobcfg['unitsync']
		metadatapath=UpqConfig().paths['metadata']

		if not os.path.exists(filepath):
			self.msg("File doesn't exist: %s" %(filepath))
			return False
		tmpdir=self.setupdir(filepath) #temporary directory for unitsync

		os.environ["SPRING_DATADIR"]=tmpdir
		os.environ["HOME"]=tmpdir
		usync = unitsync.Unitsync(libunitsync)
		usync.Init(True,1)
		version = usync.GetSpringVersion();
		self.logger.debug("using unitsync version %s" %(version))

		usync.RemoveAllArchives()
		usync.AddArchive(filename)
		usync.AddAllArchives(filename)

		idx=self.getMapIdx(usync,filename)
		if idx>=0: #file is map
			archivepath=usync.GetArchivePath(filename)+filename
			springname = usync.GetMapName(idx)
			self.dumpmap(usync, springname, metadatapath, filename,idx)
			data=self.getMapData(usync, filename, idx)
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
		if version=="0.82.7":
			data['sdp']=""
			self.logger.error("Incompatible Spring unitsync.dll detected, not extracting sdp name");
		else:
			data['sdp']= self.getSDPName(usync, filename)
		self.insertData(data, fid)
		self.append_job("movefile", {"subdir": moveto})
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
	def createMapImage(self, usync, mapname, outfile, size):
		if os.path.isfile(outfile):
			self.logger.debug("[skip] " +outfile + " already exists, skipping...")
			return
		data=ctypes.string_at(usync.GetMinimap(mapname, 0), 1024*1024*2)
		im = Image.frombuffer("RGB", (1024, 1024), data, "raw", "BGR;16")
		im=im.resize(size)
		tmp=".tmp.jpg" # first create tmp file
		im.save(tmp)
		shutil.move(tmp,outfile) # rename to dest
		self.logger.debug("[created] " +outfile +" ok")

	def createMapInfoImage(self, usync, mapname, maptype, byteperpx, decoder,decoderparm, outfile, size):
		if os.path.isfile(outfile):
			self.logger.debug("[skip] " +outfile + " already exists, skipping...")
			return
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
			im=im.resize(size)
			tmp=".tmp.jpg"
			im.save(tmp)
			shutil.move(tmp,outfile)
			self.logger.debug("[created] " +outfile +" ok")

	def dumpmap(self, usync, springname, outpath, filename, idx):
		metalmap = outpath + '/' + filename + ".metalmap" + ".jpg"
		heightmap = outpath + '/' + filename + ".heightmap" + ".jpg"
		mapimage = outpath + '/' + filename + ".jpg"
		if os.path.isfile(metalmap) and os.path.isfile(heightmap) and os.path.isfile(mapimage):
			self.logger.debug("[skip] " +metalmap + " already exists, skipping...")
			self.logger.debug("[skip] " +heightmap + " already exists, skipping...")
			self.logger.debug("[skip] " +mapimage + " already exists, skipping...")
		else:
			mapwidth=float(usync.GetMapWidth(idx))
			mapheight=float(usync.GetMapHeight(idx))
			if mapwidth>mapheight:
				scaledsize=(1024, int(((mapheight/mapwidth) * 1024)))
			else:
				scaledsize=(int(((mapwidth/mapheight) * 1024)), 1024)
			self.createMapImage(usync,springname,mapimage, scaledsize)
			self.createMapInfoImage(usync,springname, "height",2, "RGB","BGR;15", heightmap, scaledsize)
			self.createMapInfoImage(usync,springname, "metal",1, "L","L;I", metalmap, scaledsize)

	def getGameDepends(self, usync, idx, gamearchivecount, game):
		res=[]
		for i in range (1, gamearchivecount): # get depends for file, idx=0 is filename itself
			deps=os.path.basename(usync.GetPrimaryModArchiveList(i))
			if not deps in self.springcontent
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
	def getSDPName(self, usync, filename):
		archiveh=usync.OpenArchive(filename)
		pos=0
		files = []
		#get a list of all files
		while True:
			name=ctypes.create_string_buffer(1024)
			size=ctypes.c_int(1024)
			res=usync.FindFilesArchive(archiveh, pos, name, ctypes.byref(size))
			if res<0:
				self.logger.error("FindFilesArchive returned invalid archive for %s" % (filename))
				break
			fileh=usync.OpenArchiveFile(archiveh, name.value)
			if fileh<0:
				self.logger.error("Invalid handle for %s %s %s" % (name.value, fileh,  ""+usync.GetNextError()))
				break
			files.append(name.value)
			pos=pos+1
		m=hashlib.md5()
		files.sort(cmp = lambda a, b: cmp(a.lower(), b.lower()))
		i=0
		for f in files:
			# ignore directory entries
			if f[-1] == '/': continue
			fileh=usync.OpenArchiveFile(archiveh, f)
			size=usync.SizeArchiveFile(archiveh, fileh)
			buf = ctypes.create_string_buffer(size)
			bytes=usync.ReadArchiveFile(archiveh, fileh, buf, size)
			usync.CloseArchiveFile(archiveh, fileh)
			m.update(hashlib.md5(f.lower()).digest())
			m.update(hashlib.md5(ctypes.string_at(buf,size)).digest())
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
		res['FileName'] = usync.GetMapFileName(idx)
		res['MapMinHeight'] = usync.GetMapMinHeight(mapname)
		res['MapMaxHeight'] = usync.GetMapMaxHeight(mapname)

		res['Resources'] = self.getMapResources(usync, idx,filename)
		res['Units'] = self.getUnits(usync, filename)

		res['StartPos']=self.getMapPositions(usync,idx,filename)
		res['Depends']=self.getMapDepends(usync,filename)
		version="" #TODO: add support
		res['Version']=version
		return res

