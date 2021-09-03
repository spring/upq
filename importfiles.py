
from lib import upqconfig, upqdb, extract_metadata
import glob
import sys, os

cfg = upqconfig.UpqConfig()
db = upqdb.UpqDB()
db.connect(cfg.db['url'], cfg.db['debug'])


print(cfg.paths)

unitsyncpath=cfg.paths['unitsync']
sys.path.append(unitsyncpath)


files = glob.glob("/home/springfiles/www/downloads/spring/spring-maps/*") + glob.glob("/home/springfiles/www/downloads/spring/games/*")


for f in files:
	jobdata = {
		"file": f,
	}
	j = extract_metadata.Extract_metadata("extract_metadata", jobdata)
	j.run()

