#!/usr/bin/env python

import socket
import sys
import ConfigParser



def send_cmd(txts, socket_path):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(socket_path)
    except:
       raise Exception("Couldn't connect to %s" % (socket_path))
       return 2
    print >>sys.stderr, "Connected to '%s'."%socket_path
    #for txt in txts:
    txt = reduce(lambda x, y: x+" "+y, txts)
    sock.settimeout(10)
    sock.send(txt+"\n")
    print >>sys.stderr, "Sent    : '%s'"%txt
    res=""
    while True:
        res += sock.recv(1)
        if res.endswith("\n"):
            print >>sys.stderr, res,
            break
    sock.close()
    return 0

def main(argv=None):
    config = ConfigParser.RawConfigParser()
    config.read('upq.cfg')
    socket_path=config.get("paths","socket")
    if argv is None:
        argv = sys.argv
    if len(argv)==1:
	print 'Usage: %s "<jobname>( param:value)*"' % (argv[0])
        return 1
    return send_cmd(argv[1:],socket_path)

if __name__ == "__main__":
    sys.exit(main())
