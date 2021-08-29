from lib import upqdb, upqconfig
import json
import random

cfg = upqconfig.UpqConfig()
cfg.readConfig()
db = upqdb.UpqDB()
db.connect(cfg.db['url'], cfg.db['debug'])

wherecond = ""

def getlimit(request):
	offset = 0
	limit = 10
	if "offset" in request:
		offset = int(request["offset"])
	if "limit" in request:
		limit = min(64, int(request["limit"]))
	return "LIMIT %d, %d" %(offset, limit)


def sqlescape(string):
	#FIXME!!!!!
	return string

request = {
	#"offset": "10",
	#"limit": "3",
	#"nosensitive": "",
	#"logical": "or",
	"springname": "DeltaSiegeDry",
}

if "logical" in request and request["logical"] == "or":
	logical = " OR "
else:
	logical = " AND "

if "nosensitive" in request:
	binary=""
else:
	binary="BINARY"

def GetQuery(request, binary, tag, cond):
	if not tag in request:
		return []
	params = {
		"binary": binary,
		tag : sqlescape(request[tag])
	}
	#print(params)
	return [cond.format(**params)]

conditions = {
	"tag": "t.tag LIKE {binary} '{tag}'",
	"filename": "f.filename LIKE {binary} '{filename}'",
	"category": "c.name LIKE {binary} '{category}'",
	"name": "f.name LIKE {binary} '{name}'",
	"version": "f.version LIKE {binary}'{version}'",
	"sdp": "f.sdp LIKE {binary} '{sdp}'",
	"springname": "( (CONCAT(f.name,' ',f.version) LIKE {binary} '{springname}') OR (f.name LIKE {binary} '{springname}' OR f.version LIKE {binary} '{springname}') )",
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


clientres = []

for row in rows:
	d = dict(row)
	#inject local file as mirror
	if d["category"] in ["game", "map"]:
		d["mirrors"] = ["https://springfiles.springrts.com/" + d["path"] + d["filename"]]
	else:
		d["mirrors"] = []

	d["mirrors"] += GetMirrors(db, d["fid"])
	#print(mirrors)
	#print(row)

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
	del(d["fid"])
	d["timestamp"] = d["timestamp"].isoformat()
	clientres.append(d)

json.dumps(clientres)
