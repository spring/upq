from lib import upqdb, upqconfig

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
	print(params)
	return [cond.format(**params)]


wheres = []
wheres += GetQuery(request, binary, "tag", "t.tag LIKE {binary} '{tag}'")
wheres += GetQuery(request, binary, "filename", "f.filename LIKE {binary} '{filename}'")
wheres += GetQuery(request, binary, "category", "c.name LIKE {binary} '{category}'")
wheres += GetQuery(request, binary, "name", "f.name LIKE {binary} '{name}'");

wheres += GetQuery(request, binary, "version", "f.version LIKE {binary}'{version}'")
wheres += GetQuery(request, binary, "sdp", "f.sdp LIKE {binary} '{sdp}'")
wheres += GetQuery(request, binary, "springname", "( (CONCAT(f.name,' ',f.version) LIKE {binary} '{springname}') OR (f.name LIKE {binary} '{springname}' OR f.version LIKE {binary} '{springname}') )")
wheres += GetQuery(request, binary, "md5", "f.md5 = '{md5}'")


wherecond = logical.join(wheres)
if wherecond:
	wherecond = " AND " + wherecond

print(wherecond)

res = db.query("""SELECT
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


for row in res:
	print(row)

"""
/**
* return images
*/
function _get_metadata($row){
	$meta=json_decode($row, true);
	if (is_array($meta))
		return $meta;
	return array();
}

$https=(!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || (!empty($_SERVER['SERVER_PORT']) && $_SERVER['SERVER_PORT'] == 443);
function TransformUrl($url)
{
	global $https;
	if ($https) {
		return str_replace("http://", "https://", $url);
	}
	return $url;
}

function _add_metadata_path($arr){
	global $config;
	$res=array();
	foreach ($arr as $val){
		$res[] = TransformUrl($config['metadata'].'/'.$val);
	}
	return $res;
	
}

/**
*	implementation of the xml-rpc call
*/
function search($req){
	$res=array();
	while($row = db_fetch_array($result)){
		#inject local file as mirror
		if (($row['category'] == "game") or ($row['category'] == "map")) {
			$row['mirrors']=TransformUrl(array($config['base_url'].'/'.$row['path'].'/'.$row['filename']));
		} else {
			$row['mirrors']=array();
		}
		$res[]=$row;
	}


	for($i=0;$i<count($res);$i++){
		//search + add depends to file
		$result=db_query("SELECT CONCAT(a.name,' ',a.version) as springname, depends_string
			FROM {file_depends} AS d
			LEFT JOIN {file} AS a ON d.depends_fid=a.fid
			WHERE d.fid=%d",$res[$i]['fid']);
		while($row = db_fetch_array($result)){
			if(!array_key_exists('depends', $res[$i]))
				$res[$i]['depends']=array();
			if(strlen($row['springname'])<=0) // 0 means it wasn't resolveable, return the string
				$res[$i]['depends'][]=$row['depends_string'];
			else{ //is resolveable, return string from archive
				$res[$i]['depends'][]=$row['springname'];
			}
		}
		//search + add mirrors to file
		$result=db_query('SELECT CONCAT(m.url_prefix,"/",mf.path) as url
			FROM mirror_file as mf
			LEFT JOIN mirror as m ON mf.mid=m.mid
			LEFT JOIN file as f ON f.fid=mf.fid
			WHERE f.fid=%d
			AND (m.status=1 or m.status=2)
			AND mf.status=1',array($res[$i]['fid']));
		while($row = db_fetch_array($result)){
			$res[$i]['mirrors'][]=TransformUrl($row['url']);
		}
		//randomize order of result
		shuffle($res[$i]['mirrors']);

		//add tags
		$res[$i]['tags']=array();
		$result=db_query('SELECT tag FROM {tag} t
			WHERE fid=%d', array($res[$i]['fid']));
		while($row = db_fetch_array($result)){
			$res[$i]['tags'][]=$row['tag'];
		}
		$metadata=_get_metadata($res[$i]['metadata']);
		if (array_key_exists('images', $req)){
			if (array_key_exists('splash', $metadata))
				$res[$i]['splash'] = _add_metadata_path($metadata['splash']);
			if (array_key_exists('mapimages', $metadata))
				$res[$i]['mapimages'] = _add_metadata_path($metadata['mapimages']);
		}			
		unset($metadata['splash']);
		unset($metadata['mapimages']);
		//links to metadata
		if(array_key_exists('metadata', $req)){
			$res[$i]['metadata']=$metadata;
		}else{
			unset($res[$i]['metadata']);
		}

		//additional metadata
		$res[$i]['size']=intval($res[$i]['size']);
		if ($res[$i]['version']=="")
			$res[$i]['springname']=$res[$i]['name'];
		else
			$res[$i]['springname']=$res[$i]['name']." ".$res[$i]['version'];
		unset($res[$i]['fid']);
		unset($res[$i]['path']);
		ksort($res[$i]);
	}
	return $res;
}
"""
