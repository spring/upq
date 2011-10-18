<?php
//for an example config, see config.php
if (file_exists('config.php'))
	include ('config.php');

if (defined('ALLOWED_IP') && array_key_exists('REMOTE_ADDR',$_SERVER) && ($_SERVER['REMOTE_ADDR'] != constant('ALLOWED_IP')))
	exit("disallowed ip: ".$_SERVER['REMOTE_ADDR']);

if (defined ('PASSWORD') && array_key_exists('pw',$_GET) && ($_GET['pw'] != constant('PASSWORD')))
	exit("disallowed password!");

$path = @$_SERVER[DOCUMENT_ROOT] . '/' . @$_GET['p'];

if (is_dir($path))
	exit("File '$path' is a directory!\n");
if (!is_readable($path))
	exit("File '$path' doesn't exist!\n");

if (defined('LOCK_FILE') && file_exists(constant('LOCK_FILE'))){
	//lock file exists. check if its older than x. could be from a terminated deamon.php
	$filelastmodified = filemtime(constant('LOCK_FILE'));
	$age = time() - $filelastmodified;
	if(($age) > constant('MAX_LOCK_FILE_AGE_S'))
		unlink(constant('LOCK_FILE')); //delete the lock and keep running
	else
		exit('Already running since: ' . $age . ' s');
}

if (defined('LOCK_FILE'))
	touch(constant('LOCK_FILE'));
echo hash_file('md5', $path);
if (defined('LOCK_FILE'))
	unlink(constant('LOCK_FILE'));
?>
