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
import upqconfig
from upqjob import UpqJob

class Notify(UpqJob):
    def run(self):
        for key,value in self.jobdata.items():
            msg=self.jobdata['msg']
            err='success' in self.jobdata
            if (key=="mail"):
                if err:
                    subject="Error"
                else:
                    subject="Success"
                self.mail(value, msg, subject)
            elif (key=="syslog"):
                self.syslog(err, msg)
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
