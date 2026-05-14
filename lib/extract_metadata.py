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

from lib import log

import ctypes
from io import BytesIO
import shutil
import tempfile
import hashlib
import json
import filecmp
import logging
import datetime
import re
import subprocess

# done to avoid issue where libunitsync segfaults on Init if it runs after importing these
if __name__ != "__main__":
	from lib import upqdb
	from PIL import Image

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

	with open(filename, "rb", 4096) as f:
		while True:
			data = f.read(4096)
			if not data: break
			md5.update(data)
			sha1.update(data)
			sha256.update(data)

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
	msg = usync.GetNextError()
	err = ""
	while not msg == None:
		err += msg.decode()
		msg = usync.GetNextError()
	return err

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

def getunitsyncpath():
	for possibleusync in [
		"/usr/lib/spring/libunitsync.so",
		os.path.expanduser("~/.spring/engine/103.0/libunitsync.so"),
		os.path.expanduser("~/.spring/engine/amd64/103.0/libunitsync.so"),
	]:
		if os.path.isfile(possibleusync):
			return possibleusync

def initUnitSync(libunitsync = None, tmpdir = None):
	if not libunitsync:
		libunitsync = getunitsyncpath()
	assert(libunitsync)
	if tmpdir:
		os.environ["SPRING_DATADIR"] = tmpdir
		os.environ["HOME"] = tmpdir
	os.environ["SPRING_LOG_SECTIONS"]="unitsync,ArchiveScanner,VFS"
	usync = unitsync.Unitsync(libunitsync)
	usync.Init(True, 1)
	msgs = getErrors(usync)
	if msgs:
		logging.error(msgs)
	version = usync.GetSpringVersion().decode()
	logging.debug("using unitsync version %s" %(version))
	usync.RemoveAllArchives()
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
	shutil.move(srcfile, dstfile)
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
	logging.info(f"mapCount={mapcount}")
	for i in range(0, mapcount):
		mac=usync.GetMapArchiveCount(usync.GetMapName(i)) # initialization for GetMapArchiveName()
		logging.info(f"mapIdx={i} GetMapFileName()={usync.GetMapFileName(i).decode()} GetMapArchiveName()={usync.GetMapArchiveName(i).decode()} GetMapName={usync.GetMapName(i).decode()}")
		mapfilename = os.path.basename(usync.GetMapArchiveName(i).decode())
		if filename==mapfilename:       # this never matches because GetMapArchiveName returns the spring name not the file name e.g. "Wanderlust 2.1" instead of "wanderlust_2.1.sd7"
			return i
		else:
			return 0        # just assume it's the first map item
	return -1

def getGameIdx(usync, filename):
	assert(isinstance(filename, str))
	gamecount = usync.GetPrimaryModCount()
	logging.info(f"gameCount={gamecount}")
	for i in range(0, gamecount):
		gameName=usync.GetPrimaryModArchive(i).decode()
		logging.info(f"gameIdx {i} {gameName}")
		if filename == gameName:
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
	""" loads filename from archiveh, parses it and returns lua-tables as dict """
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

#TODO uses deprecated functions on the lib, remove?
def getMapResources(usync, idx, Map):
	res=[]
	resourceCount=usync.GetMapResourceCount(idx)
	for i in range (0, resourceCount):
		res.append({"Name": usync.GetMapResourceName(idx, i).decode(),
			"Max": usync.GetMapResourceMax(idx, i),
			"ExtractorRadius": usync.GetMapResourceExtractorRadius(idx, i)})
	return res

#TODO uses deprecated functions on the lib, remove?
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


def getInfoMap(usync,infoCount):
	propMap = {}
	for i in range(infoCount):
		key = usync.GetInfoKey(i)
		infoType = usync.GetInfoType(i)

		if isinstance(key, bytes):
			key = key.decode('utf-8')

		if isinstance(infoType, bytes):
			infoType = infoType.decode('utf-8')

		try:
			if infoType == 'integer':
				value = usync.GetInfoValueInteger(i)
			elif infoType == 'float':
				value = usync.GetInfoValueFloat(i)
			elif infoType == 'bool':
				value = usync.GetInfoValueBool(i)
			elif infoType == 'string':
				value = usync.GetInfoValueString(i)
				if isinstance(value, bytes):
					value = value.decode('utf-8')
			else:
				value = None

			# Store with lowercase key for case-insensitive lookup
			propMap[key.lower()] = value
			logging.info(f"  {key} ({infoType}): {value}")
		except Exception as e:
			logging.error(f"  Error reading {key}: {e}")
			continue
	return propMap

def getPropFromInfoMap(propMap, propName, default=None):
	return propMap.get(propName.lower(), default)

def addResPropIfSet(resMap,propMap,propName,resPropName,default=None):
	value = getPropFromInfoMap(propMap, propName, default)
	if value is not None:
		resMap[resPropName] = value

def getGameData(usync, idx, archivename, archiveh):
	res = {}

	try:
		infoCount = usync.GetPrimaryModInfoCount(idx)
		if infoCount <= 0:
			logging.info(f"No mod info available for {archivename}")
			return res

		# Create a dictionary with lowercase keys for case-insensitive lookup
		propMap = getInfoMap(usync,infoCount)

		addResPropIfSet(res,propMap,'name_pure','Name')
		addResPropIfSet(res,propMap,'description','Description')
		addResPropIfSet(res,propMap,'version','Version')
		addResPropIfSet(res,propMap,'author','Author')
		addResPropIfSet(res,propMap,'shortname','Shortname')
		addResPropIfSet(res,propMap,'mutator','Mutator')
		addResPropIfSet(res,propMap,'game','Game')

		logging.info(f"Successfully extracted {len(propMap)} properties from {archivename}")

		# other properties
		res['Depends'] =  getDepends(usync, archiveh, "modinfo.lua")
		res['Units'] = getUnits(usync, archivename)
		return res
	except AttributeError as e:
		logging.error(f"Error: GetPrimaryModInfoCount not available: {e}")
		return res

def getMapData(usync, filename, idx, archiveh, springname):
	res = {}

	mapname = usync.GetMapName(idx).decode()
	res['Name'] = mapname
	res['Version'] = ""		#TODO as of may 2026, lib still doesn't actually add this to its info map

	try:
		infoCount = usync.GetMapInfoCount(idx)
		if infoCount <= 0:
			logging.info(f"No map info available for {springname}")
			return res

		# Create a dictionary with lowercase keys for case-insensitive lookup
		propMap = getInfoMap(usync,infoCount)

		addResPropIfSet(res,propMap,'minwind','MinWind')
		addResPropIfSet(res,propMap,'maxwind','MaxWind')
		addResPropIfSet(res,propMap,'tidalstrength','TidalStrength')
		addResPropIfSet(res,propMap,'gravity','Gravity')
		addResPropIfSet(res,propMap,'maxmetal','MaxMetal')
		addResPropIfSet(res,propMap,'extractorradius','ExtractorRadius')
		addResPropIfSet(res,propMap,'author','Author')
		addResPropIfSet(res,propMap,'description','Description')
		addResPropIfSet(res,propMap,'width','Width')
		addResPropIfSet(res,propMap,'height','Height')
		addResPropIfSet(res,propMap,'version','Version')
		
		if res['Height'] is not None:
			res['Height'] = res['Height']/512

		if res['Width'] is not None:
			res['Width'] = res['Width']/512

		logging.info(f"Successfully extracted {len(propMap)} properties from {springname}")

		# other properties
		#res['Resources'] = getMapResources(usync, idx,filename)
		#res['Units'] = getUnits(usync, filename)
		#res['StartPos'] = getMapPositions(usync,idx,filename.encode("ascii"))
		res['Depends'] = getDepends(usync, archiveh, "mapinfo.lua")
		return res
	except Exception as e:
		logging.error(f"Error getting map data: {e}")
		#traceback.print_exc()
		return res

def saveImage(image, size, imagedir, createThumbnail=None):
	""" store a image, called with an Image object, returns the filename """
	m = hashlib.md5()
	m.update(image.tobytes())
	if (size[0]>1024): # shrink if too big
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
	logging.debug("Wrote " + filename)
	# add thumbnail, if necessary
	if createThumbnail is not None:
		image = Image.open(absname)
		image.thumbnail((256, 256))
		thumbName = absname.replace('.jpg','_thumbnail.jpg')
		image.save(thumbName)
		os.chmod(thumbName,int("0644",8))
		logging.debug("Wrote " + thumbName)
	return filename


def insertData(db, data):
	#logging.debug(data)
	metadata=json.dumps(data["metadata"])
	results = db.query("SELECT fid FROM file WHERE sdp='%s' or md5='%s'"% (data['sdp'], data['md5']))
	res=results.first()
	if res:
		fid=res._mapping['fid']
	else:
		fid=0

	assert(data["path"] in ("games", "maps"))
	assert("/" not in data["filename"])
	assert(data["uid"] > 0)
	data["cid"] = upqdb.getCID(db, data["category_name"])
	if fid<=0:
		fid=db.insert("file", {
			"name": data["name"],
			"version": data["version"],
			"sdp": data['sdp'],
			"cid": data["cid"],
			"metadata": metadata,
			"uid": data['uid'],
			"path": data["path"],
			"name_without_version": data.get("name_without_version"),
			"map_width": data.get("map_width",0),
			"map_height": data.get("map_height",0),
			"version_sort_number": data.get("version_sort_number",0),
			"filename": data["filename"],
			"timestamp": data["timestamp"],
			"size": data["size"],
			"status": 1,
			"md5": data["md5"],
			"sha1": data["sha1"],
			"sha256": data["sha256"],
			})
	else:
		db.query("UPDATE file SET name='%s', version='%s', sdp='%s', cid=%s, metadata='%s', md5='%s', sha1='%s', sha256='%s', status=1, filename='%s', path='%s', name_without_version='%s', map_width=%d, map_height=%d, version_sort_number=%f WHERE fid=%s" %(
			data['name'],
			data['version'],
			data['sdp'],
			data["cid"],
			metadata,
			data["md5"],
			data["sha1"],
			data["sha256"],
			data["filename"],
			data["path"],
			data.get("name_without_version"),
			data.get("map_width",0),
			data.get("map_height",0),
			data.get("version_sort_number",0),
			fid
			))
	# remove already existing depends
	db.query("DELETE FROM file_depends WHERE fid = %s" % (fid) )
	if 'Depends' in data["metadata"]:
		for depend in data["metadata"]['Depends']:
			res=db.query("SELECT fid FROM file WHERE CONCAT(name,' ',version)='%s'" % (depend))
			row=res.first()
			if not row:
				id=0
			else:
				id=row._mapping['fid']
			try:
				db.insert("file_depends", {"fid":fid, "depends_string": depend, "depends_fid": id})
				logging.info("Added '%s' version '%s' to the mirror-system" % (data['name'], data['version']))
			except upqdb.UpqDBIntegrityError:
				pass
	return fid

def createSplashImages(usync, archiveh, filelist, metadir):
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
				res.append(saveImage(im, im.size, metadir))
			except Exception as e:
				logging.error("Invalid image %s: %s" % (f, e))
				pass
	return res

# extracts minimap from given file
def createMapImage(usync, mapname, size, metadir):
	assert(isinstance(mapname, str))
	logging.debug("Writing image: %s %dx%d"% (mapname, size[0], size[1]))
	data=ctypes.string_at(usync.GetMinimap(mapname.encode("ascii"), 0), 1024*1024*2)
	im = Image.frombuffer("RGB", (1024, 1024), data, "raw", "BGR;16")
	del data
	return saveImage(im, size, metadir, True)

def createMapInfoImage(usync, mapname, maptype, byteperpx, decoder,decoderparm, size, metadir):
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
		res = saveImage(im, size, metadir)
		del data
		return res
	del data
	logging.error("Error creating image %s" % (getErrors(usync)))
	raise Exception("Error creating image")

def dumpMap(usync, springname, outpath, filename, idx, mapData):
	mapwidth=float(mapData['Width'])
	mapheight=float(mapData['Height'])
	if mapwidth>mapheight:
		scaledsize=(1024, int(((mapheight/mapwidth) * 1024)))
	else:
		scaledsize=(int(((mapwidth/mapheight) * 1024)), 1024)
	res = []
	res.append(createMapImage(usync,springname, scaledsize, outpath))
	res.append(createMapInfoImage(usync,springname, "height",2, "RGB","BGR;15", scaledsize, outpath))
	res.append(createMapInfoImage(usync,springname, "metal",1, "L","L;I", scaledsize, outpath))
	return res

def getVersionFromFilename(filename):
	version = ""
	matches = re.search(r'(?<=[\-_ vV])([vV]?[0-9\.]+[^\-_ ]*)(?=.sd.$)',filename)
	if matches:
		version = matches.group(1)
	return version

def getNameWithoutVersion(name,version):
	if version:
		return re.sub(r'(?i)[\-_ ]*[vV]?'+version,'',name).strip()
	return name

def getVersionSortNumber(version):
	vCompArr=version.split('.')
	cvString = ""
	first = True
	for vComp in vCompArr:
		if first:
			cvString += re.sub('[^0-9]','',vComp)
			cvString += '.'
			first = False
		else:
			cvString += '0'+re.sub('[^0-9]','0',vComp)
	result = 0
	try:
		result = float(cvString)
	except ValueError:
		result = 0
		
	return result

# copy keywords from previously added files corresponding to different versions of the same item, excluding the map size ones	
def addInheritedKeywords(db,fid,nameWithoutVersion):
	nameWithoutVersion = nameWithoutVersion.replace("'","\\'")
	db.query("INSERT IGNORE INTO file_keyword (SELECT DISTINCT %d,keyword FROM file_keyword fk INNER JOIN file f ON (fk.fid=f.fid) WHERE f.name_without_version='%s' AND fk.keyword NOT IN ('small','medium','large'))" % (fid,nameWithoutVersion))

def setSizeKeywords(db,fid,width,height):
	kw = "small"
	if width*height > 18*18:
		kw = "large"
	elif width*height > 12*12:
		kw = "medium"
	db.query("REPLACE INTO file_keyword(fid,keyword) VALUES(%d,'%s')" % (fid,kw))

def extractmetadata(usync, filepath, metadir):
	"""
	>>> datadir = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)),  "../tests"))
	>>> mapfile = os.path.join(datadir, "maps/blank_v1.sd7")
	>>> assert(os.path.isfile(mapfile))
	>>> tmpdir = setupdir(mapfile, "/tmp")
	>>> usync = initUnitSync(tmpdir=tmpdir)
	>>> data = extractmetadata(usync, mapfile, "/tmp/")
	>>> print(data['metadata']['MapFileName'] == 'maps/Blank v1.smf')
	True
	"""

	data = get_hash(filepath)
	data["size"] = os.path.getsize(filepath)
	data["timestamp"] = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))

	filename=os.path.basename(filepath) # filename only (no path info)

	usync.AddArchive(filename.encode("ascii"))
	usync.AddAllArchives(filename.encode("ascii"))
	archiveh = openArchive(usync, os.path.join("games", filename))


	filelist = getFileList(usync, archiveh)
	sdp = getSDPName(usync, archiveh)

	idx = getMapIdx(usync, filename)
	logging.debug("Extracting data from " + filename)
	archivepath = usync.GetArchivePath(filename).decode()+filename
	if idx>=0: #file is map
		springname = usync.GetMapName(idx).decode()
		data["metadata"] = getMapData(usync, filename, idx, archiveh, springname)
		data['metadata']['mapimages'] = dumpMap(usync, springname, metadir, filename,idx, data['metadata'])
		data['path'] = "maps"
		data['category_name'] = "map"
	else: # file is a game
		idx = getGameIdx(usync, filename)
		if idx<0:
			logging.error("Invalid file detected: %s %s %s"% (filename, getErrors(usync), idx))
			return False
		gamearchivecount = usync.GetPrimaryModArchiveCount(idx) # initialization for GetPrimaryModArchiveList()
		data["metadata"] = getGameData(usync, idx, archivepath, archiveh)
		data['path'] = "games"
		data['category_name'] = "game"

	if (sdp == "") or (data["metadata"]['Name'] == ""): #mark as broken because sdp / name is missing
		logging.error("Couldn't get name / filename")
		return False

	_, extension = os.path.splitext(filename)
	data["filename"] = GetNormalizedFilename(data["metadata"]['Name'], data["metadata"]['Version'], extension)
	data['metadata']['splash'] = createSplashImages(usync, archiveh, filelist, metadir)
	data["name"] = escape(data["metadata"]['Name'])
	data["version"] = escape(data["metadata"]['Version'])
	data['sdp']=sdp
	if data['category_name'] == "map" : # file is map
		version = data["version"]
		# workaround for version being empty on maps, get it from the file name, if possible
		if not version : 
			version = getVersionFromFilename(data["filename"])

		data["name_without_version"] = getNameWithoutVersion(data["name"],version)
		data["version_sort_number"] = getVersionSortNumber(version)
		
		metadata = data["metadata"]
		data["map_width"] = int(metadata['Width'])
		data["map_height"] = int(metadata['Height'])
	
	usync.CloseArchive(archiveh)
	return data

def extract_metadata_unitsync(cfg, db, filepath, accountid, tmpdir):
	#filename of the archive to be scanned
	filepath=os.path.abspath(filepath)

	if not os.path.exists(filepath):
		logging.error("File doesn't exist: %s" %(filepath))
		return False

	# get data for content package using unitsync lib
	#usync = initUnitSync(cfg.paths['unitsync'], tmpdir)
	#data = extractmetadata(usync, filepath, cfg.paths["metadata"])
	#usync.RemoveAllArchives()
	#usync.UnInit()
	#del usync
	# use external process as workaround for usync.Init crashing after importing sqlalchemy or PIL.image
	try:
		result = subprocess.run(
			[sys.executable, os.path.join(os.path.dirname(__file__), "extract_metadata.py"), tmpdir, filepath],
			capture_output=True,
			text=True,
			timeout=30  # 30 second timeout
		)
        
		if result.returncode != 0:
			logging.error(f"Worker failed: {result.stderr}")
			return False


		# Split output by marker and parse JSON output after it
		if "--- RESULT" not in result.stdout:
			logging.error("Marker '--- RESULT' not found in output")
			return False

		jsonOutput = result.stdout.split("--- RESULT", 1)[1].strip()
		data = json.loads(jsonOutput)
	except subprocess.TimeoutExpired:
		logging.error("Metadata extraction timeout")
		return False
	except json.JSONDecodeError:
		logging.error(f"Invalid JSON from worker: {result.stdout}")
		return False
	except Exception as e:
		logging.error(f"ERROR : {e}")
		return False
	if "timestamp" in data:
		data['timestmap'] = datetime.datetime.fromisoformat(data['timestamp'])

	data['uid'] = accountid

	moveto = os.path.join(cfg.paths['files'], data["path"], data["filename"])
	movefile(filepath, moveto)
	assert(os.path.isfile(moveto))

	fid = 0
	try:
		fid = insertData(db, data)
	except upqdb.UpqDBIntegrityError as e:
		logging.error("Duplicate file detected: %s %s %s %s" % (data["filename"], data['name'], data['version'], str(e)))
		return False

	logging.info("Updated '%s' version '%s' sdp '%s' in the mirror-system" % (data['name'], data['version'], data['sdp']))
		
	# add keywords information
	if fid > 0 and data.get('category_name') == "map" :
		addInheritedKeywords(db,fid,data["name_without_version"])
		setSizeKeywords(db,fid,data["map_width"],data["map_height"])
	
	logging.info("*** Done! ***")
	return True


def Extract_metadata(cfg, db, filepath, accountid):
	oldcwd = os.getcwd() # unitsync chdirs, keep current cwd, to restore it later
	tmpdir = setupdir(filepath, cfg.paths['tmp']) #temporary directory for unitsync
	try:
		return extract_metadata_unitsync(cfg, db, filepath, accountid, tmpdir)
	finally:
		assert tmpdir.startswith("/home/springfiles/upq/tmp/")
		shutil.rmtree(tmpdir)
		os.chdir(oldcwd)

if __name__ == "__main__":
	# when run directly, print extracted metadata as json
	# useful for testing and required to avoid issue where importing sqlalchemy or PIL.image makes unitsync's Init segfault
	tmpdir = ""
	filepath = ""
	if len(sys.argv) < 3:
		print("Usage : extract_metadata.py <tmpdir> <filepath>")
		sys.exit(1)
	else:
		tmpdir = sys.argv[1]
		filepath = sys.argv[2]
		
	
	from lib import upqconfig
	cfg = upqconfig.UpqConfig()

	logging.info(f"usync={cfg.paths['unitsync']} meta={cfg.paths['metadata']}")
	usync = initUnitSync(cfg.paths['unitsync'], tmpdir)
	from PIL import Image		# import this after running Init
	data = extractmetadata(usync, filepath, cfg.paths["metadata"])
	if data['timestamp']:
		data['timestamp'] = data['timestamp'].isoformat()
	usync.RemoveAllArchives()
	usync.UnInit()
	del usync
	logging.info(f"result={data}")
	print("--- RESULT")
	print(json.dumps(data, indent=2))

	#import doctest
	#doctest.testmod()

