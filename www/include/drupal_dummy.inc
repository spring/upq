<?php

if(!mysql_connect($config['db_host'], $config['db_user'], $config['db_pass']))
	die("mysql error: ".mysql_error());

if(!mysql_select_db($config['db_db']))
	die("mysql error: ".mysql_error());

//drupal dummy functions to make xmlrp*.inc work

function check_plain($text) {
  return (preg_match('/^./us', $text) == 1) ? htmlspecialchars($text, ENT_QUOTES, 'UTF-8') : '';
}

function t($string, $args = array(), $langcode = NULL){
    foreach ($args as $key => $value) {
          $args[$key] = check_plain($value);
    }
    return strtr($string, $args);
}

function db_prefix_tables($sql) {
    $db_prefix="";
    return strtr($sql, array('{' => $db_prefix, '}' => ''));
}


function _db_query_callback($match, $init = FALSE) {
  static $args = NULL;
  if ($init) {
    $args = $match;
    return;
  }

  switch ($match[1]) {
    case '%d': // We must use type casting to int to convert FALSE/NULL/(TRUE?)
      $value = array_shift($args);
      $value = (int) $value;
      // We don't need db_escape_string as numbers are db-safe.
      return $value;
    case '%s':
      return db_escape_string(array_shift($args));
    case '%n':
      // Numeric values have arbitrary precision, so can't be treated as float.
      // is_numeric() allows hex values (0xFF), but they are not valid.
      $value = trim(array_shift($args));
      return is_numeric($value) && !preg_match('/x/i', $value) ? $value : '0';
    case '%%':
      return '%';
    case '%f':
      return (float) array_shift($args);
    case '%b': // binary data
      return db_encode_blob(array_shift($args));
  }
}

function db_escape_string($text) {
  return mysql_real_escape_string($text);
}

function db_encode_blob($data) {
  return "'". mysql_real_escape_string($data, $active_db) ."'";
}

define('DB_QUERY_REGEXP', '/(%d|%s|%%|%f|%b|%n)/');
function db_query($query) {
  $args = func_get_args();
  array_shift($args);
  $query = db_prefix_tables($query);
  if (isset($args[0]) and is_array($args[0])) { // 'All arguments in one array' syntax
    $args = $args[0];
  }
  _db_query_callback($args, TRUE);
  $query = preg_replace_callback(DB_QUERY_REGEXP, '_db_query_callback', $query);
  return _db_query($query);
}

function _db_query($query) {
  $result = mysql_query($query);
  if (!mysql_errno()) {
    return $result;
  }
  else {
    trigger_error(check_plain(mysql_error() ."\nquery: ". $query), E_USER_WARNING);
    return FALSE;
  }
}

function db_result($result) {
  if ($result && mysql_num_rows($result) > 0) {
    // The mysql_fetch_row function has an optional second parameter $row
    // but that can't be used for compatibility with Oracle, DB2, etc.
    $array = mysql_fetch_row($result);
    return $array[0];
  }
  return FALSE;
}

function watchdog($msg, $arr=array()){
	return;
	if (sizeof($arr)>0)
		print_r($arr);
	echo "\n";
}

function db_fetch_array($result){
	if ($result)
		return mysql_fetch_array($result, MYSQL_ASSOC);
}

