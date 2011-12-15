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
import time
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
                self._retrywait(value, 0)
            elif key == "retrywait":
                try:
                    # value looks like this:
                    # retries|time e.g.: 3|1h  or  4|30m  or  1|10s
                    tries,waittime = value.split('|')
                    tries = int(tries)
                    mul1  = int(waittime[:-1])
                    mul2 = waittime[-1:]
                    if    mul2 == "s": multi = 1
                    elif  mul2 == "m": multi = 60
                    elif  mul2 == "h": multi = 3600
                    else: raise Exception()
                except:
                    log.getLogger().error("notify retrywait:%s", value)
                    raise ValueError("retrywait -> tries|time -> int|int<s|m|h>")
                self._retrywait(tries, mul1*multi)
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

    def _retrywait(self, tries, waittime):
        """
        redo job 'tries' (int) times, waiting 'waittime' (int) seconds before each run
        """
        if waittime: log.getLogger().info("Waiting %d seconds before retry.", waittime)
        time.sleep(waittime)
        if self.jobdata['job']['retries'] >= tries:
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
            UpqQueueMngr().enqueue_job(retry_job)
