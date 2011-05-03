# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# Tasks are classes derived from UpqTask
#
# The classes name MUST be the same as the modules filename with
# the first letter upper case!
#

import log

class UpqTask():
    logger = log.getLogger("upq")
    result = {}
    
    def __init__(self, filename, fileid, config, thread):
        self.filename = filename
        self.fileid = fileid
        self.config = config
        self.thread = thread
        self.result = {}
    
    def get_result(self):
        return self.result
    
    def run(self):
        # save result into self.result
        pass
