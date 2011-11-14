# -*- coding: utf-8 -*-
# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# notify: notify users about result of jobs
#

from email.mime.text import MIMEText
import smtplib
import syslog
import operator
import quopri
import email
import log
import copy
import upqconfig
from upqjob import UpqJob
from upqqueuemngr import UpqQueueMngr

class Notify(UpqJob):
    def run(self):
        for key,value in self.jobdata.items():
            msg=self.jobdata['job']['msgstr']
            if key=="mail":
                if self.jobdata['success']:
                    subject="Error"
                else:
                    subject="Success"
                log.getLogger().debug("notify mail(value, msg, subject)=mail(%s, %s, %s)", value, msg, subject)
                self.mail(value, msg, subject)
            elif key=="syslog":
                log.getLogger().debug("notify syslog")
                self.syslog(self.jobdata['success'], msg)
            elif key == "retry":
                log.getLogger().debug("notify retry:%s", value)
                if self.jobdata['job']['retries'] >= int(value):
                    log.getLogger().info("Tried %d times, no more retries.", self.jobdata['job']['retries'])
                    return False
                else:
                    # recreate job
                    retry_job = UpqQueueMngr().new_job(self.jobdata['job']['jobname'], self.jobdata['job']['jobdata'])
                    for key in self.jobdata['job'].keys():
                        # copy data to allow release of old job resources
                        setattr(retry_job, key, copy.deepcopy(self.jobdata['job'][key]))

                    retry_job.retries += 1
                    log.getLogger().info("retrying job '%s' for the %d. time", retry_job.jobname, retry_job.retries)
                    retry_job.jobid = UpqQueueMngr().enqueue_job(retry_job)
        return True

    def success(self, jobname, msg):
        if self.uc.jobs[jobname].has_key('notify_success') and self.uc.jobs[jobname]['notify_success']:
            notify_success = self.uc.jobs[jobname]['notify_success'].split()
            f = operator.methodcaller(notify_success[0], True, jobname, notify_success[1:], msg)
            f(self)

    def fail(self, jobname,  msg):
        if self.uc.jobs[jobname].has_key('notify_fail') and self.uc.jobs[jobname]['notify_fail']:
            notify_fail = self.uc.jobs[jobname]['notify_fail'].split()
            f = operator.methodcaller(notify_fail[0], False, jobname, notify_fail[1:], msg)
            f(self)

    def mail(self, recipient, msg, subject):
        mail = MIMEText(msg, "plain")
        mail.set_charset(email.charset.Charset('utf-8'))

        mail['Subject'] = subject
        mail['From']=self.jobcfg['from']
        mail['To']=recipient
        try:
            server = smtplib.SMTP("localhost")
            server.sendmail(mail['From'] , recipient, mail.as_string())
            server.quit()
        except Exception, e:
            self.msg="Error sending mail: '%s'" % e
            self.logger.error(self.msg)

    def syslog(self, err, msg):
        syslog.syslog(msg)
