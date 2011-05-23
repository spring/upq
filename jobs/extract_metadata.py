# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#called with fileid, extracts/inserts metadata
#calls upload

import upqtask
from upqjob import UpqJob

from unitsync import unitsync as unitsyncpkg
import sys
import os
import ctypes
import Image
import shutil
import getopt
import base64

import sys
sys.path.append('metalink')
import metalink

from xml.dom import minidom

class Extract_metadata(UpqJob):
	def run(self):
		unitsync=self.jobcfg['unitsync']
		outputpath=self.jobcfg['outputpath']
		datadir=self.jobcfg['datadir']

		outputpath = os.path.abspath(outputpath)
		os.environ["SPRING_DATADIR"]=outputpath
		usync = unitsyncpkg.Unitsync(unitsync)

		usync.Init(True,1)
		mapcount = usync.GetMapCount()
		gamescount = usync.GetPrimaryModCount()
		createdict(usync,gamescount, mapcount)
		for i in range(0, mapcount):
			maparchivecount = usync.GetMapArchiveCount(usync.GetMapName(i)) # initialization for GetMapArchiveName()
			filename = os.path.basename(usync.GetMapArchiveName(0))
			archivepath=usync.GetArchivePath(filename)+filename
			print "["+str(i) +"/"+ str(mapcount)+ "] extracting data from "+filename
			springname = usync.GetMapName(i)
			dumpmap(usync, springname, outputpath, filename,i)
			writeMapXmlData(usync, springname, i, outputpath +"/" +filename+".metadata.xml",maparchivecount, archivepath)
			create_torrent(archivepath, outputpath +"/" +filename+".torrent")
		for i in range (0, gamescount):
			springname=usync.GetPrimaryModName(i)
			filename=usync.GetPrimaryModArchive(i)
			archivepath=usync.GetArchivePath(filename)+filename
			print "["+str(i) +"/"+ str(gamescount)+ "] extracting data from "+filename
			gamearchivecount=usync.GetPrimaryModArchiveCount(i) # initialization for GetPrimaryModArchiveList()
			writeGameXmlData(usync, springname, i, outputpath + "/" + filename + ".metadata.xml", gamearchivecount, archivepath)
			create_torrent(archivepath, outputpath +"/" +filename+".torrent")
		print "Parsed "+ str(gamescount) + " games, " + str(mapcount) + " maps"

	#calls extract metadata script
	#if no category set, use category from metadata, move + rename file there

	springcontent = [ 'bitmaps.sdz', 'springcontent.sdz', 'maphelper.sdz', 'cursors.sdz' ]

	def getXmlData(doc, parent, element, value):
		node = doc.createElement(element)
		value = str(value)
		value = value.decode('utf-8','replace')
		subnode = doc.createTextNode(value)
		node.appendChild(subnode)
		parent.appendChild(node)

	def getMapPositions(usync,doc, idx, Map):
		positions = doc.createElement("Positions")
		startpositions = usync.GetMapPosCount(idx)
		for i in range(0, startpositions):
			startpos=doc.createElement("StartPos")
			getXmlData(doc, startpos, "X", str(usync.GetMapPosX(idx, i)))
			getXmlData(doc, startpos, "Z", str(usync.GetMapPosZ(idx, i)))
			positions.appendChild(startpos)
		Map.appendChild(positions)

	def getMapDepends(usync,doc,idx,Map,maparchivecount):
		for j in range (1, maparchivecount): # get depends for file, idx=0 is filename itself
			deps=os.path.basename(usync.GetMapArchiveName(j))
			node = doc.createElement("Depends")
			if not deps in springcontent:
				getXmlData(doc, node, "Depend", str(deps))
		Map.appendChild(node)
	def getMapResources(usync,doc,idx,Map, maparchivecount):
		resources = doc.createElement("MapResources")
		resourceCount=usync.GetMapResourceCount(idx)
		for i in range (0, resourceCount):
			resource=doc.createElement("Resource")
			getXmlData(doc, resource, "Name", str(usync.GetMapResourceName(idx, i)))
			getXmlData(doc, resource, "Max", str(usync.GetMapResourceMax(idx, i)))
			getXmlData(doc, resource, "ExtractorRadius", str(usync.GetMapResourceExtractorRadius(idx, i)))
			resources.appendChild(resource)
		Map.appendChild(resources)

	def writeMapXmlData(usync, smap, idx, filename,maparchivecount,archivename):
			if os.path.isfile(filename):
			print "[skip] " +filename + " already exists, skipping..."
		else:
			doc = minidom.Document()
			archive = doc.createElement("Archive")
			getXmlData(doc, archive, "Type", "Map")
			mapname=usync.GetMapName(idx)
			getXmlData(doc, archive, "Name", mapname)
			getXmlData(doc, archive, "Author", usync.GetMapAuthor(idx))
			getXmlData(doc, archive, "Description", usync.GetMapDescription(idx))
			getXmlData(doc, archive, "Gravity", str(usync.GetMapGravity(idx)))
			getXmlData(doc, archive, "MaxWind", str(usync.GetMapWindMax(idx)))
			getXmlData(doc, archive, "MinWind", str(usync.GetMapWindMin(idx)))
					getXmlData(doc, archive, "TidalStrength", str(usync.GetMapTidalStrength(idx)))

			getXmlData(doc, archive, "Height", str(usync.GetMapHeight(idx)))
			getXmlData(doc, archive, "Width", str(usync.GetMapWidth(idx)))

					getXmlData(doc, archive, "Gravity", str(usync.GetMapGravity(idx)))
					getXmlData(doc, archive, "FileName", str(usync.GetMapFileName(idx)))
					getXmlData(doc, archive, "MapMinHeight", str(usync.GetMapMinHeight(mapname)))
					getXmlData(doc, archive, "MapMaxHeight", str(usync.GetMapMaxHeight(mapname)))

			getMapResources(usync, doc, idx,archive, maparchivecount)

			getMapPositions(usync,doc,idx,archive)
			getMapDepends(usync,doc,idx,archive,maparchivecount)
			doc.appendChild(archive)
			tmp=".tmp.xml"
			metadata = open(tmp,'w')
			metadata.write(doc.toxml("utf-8"))
			metadata.close()
			shutil.move(tmp,filename)
			print "[created] " +filename +" ok"

	# extracts minimap from given file
	def createMapImage(usync, mapname, outfile, size):
		if os.path.isfile(outfile):
			print "[skip] " +outfile + " already exists, skipping..."
			return
		data=ctypes.string_at(usync.GetMinimap(mapname, 0), 1024*1024*2)
		im = Image.frombuffer("RGB", (1024, 1024), data, "raw", "BGR;16")
		im=im.resize(size)
		tmp=".tmp.jpg" # first create tmp file
		im.save(tmp)
		shutil.move(tmp,outfile) # rename to dest
		print "[created] " +outfile +" ok"

	def createMapInfoImage(usync, mapname, maptype, byteperpx, decoder,decoderparm, outfile, size):
		if os.path.isfile(outfile):
			print "[skip] " +outfile + " already exists, skipping..."
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
			print "[created] " +outfile +" ok"


	def dumpmap(usync, springname, outpath, filename, idx):
		metalmap = outpath + '/' + filename + ".metalmap" + ".jpg"
		heightmap = outpath + '/' + filename + ".heightmap" + ".jpg"
		mapimage = outpath + '/' + filename + ".jpg"
		if os.path.isfile(metalmap) and os.path.isfile(heightmap) and os.path.isfile(mapimage):
			print "[skip] " +metalmap + " already exists, skipping..."
			print "[skip] " +heightmap + " already exists, skipping..."
			print "[skip] " +mapimage + " already exists, skipping..."
		else:
			mapwidth=float(usync.GetMapWidth(idx))
			mapheight=float(usync.GetMapHeight(idx))
			if mapwidth>mapheight:
				scaledsize=(1024, int(((mapheight/mapwidth) * 1024)))
			else:
				scaledsize=(int(((mapwidth/mapheight) * 1024)), 1024)
			createMapImage(usync,springname,mapimage, scaledsize)
			createMapInfoImage(usync,springname, "height",2, "RGB","BGR;15", heightmap, scaledsize)
			createMapInfoImage(usync,springname, "metal",1, "L","L;I", metalmap, scaledsize)

	def getGameDepends(usync, idx, gamearchivecount, doc, game):
		depends = doc.createElement("Depends")
		game.appendChild(depends)
		for i in range (1, gamearchivecount): # get depends for file, idx=0 is filename itself
			deps=os.path.basename(usync.GetPrimaryModArchiveList(i))
			print deps
			if not deps in springcontent and not deps.endswith(".sdp"): #FIXME: .sdp is returned wrong by unitsync
				if deps in springnames:
					depend=springnames[deps]
				else:
					depend=deps
				getXmlData(doc, depends, "Depend", depend)

	def writeGameXmlData(usync, springname, idx, filename,gamesarchivecount, archivename):
		if os.path.isfile(filename):
			print "[skip] " +filename + " already exists, skipping..."
			return
		doc = minidom.Document()
		archive = doc.createElement("Archive")
		doc.appendChild(archive)
		version=usync.GetPrimaryModVersion(idx)
		if springname.endswith(version) : # Hack to get version independant string
			springname=springname[:len(springname)-len(version)]
			if springname.endswith(" ") : #remove space at end (added through unitsync hack)
				springname=springname[:len(springname)-1]
		getXmlData(doc, archive, "Type", "Game")
		getXmlData(doc, archive, "Name", springname)
		getXmlData(doc, archive, "Description", usync.GetPrimaryModDescription(idx))
		getXmlData(doc, archive, "Version", version)
		getGameDepends(usync, idx, gamesarchivecount, doc, archive)
		tmp=".tmp.xml"
		f=open(tmp, 'w')
		f.write(doc.toxml("utf-8"))
		f.close()
		shutil.move(tmp,filename)
		print "[created] " +filename +" ok"


	def usage():
		print "--help \n\
	--output <outputdir>\n\
	--unitsync <libunitsync.so>\n\
	--datadir <maps/gamesdir>\n\
	"
	springnames={}
	def createdict(usync,gamescount, mapcount):
		#create dict with springnames[filename]=springname
		for i in range(0, gamescount):
			springname=usync.GetPrimaryModName(i)
			filename=usync.GetPrimaryModArchive(i)
			springnames[filename]=springname
		for i in range(0, mapcount):
			maparchivecount = usync.GetMapArchiveCount(usync.GetMapName(i)) # initialization for GetMapArchiveName()
			filename = os.path.basename(usync.GetMapArchiveName(0))
			print "["+str(i) +"/"+ str(mapcount)+ "] extracting data from "+filename
			springname = usync.GetMapName(i)
			springnames[filename]=springname

	def create_torrent(filename, output):
		if os.path.isdir(filename):
			print "[skip] " +filename + "is a directory, can't create torrent"
			return
		if os.path.isfile(output):
			print "[skip] " +output + " already exists, skipping..."
			return
		metalink._opts = { 'overwrite': False }
		filesize=os.path.getsize(filename)
		torrent = metalink.Torrent(filename)
		m = metalink.Metafile()
		m.hashes.filename=filename
		m.scan_file(filename, True, 255, 1)
		m.hashes.get_multiple('ed2k')
		torrent_options = {'files':[[metalink.encode_text(filename), int(filesize)]],
			'piece length':int(m.hashes.piecelength),
			'pieces':m.hashes.pieces,
			'encoding':'UTF-8',
			}
		data=torrent.create(torrent_options)
		tmp=".tmp.torrent"
		f=open(tmp,"wb")
		f.write(data)
		f.close()
		shutil.move(tmp,output)
		print "[created] " +output +" ok"
