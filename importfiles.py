import upqconfig, upqdb
import glob
import sys, os

cfg = upqconfig.UpqConfig()
cfg.readConfig()
db = upqdb.UpqDB()
db.connect(cfg.db['url'], cfg.db['debug'])


print(cfg.paths)

unitsyncpath=cfg.paths['unitsync']
sys.path.append(unitsyncpath)

from jobs import extract_metadata

files = glob.glob("/home/springfiles/www/games/*") + glob.glob("/home/springfiles/www/maps/*")


for f in files:
	jobdata = {
		"file": f,
	}
	j = extract_metadata.Extract_metadata("extract_metadata", jobdata)
	j.run()

