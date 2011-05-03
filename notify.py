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

class Notify():
    def success(self, jobname, method, recipient, msg):
        f = operator.methodcaller(method, True, jobname, recipient, msg)
        f(self)
    
    def fail(self, jobname, method, recipient, msg):
        f = operator.methodcaller(method, False, jobname, recipient, msg)
        f(self)
    
    def mail(self, success, jobname, recipient, msg):
        mail = MIMEText(msg, "plain")
        mail.set_charset(email.charset.Charset('utf-8'))
        
        if success:
            mail['Subject'] = "success "+jobname
        else:
            mail['Subject'] = "fail "+jobname
        #mail['From'] = "root@localhost"
        recipients = recipient[0]
        for r in recipient[1:]:
            recipients = recipients+", "+r
        mail['To'] = recipients
        
        server = smtplib.SMTP("localhost")
        server.sendmail(mail['from'], recipient, mail.as_string())
        server.quit()
    
    def syslog(self, success, jobname, recipient, msg):
        """
        Log message "SUCCESS/FAIL msg" to syslog.
        
        TODO: use "recipient" as log facility?
        """
        log.getLogger().debug("syslogging")
        if success:
            msg = "SUCCESS "+jobname+" "+msg
        else:
            msg = "FAIL    "+jobname+" "+msg
        
        syslog.syslog(msg)
