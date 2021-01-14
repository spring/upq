# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

# downloads a file

from upqjob import UpqJob
from upqdb import UpqDB
from time import time
import os
import shutil
import requests



class Download(UpqJob):
	"""
		"download url:$url"
	"""
	def run(self):
		url=self.jobdata['url']
		filename=os.path.basename(url)
		tmpfile=os.path.join(self.getcfg('temppath', '/tmp'), filename)
		self.jobdata['file']=tmpfile
		self.logger.debug("going to download %s", url)
		try:
			response = requests.get(url, stream=True, verify=False)
			with open(tmpfile, 'wb') as out_file:
				shutil.copyfileobj(response.raw, out_file)
			del response
			self.logger.debug("downloaded to %s", tmpfile)
		except Exception as e:
			self.logger.error(str(e))
			return False
		return True

