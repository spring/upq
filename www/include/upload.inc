<?php

$valid_ext = array('sd7', 'sdz');

function tempdir() {
    $tempfile=tempnam(sys_get_temp_dir(),'upq');
    if (file_exists($tempfile)) { unlink($tempfile); }
    mkdir($tempfile);
    if (is_dir($tempfile)) { return $tempfile; }
}

foreach($_FILES as $file) {
	$ext = pathinfo($file['name'], PATHINFO_EXTENSION);
	if (!in_array($ext, $valid_ext)) {
		echo "Invalid file extension";
		break;	
	}
	//create temp directory
	$dir = tempdir();
	$orgname = basename($file['name']);
	$tmpfile =  $file['tmp_name'].".$ext";
	$upqfile = $dir.'/'.$orgname;
	//move+rename file to original filename in temp directory
	rename($file['tmp_name'], $upqfile);
	// feed upq with the uploaded file
	echo upq_run("new_file file:$upqfile")."<br>";
	echo "Uploaded $orgname<br>";
}

