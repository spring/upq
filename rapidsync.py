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


from lib import log, upqdb, upqconfig

import sys

import json
import os

cfg = upqconfig.UpqConfig()
db = upqdb.UpqDB()
db.connect(cfg.db['url'], cfg.db['debug'])

from lib import rapidsync
j = rapidsync.Rapidsync()
j.run(cfg)

