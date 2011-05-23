# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# New_file: handle new files on springfiles.com
# inserts file into db + forks hash job
#

from upqjob import UpqJob

class New_file(UpqJob):
    """
    filepath must be set
    """

    def check(self):
        # check if file is readable
        self.enqueue_job()

        # try to guess if we have a filename or a fileid
        self.logger.debug("self.jobdata='%s'", self.jobdata)
        self.fileid = int(self.jobdata['fid'])
        self.filename = self.jobdata['filename']
        return True

    def run(self):

        return False

