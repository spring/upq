# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import ConfigParser
import os, os.path

import log

class UpqConfig():
    __shared_state = {}
    # don't use "logger" before readConfig() ran!
    logger = None
    paths  = {}
    jobs   = {}
    db     = {}
    config_log = "Log replay from config parsing:\n"
    config = None

    def __init__(self):
        self.__dict__ = self.__shared_state

    def conf_log(self, msg):
        self.config_log += msg+"\n"

    def readConfig(self):
        self.config = ConfigParser.RawConfigParser(allow_no_value=True)
        self.config.read('upq.cfg')

        if not self.logger and not self.config.has_section("logging"):
            # make sure to have a working logging system
            print >>sys.stderr, "No 'logging' section found in config file. Initializing log system with defaults."
            self.logger = log.init_logging(dict())
        else:
             log_cfg = self.config.items("logging")
             self.logger = log.init_logging(dict(log_cfg))
             self.logger.debug("===== Logging initialized =====")


        for section in self.config.sections():
            self.conf_log("found section '%s'"%section)
            if section == "logging":
                pass
            elif section == "paths":
                self.paths = dict(self.config.items(section))
                for path in self.paths.keys():
                    if self.paths[path][:2] == "./":
                        # convert relative to absolute path
                        self.paths[path] = os.path.realpath(os.path.dirname(__file__)) +self.paths[path][1:]
            elif section.startswith("db"):
                self.db = dict(self.config.items(section))
            elif section.startswith("job"):
                job=section.split()[1]
                if self.config.getboolean(section, "enabled"):
					self.jobs[job]={} #initialize default values
					self.jobs[job]['concurrent']=1
					self.jobs[job]['notify_fail']=""
					self.jobs[job]['notify_success']=""
					for name, value in self.config.items(section):
						if name=="concurrent":
							self.jobs[job]['concurrent'] = self.config.getint(section, "concurrent")
						else:
							self.jobs[job][name]=value

                else:
                    self.conf_log("   job '%s' is disabled" % job )

            else:
                self.conf_log("Unknown section '%s' found in config file, ignoring."% (section))

        self.logger.info(self.config_log)

        self.logger.info("paths='%s'", self.paths)
        self.logger.info("jobs='%s'", self.jobs)
        self.logger.info("db='%s'", self.db)

