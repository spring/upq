<?php
	require('config.php');
	require('include/drupal_dummy.inc');
	require('include/upq.inc');
	require('include/upload.inc');
?>
<html>
<head>
		<title>upload to upq</title>
		<style type="text/css">
<!--
body {
	background-color: #DDDDDD;
	color: #000000;
	margin:50px 0px;
	padding:0px;
	text-align:center; /* Hack for IE5/Win */
}
body, td, input{
	font-size:12;
}
.page {
	width: 600px;
	background-color: #FFFFFF;
	padding: 1em;
	margin:0px auto;
	text-align:left;
	border: 1px solid;
}
.form {
	width:600px;
}

h1 {
	font-size: 18px;
}
-->
		</style>
</head>
<body>
<div class="page">
	<h1>
		Upload
	</h1>
	<p>
		With this form you can upload files to the spring mirroring system.
		Files will be uploaded to mirrors and can be automaticly downloaded by Lobbies.
	</p>
	<form method="post" enctype="multipart/form-data">
		<table class="form">
		<tr>
				<td>Username</td>
				<td><input type="text" name="username"></td>
		</tr>
		<tr>
				<td>Password</td>
				<td><input type="password" name="password"></td>
		</tr>
<!--
		<tr>
			<td>publish in rapid (only games will be published)</td>
			<td><input type="checkbox" name="rapid"></td>
		</tr>
-->
		<tr>
			<td>Select file for upload</td>
			<td><input type="file" name="file"></td>
		</tr>
		<tr>
			<td>OR: http-url to download </td>
			<td><input type="text"></td>
		</tr>
		<tr>
			<td colspan="2" style="text-align: right;"><input type="submit" value="Upload"></td>
		</tr>
		</table>
	</form>
</div>
</body>
</html>

