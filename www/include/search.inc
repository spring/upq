<?php

/**
* @param query resulting query, for example "AND filename='%s'"
* @param vars data for query, for example "Zero-K v0.51"
* @param logical how the queries are assigned, AND/OR
* @param condition SQL condition, for example "LIKE filename '%s'" or "filename='%s'"
* @param request the request array
* @param values values that are used from the request array (i.e.  $request[$values[0]], $request[$values[1], ...])
*/

function _file_mirror_createquery(&$query, &$vars, $logical,$condition, $request, $values=array()){
	$data=array();
	foreach($values as $val){ //if values are fine, push into data array
		if (!array_key_exists($val, $request)) //check if key exists in request
			return;
		if (strlen($request[$val])<=0) //empty values are ignored
			return;
		array_push($data, $request[$val]);
	}

	if($query=="") $logical="";

	$query.=" ".$logical." ".$condition;
	$data=str_replace(array("_", "?", "*"),array("\_", "_", "%"),$data); // escape _ as it is a wildcard in sql
	foreach($data as $val) //append values to vars (will be used to replace %s/%d in mysql query)
		array_push($vars, $val);
}

function _file_mirror_gettorrent($filename){
	if (is_readable($filename)){
		return file_get_contents($filename);
	}
	watchdog("file_mirror", "no torrent info for $filename");
	return "";
}

/**
* return images
*/
function _get_metadata($row){
	$meta=json_decode($row, true);
	if (is_array($meta))
		return $meta;
	return array();
}

function _add_metadata_path($arr){
	global $config;
	$res=array();
	foreach ($arr as $val){
		$res[] = $config['metadata'].'/'.$val;
	}
	return $res;
	
}

/**
*	implementation of the xml-rpc call
*/

function search($req){
	global $config;
	if (!is_array($req))
		return "Invalid request";
	$res="";
	$category="%";
	$query="";
	$vars=array();

	if(isset($req['logical'])&&($req['logical']=="or")){
		$logical="OR";
	}else{
		$logical="AND";
	}
	if(isset($req['nosensitive'])) //default to case-sensitive search
		$BINARY="";
	else
		$BINARY="BINARY";
	_file_mirror_createquery($query,$vars, $logical,"t.tag LIKE $BINARY '%s'", $req, array('tag'));
	_file_mirror_createquery($query,$vars, $logical,"f.filename LIKE $BINARY '%s'", $req, array('filename'));
	_file_mirror_createquery($query,$vars, $logical,"c.name LIKE $BINARY '%s'", $req, array('category'));
	_file_mirror_createquery($query,$vars, $logical,"f.name LIKE $BINARY '%s'", $req, array('name'));
	_file_mirror_createquery($query,$vars, $logical,"f.version LIKE $BINARY '%s'", $req, array('version'));
	_file_mirror_createquery($query,$vars, $logical,"f.sdp LIKE $BINARY '%s'", $req, array('sdp'));
	_file_mirror_createquery($query,$vars, $logical,"( CONCAT(f.name,' ',f.version) LIKE $BINARY '%s' OR f.name LIKE $BINARY '%s' )",$req,  array('springname','springname'));
	if($query!="")
		$query=" AND (".$query.")";
	$result=db_query("SELECT
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
		f.descriptionuri as description,
		f.metadata as metadata
		FROM file as f
		LEFT JOIN categories as c ON f.cid=c.cid
		LEFT JOIN mirror_file as m ON f.fid=m.fid
		LEFT JOIN tag as t ON  f.fid=t.fid
		WHERE c.cid>0
		AND f.status=1
		$query
		ORDER BY f.timestamp DESC
		LIMIT 0,10
		",
		$vars
	);
	$res=array();
	while($row = db_fetch_array($result)){
		$row['mirrors']=array($config['base_url'].'/'.$row['path'].'/'.$row['filename']);
		$res[]=$row;
	}


	for($i=0;$i<count($res);$i++){
		//search + add depends to file
		$result=db_query("SELECT CONCAT(a.name,' ',a.version) as springname, depends_string
			FROM {file_depends} AS d
			LEFT JOIN {file} AS a ON d.depends_fid=a.fid
			WHERE d.fid=%d",$res[$i]['fid']);
		while($row = db_fetch_array($result)){
			if(!is_array($res[$i]['depends']))
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
			AND m.status=1
			AND mf.status=1',array($res[$i]['fid']));
		while($row = db_fetch_array($result)){
			$res[$i]['mirrors'][]=$row['url'];
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
		$torrent_file='metadata/'.$res[$i]['sdp'].'.torrent';
		if(array_key_exists('torrent', $req) && file_exists($torrent_file)){
			$res[$i]['torrent']=_file_mirror_gettorrent($torrent_file);
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
		unset($res[$i]['torrent_file']);
		ksort($res[$i]);
	}
	return $res;
}
