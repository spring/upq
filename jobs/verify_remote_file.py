# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# Verify_remote_file: check the integrity of a file on a mirror by comparing
# the result of the PHP-script "deamon.php" with the stored hash in the DB
# 

import log
import upqtask
import upqjob

class Verify_remote_file(UpqJob):
    def check():
        # check if file is readable (or similar)
        # register_to_queue()
        # return ACK/REJ + optional msg in dict(['queued'], ['jobid'], ['msg'])
        return {'queued': True, 'jobid': 0, 'msg': 'Not implemented yet.'}
    
    def run():
        # actual work
        pass
