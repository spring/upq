<html>
<body>
<table>
Input is case sensitive! Use * (multiple chars) or ? (single char) as wildcard. 10 Results are returned at max.
<form action="<?php echo $_SERVER["REQUEST_URI"] ?>" method="get">

<?php
	foreach (array('springname', 'filename', 'tag', 'sdp') as $val) {
	?>
	<tr>
		<tr><td><?php echo $val; ?>:</td>
		<td><input type="text" name="<?php echo $val; ?>" value="<?php if (array_key_exists($val, $_REQUEST)) echo htmlentities($_REQUEST[$val]); ?>"></td>
	</tr>
<?
	}
	foreach (array('images', 'metadata', 'nosensitive') as $val){
?>
	<tr>
		<td><?php echo $val; ?></td>
		<td><input type="checkbox" name="<?php echo $val; ?>" <?php if (array_key_exists($val, $_REQUEST)) echo 'checked'; ?>></td>
	</tr>
<?
	}
?>
	<tr>
	<td colspan="2" align="center"><input type="submit"></td>
	</tr>
</form>
</table>

<?php
require("config.php");
require("include/drupal_dummy.inc");
require("include/search.inc");

/**
 *	format a result to a human readable output
 **/
function dump_result($res, $rec=0){
	$space="";
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

$res=search($_REQUEST);
echo "<pre>";
echo dump_result($res);
echo "</pre>";
?>
</body>
</html>
