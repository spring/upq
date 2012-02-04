# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os.path
import logging
import logging.handlers

logger=None

def init_logging(conf):
	global logger

	if conf.has_key('loglevel'):
		loglevel = conf['loglevel'].upper()
	else:
		loglevel = 'INFO'
	if conf.has_key('logfile'):
		logfile = conf['logfile']
		if logfile[:2] == "./":
			# convert relative to absolute path
			logfile = os.path.realpath(os.path.dirname(__file__))+logfile[1:]
	else:
		filename=None

	if conf.has_key('logformat'):
		logformat = conf['logformat']
	else:
		logformat = "%(asctime)s %(levelname)-8s %(module)s.%(funcName)s:%(lineno)d %(message)s"

	logging.basicConfig(level=logging.__getattribute__(loglevel),
						format=logformat,
						filename=logfile,
						filemode='a')

	logger = logging.getLogger("upq")
	return logger

def getLogger(*args, **kwargs):
	return logging.getLogger(*args, **kwargs)

