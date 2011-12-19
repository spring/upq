# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# download: downloads a file, adds to db + calls new_file
#

from upqjob import UpqJob
from upqdb import UpqDB
from time import time
import urllib
import os
import shutil

class my_download(urllib.URLopener):
	def http_error_default(self, url, fp, errcode, errmsg, headers):
		raise Exception("Error retrieving %s %d %s" %(url, errcode, errmsg))

class Download(UpqJob):
	"""
		"download url:$url"
	"""

	def run(self):
		url=self.jobdata['url']
		filename=os.path.basename(url)
		tmpfile=os.path.join(self.getcfg('temppath', '/tmp'), filename)
		self.jobdata['file']=tmpfile
#		uid=int(self.jobdata['uid'])
		self.logger.debug("going to download %s", url)
		try:
			filename, headers = my_download().retrieve(url, tmpfile)
			urllib.urlcleanup()
		except Exception, e:
			self.msg(e)
			return False
		return True

