#!/bin/sh
if [ -e ~/lib/python ]; then
	export PYTHONPATH=~/lib/python
fi
cd $(dirname $0)
#kill remaining processes
mv upq.log.2 upq.log.3
mv upq.log.1 upq.log.2
mv upq.log upq.log.1
pkill -u $(whoami) -f "python upq.py"
exec nice -19 ionice -c3 python2 upq.py

