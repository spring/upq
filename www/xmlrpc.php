<?php

require("config.php");
require("include/xmlrpc.inc");
require("include/xmlrpcs.inc");
require("include/drupal_dummy.inc");
require("include/search.inc");
require("include/upq.inc");

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
	}
	return $res;
}

function xmlrpc_upload($req){
	if (!(array_key_exists('url', $req))){
		return "Error: Url not set in request!";
	}
	//FIXME: authentification!
	return upq_run("download url:".$req['url']);
}


function main($argv){
	$req=array(
		"springname"=>"%",
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

