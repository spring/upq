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


class ParseConfig():
    # don't use "logger" before readConfig() ran!
    logger = None
    paths  = {}
    jobs   = {}
    tasks  = {}
    db     = {}
    config_log = "Log replay from config parsing:\n"
    
    def conf_log(self, msg):
        self.config_log += msg+"\n"
        #print >>sys.stderr, msg
    
    def readConfig(self):
        config = ConfigParser.RawConfigParser()
        config.read('upq.cfg')
        
        if not config.has_section("logging"):
            # make sure to have a working logging system
            print >>sys.stderr, "No 'logging' section found in config file. " \
                +"Initializing log system with defaults."
            self.logger = log.init_logging(dict())
        
        for section in config.sections():
            self.conf_log("found section '%s'"%section)
            if section == "logging":
                log_cfg = config.items(section)
                self.logger = log.init_logging(dict(log_cfg))
                self.logger.debug("===== Logging initialized =====")
            elif section == "paths":
                self.paths = dict(config.items(section))
                for path in self.paths.keys():
                    if self.paths[path][:2] == "./":
                        # convert relative to absolute path
                        self.paths[path] = os.path.realpath(os.path.dirname(__file__)) +self.paths[path][1:]
            elif section.startswith("db"):
                self.db = dict(config.items(section))
            elif section.startswith("job"):
                if config.getboolean(section, "enabled"):
                    self.jobs[section.split()[1]] = dict(config.items(section))
                    del self.jobs[section.split()[1]]['enabled']
                    self.jobs[section.split()[1]]['concurrent'] = int(self.jobs[section.split()[1]]['concurrent'])
                else:
                    self.conf_log("   job '%s' is disabled"%section.split()[1])
            elif section.startswith("task"):
                self.tasks[section.split()[1]] = dict(config.items(section))
            else:
                self.conf_log("Unknown section '%s' found in config file, ignoring.", section)
        
        self.logger.info(self.config_log)
        
        self.logger.info("paths='%s'", self.paths)
        self.logger.info("jobs='%s'", self.jobs)
        self.logger.info("tasks='%s'", self.tasks)
        self.logger.info("db='%s'", self.db)

        # sanity check
        for job in self.jobs.keys():
            if not self.jobs[job].has_key("tasks"):
                # task list must not be empty
                msg="Found job '%s' without tasks, ignoring it.", job
                self.logger.error(msg)
                raise Exception(msg)

            if not reduce((lambda x, y: x and y),
                map(self.tasks.has_key, self.jobs[job]['tasks'].split())):
                # each task must have a section in the cfg file, and thus be a
                # key in tasks
                msg="Found job '%s' with an unknown task, ignoring it.", job
                self.logger.error("Found job '%s' with an unknown task, ignoring it.", job)
                raise Exception(msg)
        
        
        return self.paths, self.jobs, self.tasks, self.db

