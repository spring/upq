<?php

require("config.php");
require("include/xmlrpc.inc");
require("include/xmlrpcs.inc");
require("include/drupal_dummy.inc");
require("include/search.inc");

//this script requires >= php 5.25

function xmlrpc_tobase64($str){
	$res = new stdClass();
	$res->is_base64=true;
	$res->is_date=false;
	$res->data=$str;
	return $res;
}

function xmlrpc_search($req){
	$res=search($req);
	for($i=0; $i<count($res); $i++){
		$res[$i]['timestamp']=xmlrpc_date($res[$i]['timestamp']);
		if(array_key_exists('torrent', $res[$i])){
			$res[$i]['torrent']=xmlrpc_tobase64($res[$i]['torrent']);
		}
	}
	return $res;
}

/**
* notify cron job about changes
*/
function _run_upq($job){
        $timeout=5;
        $sock = @stream_socket_client('unix:///tmp/.upq-incoming.sock', $errno, $errstr, $timeout);
        if($sock===FALSE){
                watchdog("filemirror", "error connecting to upq socket $errstr $fid");
                return;
        }
        stream_set_timeout($sock, $timeout);
        fwrite($sock, "$job\n");
        $res=fgets($sock);
        fclose($sock);
        watchdog("filemirror", "result from upq: $res");
        return $res;
}


function xmlrpc_upload($req){
	if (!(array_has_key('url', $req))){
		return "Error: Url not set in request!";
	}
	//FIXME: authentification!
	$url=urlencode($req['url']);
	return _run_upq("upload url:$url");
}


function main($argv){
	$req=array(
		"springname"=>"%",
		"torrent"=>"true",
	);
	$res=xmlrpc_search($req);
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

if (array_key_exists('argv', $_SERVER)) {
	main($_SERVER['argv']);
} else {
	if ($_SERVER['REQUEST_METHOD']=="POST"){
		$callbacks = array(
			"springfiles.search" => "xmlrpc_search",
			"springfiles.upload" => "xmlrpc_upload",
		);
		xmlrpc_server($callbacks);
	} else {
		echo file_get_contents("readme.html");
		return;
	}
}

