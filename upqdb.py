# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# UpqDB: DB tool class

import log
import module_loader

from sqlalchemy import create_engine, Index, Table, Column, Integer, String,DateTime,PickleType, MetaData, ForeignKey, Sequence, UniqueConstraint
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import TEXT, INTEGER, BIGINT, DATETIME, CHAR, VARCHAR, TIMESTAMP


class UpqDBIntegrityError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class UpqDB():
	__shared_state = {}
	tables = {}

	def __init__(self):
		self.__dict__ = self.__shared_state
		self.logger = log.getLogger("upq")
	def version(self):
		try:
			results=self.query("SELECT VERSION()")
		except Exception:
			results=self.query("SELECT sqlite_version()")
		for res in results:
			self.logger.info("SQL version: %s", res[0])
	def connect(self, databaseurl, debug):
		self.cleanup()
		self.engine = create_engine(databaseurl, encoding="utf-8", echo=debug, pool_recycle=True)
		self.logger.info("Opened DB connection.")
		self.meta=MetaData()
		"""
		created with this + some editing:

		tables = ["upqueue",
			"file_mirror",
			"file_mirror_paths",
			"file_mirror_files",
			"springdata_archives",
			"springdata_categories",
			"springdata_depends",
			"springdata_startpos",
			"files",
			"filehash" ]
		meta=MetaData()
		meta.bind = UpqDB().engine
		for t in tables:
			tbl=Table(t, meta, autoload=True)
		pprint.pprint(meta.tables)
		"""
		self.tables['mirror']=Table('mirror', self.meta, #table with file mirrors
			Column('mid', INTEGER(display_width=10),  primary_key=True, nullable=False, autoincrement=True),
			Column('title', VARCHAR(length=64)),
			Column('description', TEXT()),
			Column('country', VARCHAR(length=64)),
			Column('ftp_url', VARCHAR(length=64)),
			Column('ftp_user', VARCHAR(length=64)),
			Column('ftp_pass', VARCHAR(length=64)),
			Column('ftp_dir', VARCHAR(length=64)),
			Column('ftp_passive', INTEGER(display_width=4)),
			Column('ftp_ssl', INTEGER(display_width=4)),
			Column('ftp_port', INTEGER(display_width=4)),
			Column('url_prefix', VARCHAR(length=64)), # prefix to files
			Column('url_daemon', VARCHAR(length=64)), # absolute url to daemon.php
			Column('mirror_size', INTEGER(display_width=11)), # maximum size of mirror
			Column('bandwidth_limit', INTEGER(display_width=11)), # upload speed limit in kb/s
			Column('status', INTEGER(display_width=4))) # 0=inactive, 1=active
		self.tables['mirror_file']=Table('mirror_file', self.meta, #table with files on file mirrors
			Column('mfid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=True),
			Column('fid', INTEGER(display_width=8)),
			Column('mid', INTEGER(display_width=4)), # mirror id
			Column('path', VARCHAR(length=1024)), # relative to (mfid.url_prefix) path
			Column('lastcheck', DATETIME(timezone=False)), # last time checksum/existence was checked
			Column('status', INTEGER(display_width=4)), # 0=inactive, 1 = active, 2 = marked for recheck, 3 = broken
			UniqueConstraint('fid', 'mid'))
		self.tables['file']=Table('file', self.meta, #all known files
			Column('fid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=True), #primary key of file
			Column('uid', INTEGER(display_width=10), nullable=False), # owner uid of file
			Column('filename', VARCHAR(length=255), nullable=False, unique=True), # filename (without path)
			Column('path', VARCHAR(length=1024), nullable=False), # relative path where file is (without filename!)
			Column('size', INTEGER(display_width=11), nullable=False), # file size
			Column('status', INTEGER(display_width=11), nullable=False), # 0=inactive, 1 = active, 2 = marked for recheck, 3 = broken
			Column('timestamp', TIMESTAMP(timezone=False)),
			Column('torrent', INTEGER(display_width=1)), # 1 = torrent created, 0 = not
			Column('md5', CHAR(length=32), unique=True),
			Column('sha1', CHAR(length=40)),
			Column('sha256', CHAR(length=64)),
			Column('name', VARCHAR(length=256)), #spring name of this file
			Column('version', VARCHAR(length=256)), #spring version of this file
			Column('cid', INTEGER(display_width=11)), #category of this file: game/map
			Column('sdp', VARCHAR(length=32),nullable=False, unique=True), #for this file
			Column('descriptionuri', VARCHAR(length=1024)),
			Column('metadata', TEXT()),
			UniqueConstraint('name', 'version'))
		self.tables['image_file']=Table('image_file', self.meta,
			Column('iid', INTEGER(display_width=10), nullable=False), #id of the image
			Column('fid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=True),
			Column('filename', VARCHAR(length=255), nullable=False))
		self.tables['image']=Table('image', self.meta,
			Column('iid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=True),
			Column('md5', CHAR(length=32))) #md5 = path
		self.tables['tag']=Table('tag', self.meta,
			Column('tid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=True),
			Column('fid', INTEGER(display_width=10)),
			Column('tag', VARCHAR(length=256), unique=True))
		self.tables['categories']=Table('categories', self.meta, # file categories
			Column('cid', INTEGER(display_width=11), primary_key=True, nullable=False, autoincrement=True),
			Column('name', VARCHAR(length=24), nullable=False))
		self.tables['file_depends']=Table('file_depends', self.meta,
			Column('fid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=False),
			Column('depends_fid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=False), #id of other file, if null(couldn't be resolved), use depends_string
			Column('depends_string', VARCHAR(length=64), nullable=False))
		self.tables['upqueue']=Table('upqueue', self.meta,
			Column('jobid', INTEGER(display_width=11), primary_key=True, nullable=False, autoincrement=True),
			Column('jobname', VARCHAR(length=255), nullable=False),
			Column('status', INTEGER(display_width=10)), # 0 = finished, 1 = running, 2 = new, 3 = broken/failed
			Column('jobdata', TEXT(), nullable=False),
			Column('result_msg', VARCHAR(length=255)),
			Column('ctime', TIMESTAMP(timezone=False)),
			Column('start_time', TIMESTAMP(timezone=False)),
			Column('end_time', TIMESTAMP(timezone=False)))
		self.tables['sf_sync']=Table('sf_sync', self.meta,
			Column('sid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=True),
			Column('command', INTEGER(display_width=10), nullable=False, autoincrement=False), #0=update 1=delete
			Column('fid', INTEGER(display_width=10), nullable=False, autoincrement=False)) #file id which was changed

		try:
			self.meta.create_all(self.engine)
		except:
			raise Exception("Unable to initialize database %s" %(databaseurl))
		self.meta.bind = self.engine
	def query(self, query):
		#self.logger.debug(query)
		res=None
		try:
			res=self.engine.execute(query)
		except Exception as e:
			self.logger.error("Error %s executing query %s" % (str(e), str(query)))
		return res
	"""
		insert values into tables, returns last insert id if primary key is autoincrement
	"""
	def insert(self, table, values):
		strkeys=""
		strvalues=""
		if not self.tables.has_key(table): # load structure from table
			self.tables[table]=Table(table, self.meta, autoload=True)
		for key in values.keys():
			if values[key].__class__==str:
				values[key]=values[key].replace("'", "\'")
		query=self.tables[table].insert(values)
		s=Session(self.engine)
		try:
			s.execute(query)
		except IntegrityError as e:
			raise UpqDBIntegrityError("Integrity Error" + e.statement + str(values))
		finally:
			try:
				result=s.scalar("SELECT LAST_INSERT_ID()")
			except:
				result=s.scalar("SELECT last_insert_rowid()")
			s.close()
			#self.logger.debug("%s (%s) id:%s", query, values, result)
		return result
	def tbl_upqueue(self):
		return self.tbl_upqueue
	def cleanup(self):
		try:
			self.engine.close()
			self.logger.info("(%s) Closed MySQL connection.", self.thread)
		except:
			pass
	def now(self):
		return func.now()

