from lib import upqdb, upqconfig
import os, datetime, re


cfg = upqconfig.UpqConfig()
db = upqdb.UpqDB(cfg.db['url'], cfg.db['debug'])

MAP_KW_FILE="mapKeywords.txt"


print(" --- Importing map keywords --- ")

if not os.path.isfile(MAP_KW_FILE) :
	print(MAP_KW_FILE+" not found : aborted")
	sys.exit(1)


mapNamePat = re.compile('[a-zA-Z0-9_ ()!:\'.\-]+')
mapKwPat = re.compile('[a-z0-9]+')

kwFile = open(MAP_KW_FILE, 'r')
count = 0


while True:
	count += 1
	line = kwFile.readline()

	# end of file is reached
	if not line:
		break
	line = line.strip()
	print("processing : "+line)
	
	lineArr = line.split(";")
	
	mapName = lineArr[0]
	if not mapNamePat.fullmatch(mapName):
		print("map name has invalid characters: "+mapName+" : skip")
		continue
	mapName = mapName.replace("'","\\'")

	#print("name="+mapName)
	# remove keywords for this map, if any
	db.query("DELETE fk FROM file_keyword fk LEFT JOIN file f ON (f.fid=fk.fid) WHERE f.cid=2 AND f.name_without_version='"+mapName+"'")
	
	# if new keywords are set, add them
	length = len(lineArr)
	if length > 1 :
		i = 1
		while i < length:
			kw = lineArr[i]
			i+=1
			if not mapKwPat.fullmatch(kw):
				print("keyword has invalid characters: "+kw+" : skip")
				continue
			#print("kw="+kw)
			db.query("REPLACE INTO file_keyword (SELECT fid,'"+kw+"' FROM file WHERE cid=2 AND name_without_version='"+mapName+"')")
			


kwFile.close()



