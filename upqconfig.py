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

    def setstr(self,obj, section, value, default):
        try:
            obj[value]=self.config.get(section, value)
        except:
            if default!=None:
                obj[value]=default
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

    def __init__(self, configfile="", logfile=""):
        self.__dict__ = self.__shared_state
        if len(configfile)>0:
            self.configfile=configfile
        if len(logfile)>0:
            self.logfile=logfile

    def conf_log(self, msg):
        self.config_log += msg+"\n"

    def readConfig(self):
        if not os.access(self.configfile, os.R_OK):
            print >> sys.stderr, "Cannot read config file \"%s\"."%self.configfile
            sys.exit(1)
        try:
            self.config = ConfigParser.RawConfigParser()
            self.config.read(self.configfile)
        except Exception,e:
            print >> sys.stderr, "Couldn't parse %s %s" % (self.configfile, e)
            sys.exit(1)
        self.logging = {}
        self.setstr(self.logging,"logging", "loglevel", "info")
        self.setstr(self.logging,"logging", "logformat", "%(asctime)s %(levelname)-8s %(name)s.%(module)s.%(funcName)s() l.%(lineno)03d : %(message)s")
        self.setstr(self.logging,"logging", "logfile", "/var/log/upq.log")

        self.daemon = {}
        self.setbool(self.daemon, "daemon", "detach_process", False)
        self.setint(self.daemon, "daemon", "umask", 22)
        self.setstr(self.daemon, "daemon", "pidfile", None)
        self.setstr(self.daemon, "daemon", "chroot_directory", None)
        self.setint(self.daemon, "daemon", "uid", None)
        self.setint(self.daemon, "daemon", "gid", None)

        self.paths = {}
        self.setstr(self.paths, "paths", "jobs_dir", "./jobs")
        self.setstr(self.paths, "paths", "socket", "/var/run/upq-incoming.sock")
        self.setint(self.paths, "paths", "socket_chmod", 660)
        self.paths['jobs_dir']=os.path.abspath(self.paths['jobs_dir'])

        self.db = {}
        self.setstr(self.db, "db", "url", "sqlite://upq.db")

        for section in self.config.sections():
            if section.startswith("job"):
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
