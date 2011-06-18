# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# helper module
# 

import imp
import sys

from upqconfig import UpqConfig

def load_module(name):
    """
    Returns the class in the module "name" located in jobs_dir
    """
    try:
        return sys.modules[name].__getattribute__(name[0].upper()+name[1:])
    except KeyError:
        pass
    fp, pathname, description = imp.find_module(name, [UpqConfig().paths['jobs_dir'],])
    
    try:
        module = imp.load_module(name, fp, pathname, description)
        return module.__getattribute__(name[0].upper()+name[1:])
    finally:
        # Since we may exit via an exception, close fp explicitly.
        try:
            if fp: fp.close()
        except:
            pass
