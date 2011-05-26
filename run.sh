#!/bin/sh
if [ -e ~/lib/python ]; then
	export PYTHONPATH=~/lib/python
fi

exec nice -19 ionice -c3 python upq.py

