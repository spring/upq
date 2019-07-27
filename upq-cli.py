#!/usr/bin/env python3

import socket
import sys
import configparser



def send_cmd(txts, socket_path):
	sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	try:
		sock.connect(socket_path)
	except:
		raise Exception("Couldn't connect to %s" % (socket_path))
		return 2
	sys.stderr.write("Connected to '%s'."%socket_path + "\n")
	sock.settimeout(10)
	data = " ".join(txts) + "\n"
	sock.send(data.encode())
	sys.stderr.write("Sent: '%s'" % " ".join(txts) + "\n")
	res=""
	while True:
		res += sock.recv(1).decode()
		if res.endswith("\n"):
			sys.stderr.write(res + "\n")
			break
	sock.close()
	return 0

def main(argv=None):
	config = configparser.RawConfigParser()
	config.read('upq.cfg')
	socket_path=config.get("paths","socket")
	if argv is None:
		argv = sys.argv
	if len(argv)==1:
		print('Usage: %s "<jobname>( param:value)*"' % (argv[0]))
		return 1
	return send_cmd(argv[1:],socket_path)

if __name__ == "__main__":
	sys.exit(main())
