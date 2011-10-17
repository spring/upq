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
	echo $msg;
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
	xmlrpc_server($callbacks);

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
	global $config;
	$file=$config['torrentpath'].$filename.".torrent";
	if (is_readable($file)){
		$res = new stdClass();
		$res->is_base64=true;
		$res->data=base64_encode(file_get_contents($file));
		return $res;
	}
	watchdog("file_mirror", "no torrent info for $file");
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
	if (!is_array($req))
		return "Invalid request";
	global $base_url;
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
		_file_mirror_createquery($query,$vars, $logical,"CONCAT(a.name,' ',a.version) LIKE BINARY '%s' OR a.name LIKE BINARY '%s'", array($req['springname'],$req['springname']));
	if($query!="")
		$query=" AND (".$query.")";
	$result=db_query("SELECT
		distinct(f.fid) as fid,
		f.filename as filename,
		f.filepath as filepath,
		h.md5 as md5,
		a.name as name,
		a.version as version,
		LOWER(c.name) as category,
		f.filesize as size,
		f.timestamp as timestamp,
		a.sdp as sdp
		FROM files as f
		LEFT JOIN springdata_archives as a ON f.fid=a.fid
		LEFT JOIN springdata_categories as c ON a.cid=c.cid
		LEFT JOIN filehash as h ON f.fid=h.fid
		LEFT JOIN springdata_archivetags as t ON t.fid=f.fid
		WHERE c.cid>0
		$query
		ORDER BY f.fid DESC
		LIMIT 0,10
		",
		$vars
	);
	$res=array();
	while($row = db_fetch_array($result)){
		//add primary server
		$row['mirrors']=array($base_url.'/'.$row['filepath']);
		unset($row['filepath']);
		$res[]=$row;
	}

	for($i=0;$i<count($res);$i++){
		//search + add depends to file
		$result=db_query("SELECT CONCAT(archives.name,' ',archives.version) as springname, depends_string
			FROM {springdata_depends} AS depends
			LEFT JOIN {springdata_archives} AS archives ON depends.depends=archives.fid
			WHERE depends.fid=%d",$res[$i]['fid']);
		while($row = db_fetch_array($result)){
			if(!is_array($res[$i]['depends']))
				$res[$i]['depends']=array();
			if(strlen($row['springname'])<=0) // 0 means it wasn't resolveable, return the string
				$res[$i]['depends'][]=$row['depends_string'];
			else{ //is resolveable, return string from archive
				$res[$i]['depends'][]=$row['springname'];
			}
		}
		//search + add additional mirrors to file
		$result=db_query('SELECT CONCAT(mirror.url_prefix,"/",files.path) as url
			FROM file_mirror_files as files
			LEFT JOIN file_mirror as mirror ON files.fmid=mirror.fmid
			WHERE files.fid=%d
			AND mirror.active=1
			AND files.active=1
			ORDER BY files.md5check',array($res[$i]['fid']));
		while($row = db_fetch_array($result)){
			$res[$i]['mirrors'][]=$row['url'];
		}
		//add tags
		$res[$i]['tags']=array();
		$result=db_query('SELECT tag FROM {springdata_archivetags}
			WHERE fid=%d', array($res[$i]['fid']));
		while($row = db_fetch_array($result)){
			$res[$i]['tags'][]=$row['tag'];
		}
		if(array_key_exists('torrent', $req)){
			$res[$i]['torrent']=_file_mirror_gettorrent($res[$i]['filename']);
			if (!is_object($res[$i]['torrent'])){
				unset($res[$i]['torrent']);
			}
		}
		$res[$i]['description']=_file_mirror_getlink($res[$i]['fid']);
//		if (count($res[$i]['mirrors'])>2) //remove main mirror to reduce load if enough alternatives are available
//			array_shift($res[$i]['mirrors']);
		//randomize order of result
		shuffle($res[$i]['mirrors']);
		unset($res[$i]['fid']);
		if ($res[$i]['version']=="")
			$res[$i]['springname']=$res[$i]['name'];
		else
			$res[$i]['springname']=$res[$i]['name']." ".$res[$i]['version'];
	}
	$count=count($res);
	if ($count<>1)
		watchdog("error in request: ", $req);
	return $res;
}

function file_mirror_uploadfile($req){
	watchdog("filemirror", "upload request: ".$req['url']);
	$params = array( 'name' => $req['username'],
			'pass' => $req['password']);
	$user=user_authenticate($params);
	if (!is_object($user))
		return "Invalid username/password";
	$filename=$req['filename'];
	$sdp=$req['sdp']; # optional
	$tag=$req['tag']; # optional
	$url=$req['url'];
	$uid=$user->uid;
	$res=_file_mirror_run_upq("download url:$url sdp:$sdp filename:$filename uid:$uid");

	return $res;
}
