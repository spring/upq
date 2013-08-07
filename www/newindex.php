<?php
//get the q parameter from URL
$q=$_GET["q"];

//lookup all links from the xml file if length of q>0
if (strlen($q)<=0)
	return;
require("config.php");
require("include/drupal_dummy.inc");
require("include/search.inc");

function image($url, $alt){
      return sprintf('<img src="%s"/>'."\n", $url);
}

function httplink($url, $alt){
      return sprintf('<a href="%s">%s</a>'."\n", $url, $alt);
}

function br(){
	return "<br/>\n";
}

function dump_result($results){
	$res = "";
	foreach($results as $arr) {
		$springname = "unknown";
		if (array_key_exists("springname", $arr))
			$springname=$arr["springname"];
		if (array_key_exists("mirrors", $arr)) {
			$i=1;
			foreach($arr["mirrors"] as $link) {
				$res.=httplink($link, $springname." mirror $i");
				$i++;
			}
			$res.=br();
		}
		if (array_key_exists("splash", $arr)) {
			if(count($arr["splash"])>0) {
				$res.=image($arr["splash"][0], $springname);
				$res.=br();
			}
		}
		if (array_key_exists("mapimages", $arr)) {
			if(count($arr["mapimages"])>0) {
				$res.=image($arr["mapimages"][0],$springname);
				$res.=br();
			}
		}
		if (array_key_exists("tags", $arr)) {
			foreach($arr["tags"] as $link) {
				$res.=$link;
				$res.=br();
			}
		}
	}
	return $res;
}


function _search($q) {
	$REQ = array(
		"springname" => $q,
		"filename" => $q,
		"tag" => $q,
		"nosensitive" => "true",
		"logical" => "or",
		"limit" => "3",
		"images" => "true",
	);
	return search($REQ);
}

$arr=_search($q);
if(count($arr)<=0){
	$arr=_search("$q*");
	if(count($arr)<=0){
		$arr=_search("*$q*");
	}
}

echo dump_result($arr);
