#!/usr/bin/env python3

# This file is part of the "upq" program used on springfiles.springrts.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Matthias Ableitner (spring #at# abma #dot# de)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# sf-sync: syncs file data with springfiles
# can be either initiaded by an updated file
# or maybe by the xml-rpc interface (or cron?)


from upqdb import UpqDB
import upqconfig

import sys
from xmlrpc.client import ServerProxy

import json
import os
import upqjob
import upqdb

class Sf_sync(upqjob.UpqJob):

	def versionfetch(self):
		from jobs import versionfetch 
		j = versionfetch.Versionfetch("versionfetch", {})
		j.run()
		return j.run()
	def run(self):
		self.versionfetch()

upqconfig.UpqConfig()
upqconfig.UpqConfig().readConfig()
db = upqdb.UpqDB()
db.connect(upqconfig.UpqConfig().db['url'], upqconfig.UpqConfig().db['debug'])

s = Sf_sync("sf_sync", dict())
s.run()

