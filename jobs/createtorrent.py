# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#called with fileid, extracts/inserts metadata
#calls upload

from upqjob import UpqJob
from upqdb import UpqDB,UpqDBIntegrityError
from upqconfig import UpqConfig

import sys
import os
import shutil

metalinkpath=os.path.join(UpqConfig().paths['jobs_dir'],'metalink')
sys.path.append(metalinkpath)

import metalink

class Createtorrent(UpqJob):
	def check(self):
		if not 'fid' in self.jobdata:
			self.msg("fid not specified")
			return False

		results=UpqDB().query("SELECT * FROM file WHERE fid=%s and status=1" % (int(self.jobdata['fid'])))
		res=results.first()
		if res == None:
			self.msg("fid not found")
			return False
		id=self.enqueue_job()
		return True
	def run(self):
		fid=int(self.jobdata['fid'])
		results=UpqDB().query("SELECT filename, path, sdp FROM file WHERE fid=%d AND status=1" % fid)
		res=results.first()
		#filename of the archive to be scanned
		filename=res['filename'] # filename only (no path info)
		absfilename=os.path.join(UpqConfig().paths['files'], res['path'], res['filename']) # absolute filename
		torrent=os.path.join(UpqConfig().paths['metadata'], res['sdp']+ ".torrent" )
		if not os.path.exists(absfilename):
			self.msg("File doesn't exist: %s" %(absfilename))
			return False

		res=self.create_torrent(absfilename, torrent)
		if res:
			UpqDB().query("UPDATE file SET torrent='%s' WHERE fid=%s" %(os.path.basename(torrent), fid))
		return res

	def create_torrent(self, filename, output):
		if os.path.isdir(filename):
			self.logger.debug("[skip] " +filename + "is a directory, can't create torrent")
			return False
		if os.path.isfile(output):
			self.logger.debug("[skip] " +output + " already exists, skipping...")
			return True
		metalink._opts = { 'overwrite': False }
		filesize=os.path.getsize(filename)
		torrent = metalink.Torrent(filename)
		m = metalink.Metafile()
		m.hashes.filename=filename
		if not m.scan_file(filename, True, 255, 1):
			self.msg("Error scanning file %s" % (filename))
			return False
		
		m.hashes.get_multiple('ed2k')
		torrent_options = {'files':[[metalink.encode_text(filename), int(filesize)]],
			'piece length':int(m.hashes.piecelength),
			'pieces':m.hashes.pieces,
			'encoding':'UTF-8',
			}
		data=torrent.create(torrent_options)
		if not isinstance(data, basestring):
			self.msg("Error in creating torrent file: %s" % (str(data)))
			return False
		tmp=output+".tmp"
		f=open(tmp,"wb")
		f.write(data)
		f.close()
		shutil.move(tmp,output)
		os.chmod(output, int("0444",8))
		self.logger.debug("[created] " +output +" ok")
		return True
