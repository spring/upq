-- create table for the file keywords
-- code on upqdb.py, remove here?
CREATE TABLE `file_keyword` (
  `fid` int(11) NOT NULL,
  `keyword` varchar(128) NOT NULL,
  PRIMARY KEY (`fid`,`keyword`),
  CONSTRAINT `fk_file_keyword_file` FOREIGN KEY (`fid`) REFERENCES `file` (`fid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- add file attributes to simplify searches
-- code on upqdb.py, remove here?
ALTER IGNORE TABLE `file` ADD `name_without_version` varchar(256) DEFAULT NULL COMMENT 'workaround for name including version on maps' AFTER `metadata`;
ALTER IGNORE TABLE `file` ADD `map_width` int(11) DEFAULT 0 COMMENT 'map width' AFTER `name_without_version`;
ALTER IGNORE TABLE `file` ADD `map_height` int(11) DEFAULT 0 COMMENT 'map height' AFTER `map_width`;
ALTER IGNORE TABLE `file` ADD `version_sort_number` float DEFAULT 0 COMMENT 'version number to simplify comparison/sorting' AFTER `map_height`;

-- workaround for weirdness of defining delete cascade with sqlalchemy
ALTER TABLE `file_keyword` DROP FOREIGN KEY `fk_file_keyword_file`;
ALTER TABLE `file_keyword` ADD CONSTRAINT `fk_file_keyword_file` FOREIGN KEY (`fid`) REFERENCES `file` (`fid`) ON DELETE CASCADE;