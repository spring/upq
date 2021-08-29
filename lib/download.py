# This file is part of the "upq" program used on springfiles.springrts.com to manage file
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

import requests
import os
import datetime
import time
import logging

def DownloadFile(url, filename, cache=True):
	""" returns true, when file was updated """
	logging.info("Downloading %s to %s" %(url, filename))
	dirname = os.path.dirname(filename)
	if not os.path.exists(dirname):
		os.makedirs(dirname)
	headers = {}
	if cache and os.path.isfile(filename):
		file_time = datetime.datetime.fromtimestamp(os.path.getmtime(filename))
		headers["If-Modified-Since"] = httpdate(file_time)

	r = requests.get(url, timeout=10, headers=headers)
	if r.status_code == 304:
		logging.debug("Not modified")
		return False
	with open(filename, "wb") as f:
		f.write(r.content)
	url_date = datetime.datetime.strptime(r.headers["last-modified"], '%a, %d %b %Y %H:%M:%S GMT')
	ts = int((time.mktime(url_date.timetuple()) + url_date.microsecond/1000000.0))
	os.utime(filename, (ts, ts))
	return True

def httpdate(dt):
	"""Return a string representation of a date according to RFC 1123
	(HTTP/1.1).

	The supplied date must be in UTC.

	"""
	weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
	month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
	     "Oct", "Nov", "Dec"][dt.month - 1]
	return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, dt.day, month,	dt.year, dt.hour, dt.minute, dt.second)

