# This file is part of the "upq" program used on springfiles.springrts.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import logging
import configparser as ConfigParser
import os

class UpqConfig():
	__shared_state = {}
	paths  = {}
	jobs   = {}
	db	 = {}
	config = ""

	def setstr(self,obj, section, value, default):
		try:
			obj[value]=self.config.get(section, value)
		except:
			if default!=None:
				obj[value]=default
	def setpath(self, obj, section, value, default, directory=True):
		try:
			obj[value]=os.path.abspath(self.config.get(section, value))
		except:
			if default!=None:
				self.setstr(obj, section, value, os.path.abspath(default))
		if not os.path.exists(obj[value]):
			logging.error("%s doesn't exist" % (obj[value]))

	def setbool(self,obj, section, value, default):
		try:
			obj[value]=self.config.getboolean(section, value)
		except:
			if default!=None:
				obj[value]=default
	def setint(self,obj, section, value, default):
		try:
			obj[value]=self.config.getint(section, value)
		except:
			if default!=None:
				obj[value]=default

	def __init__(self):
		configfile = os.path.join(os.path.dirname(os.path.dirname(__file__)), "upq.cfg")
		logging.info("reading %s" %(configfile))
		if not os.access(configfile, os.R_OK):
			raise Exception("Cannot read config file \"%s\"." % configfile)
		try:
			self.config = ConfigParser.RawConfigParser()
			self.config.read(configfile)
		except Exception as e:
			raise Exception("Couldn't parse %s %s" % (configfile, e))

		self.paths = {}

		self.setpath(self.paths, "paths", "uploads", "uploads")
		self.setpath(self.paths, "paths", "files", "files")
		self.setpath(self.paths, "paths", "metadata", "metadata")
		self.setpath(self.paths, "paths", "broken", "paths")
		self.setpath(self.paths, "paths", "tmp", "tmp")
		self.setpath(self.paths, "paths", "unitsync", "libunitsync.so")

		self.setint(self.paths, "paths", "socket_chmod", 660)

		self.db = {}
		self.setstr(self.db, "db", "url", "sqlite:///var/lib/upq/upq.db")
		self.setbool(self.db, "db", "debug", False)

		for section in self.config.sections():
			if section.startswith("job"):
				job=section.split()[1]
				self.jobs[job]={} #initialize default values
				for name, value in self.config.items(section):
					self.jobs[job][name]=value

		logging.info("paths='%s'" % self.paths)
		logging.info("jobs:'%s'" % sorted(self.jobs.keys()))
		for job in sorted(self.jobs.keys()):
			logging.info("  {0}: {1}".format(job, self.jobs[job]))
		logging.info("db='%s'" % self.db)
