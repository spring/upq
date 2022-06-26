-- workaround for weirdness of defining delete cascade with sqlalchemy
ALTER TABLE `file_keyword` DROP FOREIGN KEY `fk_file_keyword_file`;
ALTER TABLE `file_keyword` ADD CONSTRAINT `fk_file_keyword_file` FOREIGN KEY (`fid`) REFERENCES `file` (`fid`) ON DELETE CASCADE;