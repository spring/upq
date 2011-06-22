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
		"download url:$url sdp:$sdp filename:$filename uid:$uid"	
	"""

	def check(self):
		tmp=self.jobcfg['temppath']
		self.msg=str(self.jobdata)
		self.enqueue_job()
		return True

	def run(self):
		filename=os.path.basename(self.jobdata['filename'])
		tmpfile=os.path.join(self.jobcfg['temppath'], filename)
		dstfile=os.path.join(self.jobcfg['downloaddir'], filename)
		url=self.jobdata['url']
		uid=int(self.jobdata['uid'])
		self.logger.debug("going to download %s", url)
		try:
			filename, headers = my_download().retrieve(url, tmpfile)
			urllib.urlcleanup()
		except Exception, e:
			self.msg=str(e)
			return False
		#TODO validate somehow?
		shutil.move(tmpfile, dstfile)
		self.msg="Downloaded %s (%s bytes)" % (dstfile, os.path.getsize(dstfile))
		self.enqueue_newjob("new_file", { "filepath": dstfile, "filename": filename, "uid":uid })
		return True

