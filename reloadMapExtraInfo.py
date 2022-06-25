from lib import upqdb, upqconfig, extract_metadata
import os, datetime, re, json

# loads some properties and sets some automated keywords for all existing map file records
# which would normally be set by extract_metadata as files are added

# manually run after first deployment or to recalculate values if criteria changes


cfg = upqconfig.UpqConfig()
db = upqdb.UpqDB(cfg.db['url'], cfg.db['debug'])

filesToCheck = []
rows = db.query("select fid,filename,name,version,name_without_version,version_sort_number,metadata FROM file WHERE cid=2")
for row in rows:
	filesToCheck.append(dict(row))
	
for d in filesToCheck:
	fid = d["fid"]
	filename = d["filename"]
	version = d["version"]
	# workaround for version being empty on maps, get it from the file name, if possible
	if not version :
		matches = re.search('(?<=[\-_ vV])([vV]?[0-9\.]+[^\-_ ]*)(?=.sd.$)',filename)
		if matches:
			version = matches.group(1)

	nameWithoutVersion = re.sub('(?i)[\-_ ]*[vV]?'+version,'',d["name"]).strip()
	versionSortNumber = extract_metadata.getVersionSortNumber(version)
	metadata = None 
	try :
		metadata = json.loads(d["metadata"])
	except ValueError:
		print ("fid=%d filename=%s : error decoding metadata json : skip" % (fid,filename))
	
	if not metadata:
		continue
	mapWidth = int(metadata['Width'])
	mapHeight = int(metadata['Height'])

	# update those values on the file record
	db.query("UPDATE file SET name_without_version='%s', map_width=%d, map_height=%d, version_sort_number=%f WHERE fid=%d" % (nameWithoutVersion,mapWidth,mapHeight,versionSortNumber,fid))

	# set keywords
	extract_metadata.addInheritedKeywords(db,fid,nameWithoutVersion)
	extract_metadata.setSizeKeywords(db,fid,mapWidth,mapHeight)

	print ("fid=%d filename=%s nameWithoutVersion=%s versionSortNumber=%f mapWidth=%d mapHeight=%d" % (fid,filename,nameWithoutVersion,versionSortNumber,mapWidth,mapHeight) )


