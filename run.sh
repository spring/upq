#!/bin/sh
if [ -e ~/lib/python ]; then
	export PYTHONPATH=~/lib/python
fi

nice -19 ionice -c3 python upq.py

