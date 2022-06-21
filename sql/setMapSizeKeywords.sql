REPLACE INTO file_keyword(fid,keyword) (SELECT f.fid,'small' FROM file f WHERE cid=2 AND map_width*map_height <= 12*12);
REPLACE INTO file_keyword(fid,keyword) (SELECT f.fid,'medium' FROM file f WHERE cid=2 AND map_width*map_height > 144 AND map_width*map_height <= 18*18);
REPLACE INTO file_keyword(fid,keyword) (SELECT f.fid,'large' FROM file f WHERE cid=2 AND map_width*map_height > 18*18);
