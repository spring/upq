from xmlrpc.client import ServerProxy, Error
import logging, upqconfig, upqdb
import socket

lastfid = 0

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(module)s.%(funcName)s:%(lineno)d %(message)s"))
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.DEBUG)
logging.info("Started sf_sync")

upqconfig.UpqConfig(configfile="upq2.cfg")
upqconfig.UpqConfig().readConfig()
db = upqdb.UpqDB()
db.connect(upqconfig.UpqConfig().db['url'], upqconfig.UpqConfig().db['debug'])

def SendUPQ(cmd):
	sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	sock.connect("/home/upq/.upq-incoming.sock")
	sock.sendall(cmd.encode())
	print(sock.recv(1024))
	sock.close()

with ServerProxy("https://springfiles.com/xmlrpc.php", verbose=False) as proxy:

	results = True
	while results:
		results = False
		print("Calling %s" %(lastfid))
		for f in proxy.springfiles.getfiles(lastfid):
			lastfid = max(lastfid, int(f["fid"]))
			results = True
			#print(f)
			row = db.query("SELECT * FROM file WHERE md5='%s'" %(f['md5']))
			if row.first():
				continue
			print("Missing:",f)
			#SendUPQ("download url:http://springfiles.com/%s\n" %(f["filepath"]))

