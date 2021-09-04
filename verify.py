from lib import upqdb, upqconfig
import os, datetime

# verify files in db and in filesystems

cfg = upqconfig.UpqConfig()
db = upqdb.UpqDB(cfg.db['url'], cfg.db['debug'])

rows = db.query("select path, filename, timestamp, fid from file where path <> ''")

dbfiles = set()
c = 0
for row in rows:
	c += 1
	filename = os.path.join(cfg.paths["files"], row[0], row[1])
	dbfiles.add(filename)
	#print(filename)
	assert(os.path.isfile(filename))
	"""
	ftimestamp = os.path.getmtime(filename)
	if ftimestamp < row[2].timestamp():
		db.query("update file set timestamp='%s' where fid=%d" %(datetime.datetime.fromtimestamp(ftimestamp), row[3]))
		print("local file is older")
	"""

files = set()

for path in os.path.join(cfg.paths["files"], "maps"),  os.path.join(cfg.paths["files"], "games"):
	for f in os.listdir(path):
		files.add(os.path.join(path, f))

diff = dbfiles.difference(files)
if diff:
	raise Exception("db vs filesystem missmatch: " %str(diff))
