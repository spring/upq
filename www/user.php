<html>
<body>
<table>
<form>
	<tr>
		<tr><td>Springname:</td>
		<td><input type="text" name="springname" value="<?php if (array_key_exists('springname', $_REQUEST)) echo $_REQUEST['springname']; ?>"></td>
	</tr>
	<tr>
		<td>Filename:</td>
		<td><input type="text" name="filename" value="<?php if (array_key_exists('filename', $_REQUEST)) echo $_REQUEST['filename']; ?>"></td>
	</tr>
	<tr>
	<td colspan="2" align="center"><input type="submit"></td>
	</tr>
</form>
</table>

<?php
require("config.php");
require("include/drupal_dummy.inc");
require("include/search.inc");

function json_search($req){
	$res=search($req);
	for($i=0; $i<count($res); $i++){
		if(array_key_exists('torrent', $res[$i])){
			$res[$i]['torrent']=base64_encode($res[$i]['torrent']);
		}
	}
	return $res;
}

function main($argv){
	$req=array(
		"springname"=>"%",
		"torrent"=>"true"
	);
	$res=json_search($req);
	echo json_encode($res);
}

if (array_key_exists('argv', $_SERVER))
	main($_SERVER['argv']);
else if ($_SERVER['REQUEST_METHOD']=="GET"){
	$res=json_search($_REQUEST);
} else {
	echo file_get_contents("readme.html");
}
/**
 *	format a result to a human readable output
 **/
function dump_result($res, $rec=0){
	$space="\t";
	for($i=0;$i<$rec; $i++)
		$space=$space."\t";
	if (is_array($res)){
		$ret="\n";
		$rec++;
		while(list($name, $value)=each($res)){
			$ret.=$space.$name.':'. dump_result($value, $rec);
		}
		return "$ret";
	}else{
		if (strlen($res)<=0)
			return "\n";
		if (!(strpos($res,"http://")===false))
			return sprintf('<a href="%s">%s</a>'."\n", $res, $res);
		return "$res\n";
	}
}

echo "<pre>";
echo dump_result($res);
echo "</pre>";
?>
</body>
</html>
