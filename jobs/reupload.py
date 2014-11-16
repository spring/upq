# -*- coding: utf-8 -*-
# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Matthias Ableitner (spring #at# abma #dot# de)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# sets tags for already known files taken from the file list of the "rapid"
# download system

from upqjob import UpqJob
from upqdb import UpqDB
from time import sleep
class Reupload(UpqJob):
	def run(self):
		results = UpqDB().query("SELECT count(mid) from mirror");
		count = res.first()[0]
		results=UpqDB().query("SELECT f.mfid FROM mirror_file f LEFT JOIN mirror m ON f.mid=m.mid \
			WHERE m.status=1 \
			AND ( f.lastcheck < DATE_SUB(NOW(), INTERVAL 1 MONTH) \
			OR f.lastcheck is null ) \
			ORDER BY f.lastcheck ASC \
			LIMIT 0,30")
		for res in results:
			self.enqueue_newjob("verify_remote_file", { "mfid":res["mfid"]})
			sleep(10)
		return True

