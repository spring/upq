-- create table for the file keywords
CREATE TABLE `file_keyword` (
  `fid` int(11) NOT NULL,
  `keyword` varchar(128) NOT NULL,
  PRIMARY KEY (`fid`,`keyword`),
  CONSTRAINT `fk_file_keyword_file` FOREIGN KEY (`fid`) REFERENCES `file` (`fid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- add file attributes to simplify searches
ALTER IGNORE TABLE `file` ADD `name_without_version` varchar(256) DEFAULT NULL COMMENT 'workaround for name including version on maps' AFTER `metadata`;
ALTER IGNORE TABLE `file` ADD `map_width` int(11) DEFAULT 0 COMMENT 'map width' AFTER `name_without_version`;
ALTER IGNORE TABLE `file` ADD `map_height` int(11) DEFAULT 0 COMMENT 'map height' AFTER `map_width`;

-- update new attributes for existing map file records
UPDATE file f LEFT JOIN (SELECT tab1.fid,tab1.width,tab1.height,TRIM(REGEXP_REPLACE(name,CONCAT('[\-_ ]*[vV]?(?i)',IF(version_metadata <> '',version_metadata,version_filename),'$'),'')) AS name_without_version FROM ( SELECT fid, name, REGEXP_SUBSTR(filename,'(?<=[\-_ vV])([vV]?[0-9\.]+[^\-_ ]*)(?=.sd.$)') AS version_filename, IF(metadata LIKE '%"Version":%',SUBSTRING_INDEX(SUBSTRING_INDEX(metadata,'"Version": "',-1),'",',1),'') AS version_metadata, CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(metadata,'"Width": ',-1),',',1) AS DECIMAL) AS width, CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(metadata,'"Height": ',-1),',',1) AS DECIMAL) AS height FROM file WHERE cid=2 ORDER BY timestamp DESC) tab1) f2 ON (f.fid=f2.fid) SET f.name_without_version=f2.name_without_version,f.map_width=f2.width,f.map_height=f2.height WHERE f.cid=2;
UPDATE file f SET f.name_without_version=f.name WHERE f.cid=1;

-- create trigger to update the new columns when file records are added/updated
DROP TRIGGER IF EXISTS tr_file_before_insert;
DELIMITER $$
CREATE TRIGGER tr_file_before_insert
BEFORE INSERT ON file
FOR EACH ROW
BEGIN
	IF NEW.cid = 1 THEN
		SET NEW.name_without_version=NEW.name;
	ELSEIF NEW.cid = 2 THEN
		SELECT tab1.width,tab1.height,
			TRIM(REGEXP_REPLACE(name,CONCAT('[\-_ ]*[vV]?(?i)',IF(version_metadata <> '',version_metadata,version_filename),'$'),'')) AS name_without_version 
			INTO @map_width,@map_height,@name_without_version 
			FROM ( SELECT NEW.name AS name, REGEXP_SUBSTR(NEW.filename,'(?<=[-_ vV])([vV]?[0-9]+[^-_ ]*)(?=.sd.$)') AS version_filename, 
					IF(NEW.metadata LIKE '%"Version":%',SUBSTRING_INDEX(SUBSTRING_INDEX(NEW.metadata,'"Version": "',-1),'",',1),'') AS version_metadata, 
					CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(NEW.metadata,'"Width": ',-1),',',1) AS DECIMAL) AS width, 
					CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(NEW.metadata,'"Height": ',-1),',',1) AS DECIMAL) AS height 
					) tab1;
		SET NEW.name_without_version=@name_without_version;
		SET NEW.map_width=@map_width;
		SET NEW.map_height=@map_height;
	END IF;
END $$
DELIMITER ;


DROP TRIGGER IF EXISTS tr_file_before_update;
DELIMITER $$
CREATE TRIGGER tr_file_before_update
BEFORE UPDATE ON file
FOR EACH ROW
BEGIN
	IF NEW.cid = 1 THEN
		SET NEW.name_without_version=NEW.name;
	ELSEIF NEW.cid = 2 THEN
		SELECT tab1.width,tab1.height,
			TRIM(REGEXP_REPLACE(name,CONCAT('[\-_ ]*[vV]?(?i)',IF(version_metadata <> '',version_metadata,version_filename),'$'),'')) AS name_without_version 
			INTO @map_width,@map_height,@name_without_version 
			FROM ( SELECT NEW.name AS name, REGEXP_SUBSTR(NEW.filename,'(?<=[-_ vV])([vV]?[0-9]+[^-_ ]*)(?=.sd.$)') AS version_filename, 
					IF(NEW.metadata LIKE '%"Version":%',SUBSTRING_INDEX(SUBSTRING_INDEX(NEW.metadata,'"Version": "',-1),'",',1),'') AS version_metadata, 
					CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(NEW.metadata,'"Width": ',-1),',',1) AS DECIMAL) AS width, 
					CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(NEW.metadata,'"Height": ',-1),',',1) AS DECIMAL) AS height 
					) tab1;
		SET NEW.name_without_version=@name_without_version;
		SET NEW.map_width=@map_width;
		SET NEW.map_height=@map_height;
	END IF;
END $$
DELIMITER ;


-- create trigger to set keywords for new files
DROP TRIGGER IF EXISTS tr_file_after_insert;
DELIMITER $$
CREATE TRIGGER tr_file_after_insert
AFTER INSERT ON file
FOR EACH ROW
BEGIN
	IF NEW.cid = 2 THEN
		-- inherit keywords from earlier versions of the same map, if any
		INSERT INTO file_keyword (SELECT DISTINCT NEW.fid,keyword FROM file_keyword fk INNER JOIN file f ON (fk.fid=f.fid) WHERE f.name_without_version=NEW.name_without_version);
		
		-- set the size keywords
		REPLACE INTO file_keyword(fid,keyword) VALUES (NEW.fid,IF(NEW.map_width*NEW.map_height > 18*18,'large',IF(NEW.map_width*NEW.map_height > 144 AND NEW.map_width*NEW.map_heig    ht <= 18*18,'medium','small')));
	END IF;
END $$
DELIMITER ;

