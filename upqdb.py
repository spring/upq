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

from sqlalchemy import create_engine, Table, Column, Integer, String,DateTime,PickleType, MetaData, ForeignKey, Sequence
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
		self.tables['file_mirror']=Table('file_mirror', self.meta,
			Column('fmid', INTEGER(display_width=10),  primary_key=True, nullable=False, autoincrement=True),
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
			Column('url_prefix', VARCHAR(length=64)),
			Column('url_deamon', VARCHAR(length=64)),
			Column('uid', INTEGER(display_width=4)),
			Column('mirror_size', INTEGER(display_width=11)),
			Column('fill', BIGINT(display_width=20)),
			Column('bandwidth_limit', INTEGER(display_width=11)),
			Column('active', INTEGER(display_width=4)),
			Column('flat', INTEGER(display_width=4)),
			Column('dynamic', INTEGER(display_width=4)),
			Column('mbw', BIGINT(display_width=20)),
			Column('mbw_month', INTEGER(display_width=4)),
			Column('tbw', BIGINT(display_width=20)),
			Column('created', DATETIME(timezone=False)),
			Column('changed', DATETIME(timezone=False)),
			Column('lastupload', DATETIME(timezone=False),  nullable=False))
		self.tables['file_mirror_files']=Table('file_mirror_files', self.meta,
			Column('fmfid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=True),
			Column('fmid', INTEGER(display_width=4)),
			Column('fid', INTEGER(display_width=8)),
			Column('path', VARCHAR(length=64)),
			Column('size', INTEGER(display_width=11), nullable=False),
			Column('md5', VARCHAR(length=64)),
			Column('md5check', DATETIME(timezone=False)),
			Column('active', INTEGER(display_width=4)),
			Column('changed', DATETIME(timezone=False)))
		self.tables['file_mirror_paths']=Table('file_mirror_paths', self.meta,
			Column('fmpid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=True),
			Column('fmid', INTEGER(display_width=4)),
			Column('path', VARCHAR(length=64), nullable=False)),
		self.tables['filehash']=Table('filehash', self.meta,
			Column('fid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=False),
			Column('md5', CHAR(length=32)),
			Column('sha1', CHAR(length=40)),
			Column('sha256', CHAR(length=64)))
		self.tables['files']=Table('files', self.meta,
			Column('fid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=True),
			Column('uid', INTEGER(display_width=10), nullable=False ),
			Column('filename', VARCHAR(length=255), nullable=False),
			Column('filepath', VARCHAR(length=255), nullable=False),
			Column('filemime', VARCHAR(length=255), nullable=False),
			Column('filesize', INTEGER(display_width=10), nullable=False, ),
			Column('status', INTEGER(display_width=11), nullable=False),
			Column('timestamp', TIMESTAMP(timezone=False)),
			Column('origname', VARCHAR(length=255), nullable=False))
		self.tables['springdata_archives']=Table('springdata_archives', self.meta,
			Column('fid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=False),
			Column('name', VARCHAR(length=256)),
			Column('version', VARCHAR(length=256)),
			Column('cid', INTEGER(display_width=11)),
			Column('sdp', VARCHAR(length=1024)))
		self.tables['springdata_archivetags']=Table('springdata_archivetags', self.meta,
			Column('fid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=False),
			Column('tag', VARCHAR(length=256), unique=True))
		self.tables['springdata_categories']=Table('springdata_categories', self.meta,
			Column('cid', INTEGER(display_width=11), primary_key=True, nullable=False, autoincrement=True),
			Column('name', VARCHAR(length=24), nullable=False))
		self.tables['springdata_depends']=Table('springdata_depends', self.meta,
			Column('fid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=False),
			Column('depends', INTEGER(display_width=10), primary_key=True, nullable=False),
			Column('depends_string', VARCHAR(length=64), nullable=False))
		self.tables['springdata_startpos']=Table('springdata_startpos', self.meta,
			Column('fid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=False),
			Column('id', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=False),
			Column('x', INTEGER(display_width=10), nullable=False),
			Column('z', INTEGER(display_width=10), nullable=False))
		self.tables['upqueue']=Table('upqueue', self.meta,
			Column('jobid', INTEGER(display_width=11), primary_key=True, nullable=False, autoincrement=True),
			Column('jobname', VARCHAR(length=255), nullable=False),
			Column('state', VARCHAR(length=32), nullable=False),
			Column('jobdata', TEXT(), nullable=False),
			Column('result', INTEGER(display_width=1)),
			Column('result_msg', VARCHAR(length=255)),
			Column('ctime', TIMESTAMP(timezone=False)),
			Column('start_time', TIMESTAMP(timezone=False)),
			Column('end_time', TIMESTAMP(timezone=False)))
		try:
			self.meta.create_all(self.engine)
		except:
			raise Exception("Unable to initialize database %s" %(databaseurl))
		self.meta.bind = self.engine
	def query(self, query):
		#self.logger.debug(query)
		return self.engine.execute(query)
	"""
		insert values into tables, returns last insert id if primary key is autoincrement
	"""
	def insert(self, table, values):
		strkeys=""
		strvalues=""
		if not self.tables.has_key(table): # load structure from table
			self.tables[table]=Table(table, self.meta, autoload=True)
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

