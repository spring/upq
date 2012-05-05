#!/bin/sh
if [ -e ~/lib/python ]; then
	export PYTHONPATH=~/lib/python
fi
cd $(dirname $0)
#kill remaining processes
pkill -u $(whoami) -f "python upq.py"
exec nice -19 ionice -c3 python upq.py

