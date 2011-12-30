
CREATE TABLE `upq`.`xmlrpc_log` (
`id` INT NOT NULL AUTO_INCREMENT ,
`ip` VARCHAR( 16 ) NOT NULL ,
`method` VARCHAR( 32 ) NOT NULL ,
`data` TEXT NOT NULL ,
PRIMARY KEY ( `id` )
) ENGINE = MYISAM ;

