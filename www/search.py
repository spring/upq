#!/usr/bin/python3

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


from lib import upqdb, upqconfig
import json
import random
import cgi

def getlimit(request):
	offset = 0
	limit = 10
	if "offset" in request:
		offset = int(request["offset"])
	if "limit" in request:
		limit = min(64, int(request["limit"]))
	return "LIMIT %d, %d" %(offset, limit)

def GetQuery(request, binary, tag, cond):
	if not tag in request:
		return []
	params = {
		"binary": binary,
		tag : upqdb.escape(request[tag].replace("*", "%"))
	}
	#print(params)
	return [cond.format(**params)]


def GetMirrors(db, fid):
	rows = db.query("""SELECT CONCAT(m.url_prefix,"/",mf.path) as url
		FROM mirror_file as mf
		LEFT JOIN mirror as m ON mf.mid=m.mid
		LEFT JOIN file as f ON f.fid=mf.fid
		WHERE f.fid=%d
		AND (m.status=1 or m.status=2)
		AND mf.status=1""" % fid);

	res = []
	for row in rows:
		res.append(row[0])
	random.shuffle(res)
	return res

def GetMetadataPaths(images):
	res = []
	for image in images:
		res.append("https://springfiles.springrts.com/metadata/"  + image)
	return res

def GetTags(db, fid):
	rows = db.query('SELECT tag FROM tag WHERE fid=%d' % fid)
	res = []
	for row in rows:
		res.append(row[0])
	return res

def GetResult(request):
	cfg = upqconfig.UpqConfig()
	db = upqdb.UpqDB(cfg.db['url'], cfg.db['debug'])
	wherecond = ""

	if "logical" in request and request["logical"] == "or":
		logical = " OR "
	else:
		logical = " AND "

	if "nosensitive" in request:
		binary=""
	else:
		binary="BINARY"

	conditions = {
		"tag": "t.tag LIKE {binary} '{tag}'",
		"filename": "f.filename LIKE {binary} '{filename}'",
		"category": "c.name LIKE {binary} '{category}'",
		"name": "f.name LIKE {binary} '{name}'",
		"version": "f.version LIKE {binary}'{version}'",
		"sdp": "f.sdp LIKE {binary} '{sdp}'",
		# FIXME: concat is really slow!
		"springname": "((f.name LIKE {binary} '{springname}' OR f.version LIKE {binary} '{springname}') OR (CONCAT(f.name,' ',f.version) LIKE {binary} '{springname}'))",
		"md5": "f.md5 = '{md5}'",
	}

	wheres = []
	for tag, condition in conditions.items():
		wheres += GetQuery(request, binary, tag, condition)

	wherecond = logical.join(wheres)
	if wherecond:
		wherecond = " AND " + wherecond


	#print(wherecond)
	rows = db.query("""SELECT
	distinct(f.fid) as fid,
	f.name as name,
	f.filename as filename,
	f.path as path,
	f.md5 as md5,
	f.sdp as sdp,
	f.version as version,
	LOWER(c.name) as category,
	f.size as size,
	f.timestamp as timestamp,
	f.metadata as metadata
	FROM file as f
	LEFT JOIN categories as c ON f.cid=c.cid
	LEFT JOIN tag as t ON  f.fid=t.fid
	WHERE c.cid>0
	AND f.status=1
	%s
	ORDER BY f.timestamp DESC
	%s
	"""%(wherecond, getlimit(request)))

	clientres = []
	for row in rows:
		d = dict(row)
		#inject local file as mirror
		if d["category"] in ["game", "map"]:
			d["mirrors"] = ["https://springfiles.springrts.com/files/" + d["path"] + "/" + d["filename"]]
		else:
			d["mirrors"] = []

		d["mirrors"] += GetMirrors(db, d["fid"])
		#print(mirrors)
		#print(row)

		try:
			d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
		except json.decoder.JSONDecodeError:
			d["metadata"] = ""
		if "images" in request:
			for k in ["splash", "mapimages"]:
				if k in d["metadata"]:
					d[k] = GetMetadataPaths(d["metadata"][k])
					del(d["metadata"][k])

		if not "metadata" in request:
			del(d["metadata"])

		#if "splash" in request:
		#if "images" in request:

		#json.dumps(row)
		d["tags"] = GetTags(db, d["fid"])
		del(d["fid"])
		if d["timestamp"]:
			d["timestamp"] = d["timestamp"].isoformat()

		if d["version"] == "":
			d["springname"] = d["name"]
		else:
			d["springname"] = d["name"] + " " + d["version"]


		clientres.append(d)

	return clientres

request = {}
#request={'_': '1630833475755', 'callback': 'processData', 'images': 'on', 'nosensitive': 'on', 'springname': '*'}

#request = {"md5": "311d2bc8fd1bdb092b7d1f162da5fc44"}

for k,v in cgi.parse().items():
	if isinstance(v, list):
		request[k] = v[0]
	else:
		request[k] = v

result = GetResult(request)

if "callback" in request:
	# strip anything except a-Z0-9
	print("Content-type: application/javascript\n")
	cb = upqdb.escape(request["callback"], set("abcdefhijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"));
	print( cb + "(" +  json.dumps(result) + ");")
else:
	print("Content-type: application/json\n")
	print(json.dumps(result))

