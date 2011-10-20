<?php
require("include/xmlrpc.inc");
require("include/xmlrpcs.inc");
require("include/drupal_dummy.inc");
require("config.php");

//this script requires >= php 5.25

$callbacks = array(
	"springfiles.search" => "file_mirror_xmlsearch",
);

if(!mysql_connect($config['db_host'], $config['db_user'], $config['db_pass']))
	die("mysql error: ".mysql_error());

if(!mysql_select_db($config['db_db']))
	die("mysql error: ".mysql_error());

function db_fetch_array($result){
	if ($result)
		return mysql_fetch_array($result, MYSQL_ASSOC);
}
function watchdog($msg, $arr=array()){
	return;
	if (sizeof($arr)>0)
		print_r($arr);
	echo "\n";
}

function main($argv){
	$req=array("springname"=>"%");
	$res=file_mirror_xmlsearch($req);
	$r=xmlrpc_value($res);
	echo '<methodResponse>
 <params>
  <param>
  <value>'.
     xmlrpc_value_get_xml($r)
    ."</value>
  </param>
</params>
</methodResponse>\n";
}

if (array_key_exists('argv', $_SERVER))
	main($_SERVER['argv']);
else
	if ($_SERVER['REQUEST_METHOD']=="POST"){
		xmlrpc_server($callbacks);
	} else {
		echo file_get_contents("readme.html");
		return;
	}

/**
* @param query resulting query, for example "AND filename='%s'"
* @param vars data for query, for example "Zero-K v0.51"
* @param logical how the queries are assigned, AND/OR
* @param condition SQL condition, for example "LIKE filename '%s'" or "filename='%s'"
* @param data data from the xml-rpc request, if empty string, then don't change query + vars
*/

function _file_mirror_createquery(&$query, &$vars, $logical,$condition, $data){
	if($query=="") $logical="";

	if($data=="")
		return;
	$query.=" ".$logical." ".$condition;
	$data=str_replace("_","\_",$data);
	if (is_array($data)){
		foreach($data as $val)
			array_push($vars, $val);
	}else
		array_push($vars, $data);
}

function _file_mirror_gettorrent($filename){
	if (is_readable($filename)){
		$res = new stdClass();
		$res->is_base64=true;
		$res->is_date=false;
		$res->data=file_get_contents($filename);
		return $res;
	}
	watchdog("file_mirror", "no torrent info for $filename");
	return "";
}

function _file_mirror_getlink($fid){
	//TODO: xmlrpc call
	/*
	$res=db_query("SELECT nid FROM {content_field_file} as c WHERE field_file_fid=%d
", array($fid));
	$nid=db_result($res);
	if ($nid<=0)
		return "";
	$res=db_query("SELECT dst FROM {url_alias} WHERE src='%s'",array("node/$nid"));
	$url=db_result($res);
	if (strlen($url)>0)
		return "http://springfiles.com/$url";
	return "http://springfiles.com/node/$nid";
	*/
}

/**
*	implementation of the xml-rpc call
*/

function file_mirror_xmlsearch($req){
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
	if (array_key_exists('tag', $req))
		_file_mirror_createquery($query,$vars, $logical,'t.tag LIKE BINARY "%s"', $req['tag']);
	if (array_key_exists('filename', $req))
		_file_mirror_createquery($query,$vars, $logical,'f.filename LIKE BINARY "%s"', $req['filename']);
	if (array_key_exists('category', $req))
		_file_mirror_createquery($query,$vars, $logical,'c.name LIKE BINARY "%s"', $req['category']);
	if (array_key_exists('springname', $req))
		_file_mirror_createquery($query,$vars, $logical,"CONCAT(f.name,' ',f.version) LIKE BINARY '%s' OR f.name LIKE BINARY '%s'", array($req['springname'],$req['springname']));
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
		f.torrent as torrent_file
		FROM file as f
		LEFT JOIN categories as c ON f.cid=c.cid
		LEFT JOIN mirror_file as m ON f.fid=m.fid
		LEFT JOIN tag_file as tf ON tf.fid=f.fid
		LEFT JOIN tag as t ON  tf.tid=t.tid
		WHERE c.cid>0
		$query
		ORDER BY f.fid DESC
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
		$result=db_query('SELECT CONCAT(m.url_prefix,"/",f.path) as url
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
		$result=db_query('SELECT tag FROM {tag_file} f
			LEFT JOIN tag t ON t.tid=f.tid
			WHERE fid=%d', array($res[$i]['fid']));
		while($row = db_fetch_array($result)){
			$res[$i]['tags'][]=$row['tag'];
		}
		if(array_key_exists('torrent', $req) && (strlen($res[$i]['torrent_file'])>0)){
			$res[$i]['torrent']=_file_mirror_gettorrent($config['metadata'].'/'.$res[$i]['torrent_file']);
		}
		$res[$i]['size']=intval($res[$i]['size']);
		$res[$i]['description']=_file_mirror_getlink($res[$i]['fid']);
		if ($res[$i]['version']=="")
			$res[$i]['springname']=$res[$i]['name'];
		else
			$res[$i]['springname']=$res[$i]['name']." ".$res[$i]['version'];
		$res[$i]['timestamp']=xmlrpc_date($res[$i]['timestamp']);
		unset($res[$i]['fid']);
		unset($res[$i]['path']);
		unset($res[$i]['torrent_file']);
	}
	$count=count($res);
	if ($count<>1)
		watchdog("error in request: ", $req);
	return $res;
}


