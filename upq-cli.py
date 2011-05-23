#!/usr/bin/env python

import socket
import sys

socket_name = "/tmp/upq-incoming.sock"

def send_cmd(txts):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(socket_name)
    print >>sys.stderr, "Connected to '%s'."%socket_name
    for txt in txts:
        sock.send(txt+"\n")
        print >>sys.stderr, "Sent    : '%s'"%txt
        res=""
        while True:
            res += sock.recv(1)
            if res.endswith("\n"):
                print >>sys.stderr, res
                break
    sock.close()

def main(argv=None):
    if argv is None:
        argv = sys.argv
    send_cmd(argv[1:])

if __name__ == "__main__":
    sys.exit(main())
