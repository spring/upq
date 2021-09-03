#!/usr/bin/env python3
# This file is part of the "upq" program used on springfiles.springrts.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Matthias Ableitner (spring #at# abma #dot# de)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# extracts metadata from a spring map / game and adds it into the db

import sys
import os

if __name__ == "__main__":
	sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from lib import log, upqdb

import ctypes
from PIL import Image
from io import BytesIO
import shutil
import getopt
import base64
import tempfile
import gzip
import hashlib
import json
import traceback
import filecmp
import logging

from lib.unitsync import unitsync

def escape(string):
	"""
	>>> escape("blabla%stest")
	'blabla%%stest'
	"""
	assert(isinstance(string, str))
	string=string.replace("'","''")
#	string=string.replace('"','\"')
	string=string.replace("%", "%%")
	return string

def decodeString(string):
	if string is None:
		return ""
	try:
		string=string.decode('utf-8')
		return escape(string)
	except:
		pass
	try:
		string=string.decode('cp850')
		return escape(string)
	except:
		logging.error("Error decoding string %s" % (string))
		return ""
	return escape(string)


def get_hash(filename):
	"""
	Calculate hashes (md5, sha1, sha256) of a given file

	filename is absolute path to file

	returns: {'md5': 'x', 'sha1': 'y', 'sha256': 'z'}
	"""

	md5 = hashlib.md5()
	sha1 = hashlib.sha1()
	sha256 = hashlib.sha256()

	try:
		fd = open(filename, "rb", 4096)
	except IOError as ex:
		msg = "Unable to open '%s' for reading: '%s'." % (filename, ex)
		logging.error(msg)
		raise Exception(msg)

	while True:
		data = fd.read(4096)
		if not data: break
		md5.update(data)
		sha1.update(data)
		sha256.update(data)

	fd.close()

	return {'md5': md5.hexdigest(), 'sha1': sha1.hexdigest(), 'sha256': sha256.hexdigest()}

"""
	setup temporary directory.
	creates <tempdir>/games and symlinks archive file into that directory
"""
def setupdir(filepath, tmpdir):
	if not os.path.isfile(filepath):
		logging.error("error setting up temp dir, file doesn't exist %s" %(filepath))
		raise Exception()
	temppath=tempfile.mkdtemp(dir=tmpdir)
	archivetmp=os.path.join(temppath, "games")
	os.mkdir(archivetmp)
	tmpfile=os.path.join(archivetmp, os.path.basename(filepath))
	logging.debug("symlinking %s %s" % (filepath, tmpfile))
	os.symlink(filepath, tmpfile)
	return temppath


def getErrors(usync):
	"""
	>>> getErrors(initUnitSync())
	''
	"""
	err = usync.GetNextError()
	while not err == None:
		err += usync.GetNextError().decode()
	return err if err else ""

def getFileList(usync, archiveh):
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
			logging.error("Invalid handle for '%s' '%s': %s" % (name.value, fileh,  "" + getErrors(usync)))
			return []
		files.append(name.value.decode())
		del name
		pos=pos+1
	return files

def getSDPName(usync, archiveh):
	files = getFileList(usync, archiveh)
	m = hashlib.md5()
	files = sorted(files, key=str.casefold)
	if len(files)<=0:
		raise Exception("Zero files found!")
	i=0
	for f in files:
		# ignore directory entries
		if f[-1] == '/': continue
		content = getFile(usync, archiveh, f)
		m.update(hashlib.md5(f.encode("ascii").lower()).digest())
		m.update(hashlib.md5(content).digest())
		del content
		i=i+1
	logging.debug("SDP %s" % m.hexdigest())
	return m.hexdigest()

def getFile(usync, archivehandle, filename):
	""" returns the content of an archive"""
	fileh = usync.OpenArchiveFile(archivehandle, filename.encode("ascii"))
	if fileh < 0:
		logging.error("Couldn't open %s" %(filename))
		raise Exception("Couldn't open %s" %(filename))
	size = usync.SizeArchiveFile(archivehandle, fileh)
	if size < 0:
		logging.error("Error getting size of %s" % (filename))
		raise Exception("Error getting size of %s" % (filename))
	buf = ctypes.create_string_buffer(size)
	bytes=usync.ReadArchiveFile(archivehandle, fileh, buf, size)
	usync.CloseArchiveFile(archivehandle, fileh)
	return ctypes.string_at(buf,size)

def initUnitSync(libunitsync = None, tmpdir = None, filename = None):
	if tmpdir:
		os.environ["SPRING_DATADIR"] = tmpdir
		os.environ["HOME"] = tmpdir
	os.environ["SPRING_LOG_SECTIONS"]="unitsync,ArchiveScanner,VFS"
	if not libunitsync:
		for possibleusync in [
			"/usr/lib/spring/libunitsync.so",
			os.path.expanduser("~/.spring/engine/103.0/libunitsync.so"),
			os.path.expanduser("~/.spring/engine/amd64/103.0/libunitsync.so"),
		]:
			if os.path.isfile(possibleusync):
				libunitsync = possibleusync
	assert(libunitsync)
	usync = unitsync.Unitsync(libunitsync)
	usync.Init(True,1)
	version = usync.GetSpringVersion().decode()
	logging.debug("using unitsync version %s" %(version))
	usync.RemoveAllArchives()
	if filename:
		usync.AddArchive(filename.encode("ascii"))
		usync.AddAllArchives(filename.encode("ascii"))
	return usync

def openArchive(usync, filename):
	archiveh=usync.OpenArchive(filename.encode("ascii"))
	if archiveh<=0:
		logging.error("OpenArchive(%s) failed: %s" % (filename, getErrors(usync)))
		return False
	return archiveh

def movefile(srcfile, dstfile):
	if srcfile == dstfile:
		logging.info("File already in place: %s" %(srcfile))
		return True
	if os.path.exists(dstfile):
		if filecmp.cmp(srcfile, dstfile):
			os.remove(srcfile)
			return True
		logging.error("Destination file already exists: dst: %s src: %s" %(dstfile, srcfile))
		return False
	try:
		shutil.move(srcfile, dstfile)
	except: #move failed, try to copy + delete
		shutil.copy(srcfile, dstfile)
		try:
			os.remove(srcfile)
		except:
			logging.warn("Removing src file failed: %s" % (srcfile))
	logging.debug("moved file to (abs)%s :(rel)%s" %(srcfile, dstfile))
	try:
		os.chmod(dstfile, int("0444",8))
	except OSError:
		pass
	logging.info("moved file to %s" % (dstfile))
	return True

def GetNormalizedFilename(name, version, extension):
	"""
	>>> GetNormalizedFilename("Spring Bla älü", "0.123", ".sdz")
	'spring_bla__l_-0.123.sdz'
	"""
	""" normalize filename + renames file + updates filename in database """
	assert(isinstance(name, str))
	assert(isinstance(version, str))
	assert(extension.startswith("."))
	name=name.lower()
	if len(version)>0:
		name = str(name[:200] +"-" + version.lower())[:255]
	name += extension

	res=""
	for c in name:
		if c in "abcdefghijklmnopqrstuvwxyz-_.01234567890":
			res+=c
		else:
			res+="_"
	return res

def getMapIdx(usync, filename):
	assert(isinstance(filename, str))
	mapcount = usync.GetMapCount()
	for i in range(0, mapcount):
		usync.GetMapArchiveCount(usync.GetMapName(i)) # initialization for GetMapArchiveName()
		mapfilename = os.path.basename(usync.GetMapArchiveName(0).decode())
		if filename==mapfilename:
			return i
	return -1

def getGameIdx(usync, filename):
	assert(isinstance(filename, str))
	gamecount = usync.GetPrimaryModCount()
	for i in range(0, gamecount):
		gamename=usync.GetPrimaryModArchive(i).decode()
		if filename == gamename:
			return i
	return -1

def dumpLuaTree(usync, depth = 0):
	""" dumps a lua tree into a python dict """
	if depth > 5:
		logging.error("max depth reached!")
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
			inttables.append(key)
	count = usync.lpGetStrKeyListCount()
	for table in tables:
		usync.lpSubTableStr(table)
		res[table] = dumpLuaTree(usync, depth + 1)
		usync.lpPopTable()
	count = usync.lpGetIntKeyListCount()
	for table in inttables:
		usync.lpSubTableInt(table)
		res[table] = dumpLuaTree(usync, depth + 1)
		usync.lpPopTable()
	return res

def luaToPy(usync, archiveh, filename):
	""" laods filename from archiveh, parses it and returns lua-tables as dict """
	try:
		luafile = getFile(usync, archiveh, filename)
	except Exception as e:
		logging.error("file doesn't exist in archive: %s %s" %(filename, e))
		return {}
	usync.lpOpenSource(luafile, "r")
	usync.lpExecute()
	res = dumpLuaTree(usync)
	err = usync.lpErrorLog()
	if err:
		logging.error(err)
	return res

def getMapResources(usync, idx, Map):
	res=[]
	resourceCount=usync.GetMapResourceCount(idx)
	for i in range (0, resourceCount):
		res.append({"Name": usync.GetMapResourceName(idx, i).decode(),
			"Max": usync.GetMapResourceMax(idx, i),
			"ExtractorRadius": usync.GetMapResourceExtractorRadius(idx, i)})
	return res

def getMapPositions(usync, idx, Map):
	startpositions = usync.GetMapPosCount(idx)
	res = []
	for i in range(0, startpositions):
		x=usync.GetMapPosX(idx, i)
		z=usync.GetMapPosZ(idx, i)
		res.append({'x': x, 'z': z})
	return res

def getDepends(usync, archiveh, filename):
	filterdeps = [ 'bitmaps.sdz', 'springcontent.sdz', 'maphelper.sdz', 'cursors.sdz', 'Map Helper v1', 'Spring content v1' ]
	res = luaToPy(usync, archiveh, filename)
	if 'depend' in res:
		vals = []
		for i in res['depend'].values():
			if i not in filterdeps:
				vals.append(i)
		logging.info(vals)
		return vals
	return []

def getUnits(usync, archive):
	while usync.ProcessUnits()>0:
		err = getErrors(usync)
		if err:
			logging.error("Error processing units: %s" % (err))
	res = []
	count=usync.GetUnitCount()
	for i in range(0, count):
		res.append({ "UnitName": decodeString(usync.GetUnitName(i)),
			"FullUnitName": decodeString(usync.GetFullUnitName(i))})
	return res

def getGameData(usync, idx, gamesarchivecount, archivename, archiveh):
	res={}
	springname=usync.GetPrimaryModName(idx).decode()
	version=usync.GetPrimaryModVersion(idx).decode()
	if version==springname:
		version=""
	elif springname.endswith(version) : # Hack to get version independant string
		springname=springname[:len(springname)-len(version)]
		if springname.endswith(" ") : #remove space at end (added through unitsync hack)
			springname=springname[:len(springname)-1]

	res['Name']= springname
	res['Description']= decodeString(usync.GetPrimaryModDescription(idx))
	res['Version'] = version
	res['Depends'] =  getDepends(usync, archiveh, "modinfo.lua")
	res['Units'] = getUnits(usync, archivename)
	return res

def getMapData(usync, filename, idx, archiveh, springname):
	res={}
	mapname=usync.GetMapName(idx).decode()
	res['Name'] = mapname
	author = usync.GetMapAuthor(idx)
	res['Author'] = author.decode() if author else ""
	res['Description'] = decodeString(usync.GetMapDescription(idx))
	res['Gravity'] = usync.GetMapGravity(idx)
	res['MaxWind'] = usync.GetMapWindMax(idx)
	res['MinWind'] = usync.GetMapWindMin(idx)
	res['TidalStrength'] = usync.GetMapTidalStrength(idx)

	res['Height'] = usync.GetMapHeight(idx) / 512
	res['Width'] = usync.GetMapWidth(idx) / 512

	res['Gravity'] = usync.GetMapGravity(idx)
	res['MapFileName'] = usync.GetMapFileName(idx).decode()
	res['MapMinHeight'] = usync.GetMapMinHeight(mapname)
	res['MapMaxHeight'] = usync.GetMapMaxHeight(mapname)

	res['Resources'] = getMapResources(usync, idx,filename)
	res['Units'] = getUnits(usync, filename)

	res['StartPos'] = getMapPositions(usync,idx,filename.encode("ascii"))
	res['Depends'] = getDepends(usync, archiveh, "mapinfo.lua")
	version="" #TODO: add support
	res['Version']=version
	return res

def saveImage(image, size, imagedir):
	""" store a image, called with an Image object, returns the filename """
	m = hashlib.md5()
	m.update(image.tobytes())
	if (size[0]>1024): # shrink if to big
		sizey=int((1024.0/size[0])*size[1])
		logging.debug("image to big %dx%d, resizing... to %dx%d" % (size[0], size[1], 1024, sizey))
		image=image.resize((1024, sizey))
	else:
		image=image.resize((size[0], size[1]))
	#use md5 as filename, so it can be reused
	filename=m.hexdigest()+".jpg"
	absname=os.path.join(imagedir, filename)
	if os.path.isfile(absname) and os.path.getsize(absname) == image.size:
		logging.debug("Not overwriting %s" %(absname))
		return
	image.save(absname)
	os.chmod(absname,int("0644",8))
	logging.debug("Wrote " + absname)
	return filename

class Extract_metadata():

	def insertData(self, data):
		#logging.debug(data)
		metadata=json.dumps(data["metadata"])
		results = self.db.query("SELECT fid FROM file WHERE sdp='%s' or md5='%s'"% (data['sdp'], data['md5']))
		res=results.first()
		if res:
			fid=res['fid']
		else:
			fid=0

		assert(data["path"] in ("games", "maps"))
		assert("/" not in data["filename"])
		if fid<=0:
			fid=self.db.insert("file", {
				"name": data["name"],
				"version": data["version"],
				"sdp": data['sdp'],
				"cid": data["cid"],
				"metadata": metadata,
				"uid": 0,
				"path": data["path"],
				"filename": data["filename"],
				"timestamp": upqdb.now(), #fixme: use file timestamp
				"size": os.path.getsize(filename),
				"status": 1,
				"md5": data["md5"],
				"sha1": data["sha1"],
				"sha256": data["sha256"],
				})
		else:
			self.db.query("UPDATE file SET name='%s', version='%s', sdp='%s', cid=%s, metadata='%s', md5='%s', sha1='%s', sha256='%s', status=1 WHERE fid=%s" %(
				data['name'],
				data['version'],
				data['sdp'],
				data["cid"],
				metadata,
				data["md5"],
				data["sha1"],
				data["sha256"],
				fid
				))
		# remove already existing depends
		self.db.query("DELETE FROM file_depends WHERE fid = %s" % (fid) )
		for depend in data["metadata"]['Depends']:
			res=self.db.query("SELECT fid FROM file WHERE CONCAT(name,' ',version)='%s'" % (depend))
			row=res.first()
			if not row:
				id=0
			else:
				id=row['fid']
			try:
				self.db.insert("file_depends", {"fid":fid, "depends_string": depend, "depends_fid": id})
				logging.info("Added '%s' version '%s' to the mirror-system" % (data['name'], data['version']))
			except upqdb.UpqDBIntegrityError:
				pass
		return fid

	def createSplashImages(self, usync, archiveh, filelist):
		res = []
		for f in filelist:
			if f.lower().startswith('bitmaps/loadpictures'):
				logging.debug("Reading %s" % (f))
				buf = getFile(usync, archiveh, f)
				ioobj=BytesIO()
				ioobj.write(buf)
				ioobj.seek(0)
				del buf
				try:
					im=Image.open(ioobj)
					res.append(saveImage(im, im.size, self.cfg.paths['metadata']))
				except Exception as e:
					logging.error("Invalid image %s: %s" % (f, e))
					pass
		return res

	def extractmetadata(self, usync, archiveh, filename, filepath, metadatapath, data):

		filelist = getFileList(usync, archiveh)
		sdp = getSDPName(usync, archiveh)

		idx = getMapIdx(usync, filename)
		logging.debug("Extracting data from " + filename)
		archivepath = usync.GetArchivePath(filename).decode()+filename
		if idx>=0: #file is map
			springname = usync.GetMapName(idx).decode()
			data["metadata"] = getMapData(usync, filename, idx, archiveh, springname)
			data['mapimages'] = self.dumpmap(usync, springname, metadatapath, filename,idx)
			data['path'] = "maps"
			data["cid"] = upqdb.getCID(self.db, "map")
		else: # file is a game
			idx = getGameIdx(usync, filename)
			if idx<0:
				logging.error("Invalid file detected: %s %s %s"% (filename, getErrors(usync), idx))
				return False
			gamearchivecount = usync.GetPrimaryModArchiveCount(idx) # initialization for GetPrimaryModArchiveList()
			data["metadata"] = getGameData(usync, idx, gamearchivecount, archivepath, archiveh)
			data['path'] = "games"
			data["cid"] = upqdb.getCID(self.db, "game")

		if (sdp == "") or (data["metadata"]['Name'] == ""): #mark as broken because sdp / name is missing
			logging.error("Couldn't get name / filename")
			return False

		_, extension = os.path.splitext(filename)
		data["filename"] = GetNormalizedFilename(data["metadata"]['Name'], data["metadata"]['Version'], extension)
		data['splash'] = self.createSplashImages(usync, archiveh, filelist)

		moveto = os.path.join(self.cfg.paths['files'], data["path"], data["filename"])
		if not movefile(filepath, moveto):
			logging.error("Couldn't move file %s -> %s" %(filepath, moveto))
			return False
		assert(os.path.isfile(moveto))


		data["name"] = escape(data["metadata"]['Name'])
		data["version"] = escape(data["metadata"]['Version'])

		try:
			data['sdp']=sdp
			self.insertData(data)
		except upqdb.UpqDBIntegrityError:
			logging.error("Duplicate file detected: %s %s %s" % (data["filename"], data['name'], data['version']))
			return False

		logging.info("Updated '%s' version '%s' sdp '%s' in the mirror-system" % (data['name'], data['version'], data['sdp']))
		return True

	def __init__(self, cfg, db, filepath):
		self.cfg = cfg
		self.db = db
		#filename of the archive to be scanned
		filepath=os.path.abspath(filepath)
		filename=os.path.basename(filepath) # filename only (no path info)
		metadatapath=cfg.paths['metadata']

		if not os.path.exists(filepath):
			logging.error("File doesn't exist: %s" %(filepath))
			return

		hashes = get_hash(filepath)
		tmpdir = setupdir(filepath, self.cfg.paths['tmp']) #temporary directory for unitsync

		usync = initUnitSync(self.cfg.paths['unitsync'], tmpdir, filename)
		archiveh = openArchive(usync, os.path.join("games",filename))

		res  = self.extractmetadata(usync, archiveh, filename, filepath, metadatapath, hashes)


		usync.CloseArchive(archiveh)
		usync.RemoveAllArchives()
		usync.UnInit()
		del usync
		assert(tmpdir.startswith("/home/springfiles/upq/tmp/"))
		shutil.rmtree(tmpdir)
		logging.info("*** Done! ***")
		return


	# extracts minimap from given file
	def createMapImage(self, usync, mapname, size):
		assert(isinstance(mapname, str))
		logging.debug("Writing image: %s %dx%d"% (mapname, size[0], size[1]))
		data=ctypes.string_at(usync.GetMinimap(mapname.encode("ascii"), 0), 1024*1024*2)
		im = Image.frombuffer("RGB", (1024, 1024), data, "raw", "BGR;16")
		del data
		return saveImage(im, size, self.cfg.paths['metadata'])

	def createMapInfoImage(self, usync, mapname, maptype, byteperpx, decoder,decoderparm, size):
		assert(isinstance(mapname, str))
		assert(isinstance(maptype, str))
		width = ctypes.pointer(ctypes.c_int())
		height = ctypes.pointer(ctypes.c_int())
		usync.GetInfoMapSize(mapname.encode("ascii"), maptype.encode("ascii"), width, height)
		width = width.contents.value
		height = height.contents.value
		assert(width > 0)
		assert(height > 0)
		logging.debug("Writing image <%s>: %dx%d"% (maptype, width, height))
		data = ctypes.create_string_buffer(int(width*height*byteperpx*2))
		data.restype = ctypes.c_void_p
		ret=usync.GetInfoMap(mapname.encode("ascii"), maptype.encode("ascii"), data, byteperpx)
		if ret != 0:
			im = Image.frombuffer(decoder, (width, height), data, "raw", decoderparm)
			im=im.convert("L")
			res = saveImage(im, size, self.cfg.paths['metadata'])
			del data
			return res
		del data
		logging.error("Error creating image %s" % (getErrors(usync)))
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

if __name__ == "__main__":
	import doctest
	doctest.testmod()

