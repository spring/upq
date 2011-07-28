# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# upload_file

from upqjob import UpqJob
from upqdb import UpqDB
import time
import random
from sqlalchemy import Table, MetaData
import pprint
from time import sleep

class Test(UpqJob):
	def check(self):
#		tables = ["upqueue",
#			"file_mirror",
#			"file_mirror_paths",
#			"file_mirror_files",
#			"springdata_archives",
#			"springdata_categories",
#			"springdata_depends",
#			"springdata_startpos",
#			"files",
#			"filehash" ]
#		meta=MetaData()
#		meta.bind = UpqDB().engine
#		for t in tables:
#			tbl=Table(t, meta, autoload=True)
#		pprint.pprint(meta.tables)
		self.enqueue_job()
		return True

	def run(self):
		sleep(random.uniform(2, 4))
		pprint.pprint("%d - %s - test *" % (self.jobid, self.thread))
		sleep(random.uniform(0, 3))
		pprint.pprint("%d - %s - test **" % (self.jobid, self.thread))
#		sleep(random.uniform (0, 3))
#		pprint.pprint("%d - %s - test ***" % (self.jobid, self.thread))
#		sleep(random.uniform (0, 3))
#		pprint.pprint("%d - %s - test ****" % (self.jobid, self.thread))
		self.msg("finished '%s'" % self.jobdata)
		return self.jobdata
