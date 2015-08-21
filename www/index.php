<?php
require("config.php");
require("include/drupal_dummy.inc");
require("include/search.inc");
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"> 
<head>
	<title></title>
	<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
</head>
<body>
Input is case sensitive! Use * (multiple chars) or ? (single char) as wildcard. 10 Results are returned at max.
<form action="<?php echo $_SERVER["REQUEST_URI"] ?>" method="get">
<table>

<?php
	foreach (array('springname', 'filename', 'tag', 'sdp') as $val) {
	?>
	<tr>
		<td><?php echo $val; ?>:</td>
		<td><input type="text" name="<?php echo $val; ?>" value="<?php if (array_key_exists($val, $_REQUEST)) echo htmlentities($_REQUEST[$val]); ?>"/></td>
	</tr>
<?php
	}
	foreach (array('images', 'metadata', 'nosensitive') as $val){
?>
	<tr>
		<td><?php echo $val; ?></td>
		<td><input type="checkbox" name="<?php echo $val; ?>" <?php if (array_key_exists($val, $_REQUEST)) echo 'checked'; ?>/></td>
	</tr>
<?php
	}
?>
	<tr>
		<td>category</td>
		<td>
		<select name="category">

<?php
	$res=db_query("SELECT name from categories UNION SELECT ' ' AS name ORDER BY name");
        while($val = db_result($res)){

?>
		<option<?php if ((array_key_exists('category', $_REQUEST)) && ($_REQUEST['category']==$val)) echo ' selected="selected"'; ?>><?php echo $val; ?></option>
<?php
	}
?>
		</select>
		</td>
	</tr>
	<tr>
	<td colspan="2" align="right"><input type="submit" /></td>
	</tr>
</table>
</form>

For more info about this/feedback please visit the <a href="https://github.com/springfiles/upq">UPQ project page</a>.
All these parameters can be used for the <a href="xmlrpc.php">xmlrpc api</a>, too.

<pre>
<?php

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
echo dump_result($res);
?>
</pre>
</body>
</html>
