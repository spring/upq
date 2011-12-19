#!/bin/sh
if [ -e ~/lib/python ]; then
	export PYTHONPATH=~/lib/python
fi
#kill remaining processes
pkill "python upq.py"
exec nice -19 ionice -c3 python upq.py

