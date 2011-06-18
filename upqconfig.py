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


class UpqConfig():
    __shared_state = {}
    paths  = {}
    jobs   = {}
    db     = {}
    config_log = "Log replay from config parsing:\n"
    config = ""
    configfile = "upq.cfg"
    logfile = ""

    def __init__(self, argv_options=None):
        self.__dict__ = self.__shared_state
        try:
            self.configfile=argv_options.configfile
            self.logfile=argv_options.logfile
        except:
            pass

    def conf_log(self, msg):
        self.config_log += msg+"\n"

    def readConfig(self):
        if not os.access(self.configfile, os.R_OK):
            print >> sys.stderr, "Cannot read config file \"%s\"."%self.configfile
            sys.exit(1)
        self.config = ConfigParser.RawConfigParser()
        self.config.read(self.configfile)

        if not self.config.has_section("logging"):
            # make sure to have a working logging system
            if self.logfile:
                self.logging = {'logfile': self.logfile}
            else:
                self.logging = {}
        else:
            self.logging = dict(self.config.items("logging"))
            if self.logfile:
                self.logging['logfile'] = self.logfile
        for section in self.config.sections():
            self.conf_log("found section '%s'"%section)
            if section == "logging":
                pass
            elif section == "paths":
                self.paths = dict(self.config.items(section))
                for entry in ["jobs_dir", "socket"]:
                    self.paths[entry] = os.path.abspath(self.paths[entry])
            elif section.startswith("db"):
                self.db = dict(self.config.items(section))
            elif section.startswith("daemon"):
                self.daemon = dict(self.config.items(section))
                # purge empty values, because we'll use this dict as arg to a function
                for key in self.daemon.keys():
                    if not self.daemon[key]:
                        del self.daemon[key]
                for key in ['umask', 'uid', 'gid']:
                    if self.daemon.has_key(key):
                        self.daemon[key] = int(self.daemon[key])
                if self.daemon.has_key("pidfile"):
                    self.daemon["pidfile"] = os.path.abspath(self.daemon["pidfile"])
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

        self.conf_log("paths='%s'" % self.paths)
        self.conf_log("jobs='%s'" % self.jobs)
        self.conf_log("db='%s'" % self.db)
        self.conf_log("daemon='%s'" % self.daemon)
