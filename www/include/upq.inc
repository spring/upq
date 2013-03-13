<?php

/**
* notify cron job about changes
*/
function upq_run($job){
        global $config;
        $timeout=5;
        $sock = @stream_socket_client($config['socket'], $errno, $errstr, $timeout);
        if($sock===FALSE){
                watchdog("filemirror", "error connecting to upq socket $errstr $job");
                return;
        }
        stream_set_timeout($sock, $timeout);
        fwrite($sock, "$job\n");
        $res=fgets($sock);
        fclose($sock);
        watchdog("filemirror", "result from upq: $res");
        return $res;
}

