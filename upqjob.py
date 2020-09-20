# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# Jobs are classes derived from UpqJob
#
# The classes name MUST be the same as the modules filename with
# the first letter upper case!
#

import threading

import log
import json
import requests
import upqconfig
import os
import datetime
import time

class UpqJob(object):
	def __init__(self, jobname, jobdata):
		# if you add attributes to the UpqJob class that should be carried over
		# through a restart/reschedule, add it to notify_job.jobdata['job']
		# in notify(), if and only if it is (JSON)-serializable!
		self.jobname = jobname
		self.jobcfg  = upqconfig.UpqConfig().jobs[jobname] #settings from config-filea

		# subjobs handling: if a runtime job is available, use it, else the configured ones
		if "subjobs" in jobdata: #runtime set subjobs are available
			jobdata['subjobs']=jobdata['subjobs']
		elif "subjobs" in self.jobcfg:
			# make copy of subjobs, as we modify them later
			jobdata['subjobs']=self.jobcfg['subjobs'][:]
		else:
			jobdata['subjobs'] = [] # no subjobs defined, initialize empty
		self.jobdata = jobdata #runtime parameters, these are stored into database and restored on re-run
		self.logger  = log.getLogger("upq")
		self.thread  = "T-none-0"
		self.jobid   = -1
		self.msgstr  = ""
		self.result  = False
		self.finished= threading.Event()
		self.retries = 0

	def check(self):
		"""
		Check if job is feasable and possibly queue it.
		Overwrite this method in your job class.

		Returns True + sets jobid
		"""
		# check if file is readable (or similar)
		# return True when jobdata is fine to call run(), when returning False sets self.msg
		self.enqueue_job()
		return True

	def run(self):
		"""
		Do the actual job work, save result in self.result.
		Returning boolean indicates success or failure for notification system.

		Overwrite this method in your job class.
		"""
		# Save result in self.result.
		return True

	def __setstate__(self, dict):
		# this is used to unpickle a job
		self.__dict__.update(dict)
		self.logger = log.getLogger("upq")

	def msg(self, msg):
		self.logger.debug(msg)
		if len(self.msgstr)+len(msg)<=500:
			self.msgstr+=str(msg)
		else:
			self.logger.error("msg to long: --------%s-------" %(msg))

	def append_job(self, job, params={}):
		"""
			append job, will be added as the first job
		"""
		self.jobdata['subjobs'].append(job)
		for name in params:
			self.jobdata[name]=params[name]

	def __str__(self):
		return "Job: "+self.jobname +" id:"+ str(self.jobid)+" jobdata:"+json.dumps(self.jobdata) +" thread: "+self.thread

	def getcfg(self, name, default):
		"""
			returns a config value or default, if config isn't set
		"""
		if name in  self.jobcfg:
			return self.jobcfg[name]
		else:
			return default

	def DownloadFile(self, url, filename, cache=True):
		""" returns true, when file was updated """
		dirname = os.path.dirname(filename)
		if not os.path.exists(dirname):
			os.makedirs(dirname)
		headers = {}
		if cache and os.path.isfile(filename):
			file_time = datetime.datetime.fromtimestamp(os.path.getmtime(filename))
			headers["If-Modified-Since"] = self.httpdate(file_time)

		r = requests.get(url, timeout=10, headers=headers)
		if r.status_code == 304:
			self.logger.debug("Not modified")
			return False
		with open(filename, "wb") as f:
			f.write(r.content)
		url_date = datetime.datetime.strptime(r.headers["last-modified"], '%a, %d %b %Y %H:%M:%S GMT')
		ts = int((time.mktime(url_date.timetuple()) + url_date.microsecond/1000000.0))
		os.utime(filename, (ts, ts))
		return True

	def httpdate(self, dt):
		"""Return a string representation of a date according to RFC 1123
		(HTTP/1.1).

		The supplied date must be in UTC.

		"""
		weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
		month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
		     "Oct", "Nov", "Dec"][dt.month - 1]
		return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, dt.day, month,	dt.year, dt.hour, dt.minute, dt.second)

