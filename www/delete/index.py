#!/usr/bin/python3

import sys, cgi, os, cgitb, html, shutil, re
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
from lib import upqconfig
from lib import log, upqdb

BASE_PATH = "/home/springfiles/upq"
MAP_IMAGE_PATH = BASE_PATH+"/metadata"
GAME_PATH = BASE_PATH+"/files/games"
MAP_PATH = BASE_PATH+"/files/maps"
cfg = upqconfig.UpqConfig()
db = upqdb.UpqDB(cfg.db['url'], cfg.db['debug'])


def ShowForm(tplvars):
	with open("form.html", "r") as f:
		content = f.read()
	for k, v in tplvars.items():
		content = content.replace("%" + k + "%", v)
	print(content)

def CheckAuth(username, password):
	if not username or not password:
		return False
	import xmlrpc.client
	proxy = xmlrpc.client.ServerProxy("https://springrts.com/api/uber/xmlrpc")
	res = proxy.get_account_info(username, password)
	if res["status"] == 0:
		return res["accountid"]
	return False

def CheckFields(form, required):
	for k in required:
		if not k in form:
			return False
	return True


def DeleteAssociatedRecords(fid):
	#db.query("DELETE FROM file_depends WHERE fid=%d" % fid)	#TODO table is empty
	db.query("DELETE FROM file_keyword WHERE fid=%d" % fid)
	#db.query("DELETE FROM image_file WHERE fid=%d" % fid)  #TODO image and image_file tables are empty
	db.query("DELETE FROM mirror_file WHERE fid=%d" % fid)
	db.query("DELETE FROM sf_sync WHERE fid=%d" % fid)
	db.query("DELETE FROM sf_sync2 WHERE fid=%d" % fid)
	db.query("DELETE FROM tag WHERE fid=%d" % fid)
	db.query("DELETE FROM file WHERE fid=%d" % fid)


def CheckDeleteFile(filePath):
	if os.path.isfile(filePath):
		logging.info("File %s exists: deleting..." % filePath)
		os.remove(filePath)
	else:
		logging.info("File %s not found." % filePath)


def GetItemDetails(fid):
	rows = db.query("SELECT fid,uid,filename,timestamp,f.name,c.name AS category,path FROM file f INNER JOIN categories c ON (f.cid=c.cid) WHERE f.fid=%d" % fid)
	result = rows.first()
	if result is None:
		return False
	return dict(result)


def DeleteItem(fid,d):
	if (not d):
		logging.info("no file found for fid=%d" % fid)
		return False,"ERROR : File not found"
	
	logging.info("user fid=%d filename=%s category=%s" % (d["fid"],d["filename"],d["category"]))
	if d["category"] == "map":
		# check referenced image files
		fileRes = db.query("SELECT SUBSTRING_INDEX(SUBSTRING_INDEX(metadata,'\"mapimages\": [',-1),']',1) AS imgStr FROM file WHERE fid=%d" % fid)
		fileRes = fileRes.first()
		if (fileRes is not None):
			imgListStr = fileRes[0]
			imgListStr = re.sub('[" ]','',imgListStr)
			#logging.info("imgStr=%s" % imgListStr)
			imgList = imgListStr.split(",")
			for i,imgFile in enumerate(imgList):
				# check if each image file is safe to delete
				# image file names follow a <MD5_OF_BYTES>.jpg convention so each may be referenced by many maps
				useCount = 0
				useRes = db.query("SELECT COUNT(DISTINCT fid) AS useCount FROM file WHERE metadata LIKE '%%%s%%'" % imgFile)
				useRes = useRes.first()
				if (useRes is not None):
					useCount = useRes[0]
					if useCount > 1:
						logging.info("image %s is still necessary (%d files): removal aborted" % (imgFile,useCount))
						continue
				imgFilePath = MAP_IMAGE_PATH+"/"+imgFile 
				CheckDeleteFile(imgFilePath)
		# check the original file
		oFile = d["filename"]
		oFilePath = MAP_PATH + "/" + oFile
		DeleteAssociatedRecords(fid)
		CheckDeleteFile(oFilePath)
	elif d["category"] == "game":
		oFile = d["filename"]
		oFilePath = GAME_PATH + "/" + oFile
		DeleteAssociatedRecords(fid)
		CheckDeleteFile(oFilePath)
	else:
		logging.info("file %d not a game or map : skip" % fid)
		return False,("File %d not a game or map" % fid)
	
	return True,("File %s and associated records removed successfully" % (d["filename"]))


def HandleForm(fid,d,form):
	if not CheckFields(form, ["username", "password"]):
		return False,"ERROR : Missing formdata"
	username = form.getvalue("username")
	password = form.getvalue("password")
	accountId = CheckAuth(username, password)
	if not accountId or accountId == 0:
		return False,"ERROR : Invalid Username or Password"
	if not fid:
		return False,"ERROR : Invalid file ID"
	if (accountId != d["uid"]):
		return False,"ERROR : User attempting deletion (%d) does not match uploader (%d)" % (accountId,d["uid"])
	logging.info("DELETING fid=%d filename=%s accountid=%d category=%s" % (d["fid"],d["filename"],d["uid"],d["category"]))
	status,output = DeleteItem(fid,d)
	return status,output

print("Content-type: text/html\n")
cgitb.enable()

form = cgi.FieldStorage()

# check referenced file
fid = 0
if "fid" in form:
	fid = form.getvalue("fid")
	fid = int(fid)
fileInfo = "File not found. Nothing to do here..."
msgs = ""
onload = ""
d = GetItemDetails(fid)
if (not d):
	logging.info("no file found for fid=%d" % fid)
	onload = "disableForm()"
else:
	fileInfo = """
	<span class="label">Name:</span> %s<br>
	<span class="label">Modified:</span> %s<br>
	<span class="label">Category:</span> <span class=\"category\">%s</span><br>
	<span class="label">Filename:</span> %s<br>
	""" % (d["name"],d["timestamp"],d["category"].upper(),d["filename"])
	if ("not available as sdz" in d["filename"]):
		onload = "disableForm()"
	elif os.environ['REQUEST_METHOD'] == 'POST':
		status,msgs = HandleForm(fid,d,form)
		if status == True:
			onload = "disableForm()"

ShowForm({"messages": "<pre>" + html.escape(msgs) + "</pre>","fileInfo": fileInfo,"onload": onload})

