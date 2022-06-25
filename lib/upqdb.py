# This file is part of the "upq" program used on springfiles.springrts.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# UpqDB: DB tool class

import logging

from sqlalchemy import create_engine, Index, Table, Column, Integer, Float, String,DateTime,PickleType, MetaData, ForeignKey, Sequence, UniqueConstraint
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import TEXT, MEDIUMTEXT, INTEGER, BIGINT, DATETIME, CHAR, VARCHAR, TIMESTAMP, FLOAT


cats = {}
def getCID(db, category):
	global cats
	if category in cats:
		return cats[category]
	res = db.query("SELECT cid from categories WHERE name='%s'" % (category))
	cats[category]=res.first()[0] # cache result
	return cats[category]

def escape(string, whitelist=set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789-._%*?")):
	return ''.join(c for c in string if c in whitelist)

def now():
	return func.now()

class UpqDBIntegrityError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class UpqDB():
	__shared_state = {}
	tables = {}

	def version(self):
		try:
			results=self.query("SELECT VERSION()")
		except Exception:
			results=self.query("SELECT sqlite_version()")
		for res in results:
			logging.info("SQL version: %s", res[0])

	def __init__(self, databaseurl, debug):
		self.engine = create_engine(databaseurl, encoding="utf-8", echo=debug, pool_recycle=True)
		logging.info("Opened DB connection.")
		self.meta=MetaData()
		self.tables['mirror']=Table('mirror', self.meta, #table with file mirrors
			Column('mid', INTEGER(display_width=10),  primary_key=True, nullable=False, autoincrement=True),
			Column('title', VARCHAR(length=64)),
			Column('description', TEXT()),
			Column('country', VARCHAR(length=64)),
			Column('url_prefix', VARCHAR(length=64)), # prefix to files
			Column('url_daemon', VARCHAR(length=64)), # absolute url to daemon.php
			Column('mirror_size', INTEGER(display_width=11)), # maximum size of mirror
			Column('bandwidth_limit', INTEGER(display_width=11)), # upload speed limit in kb/s
			Column('status', INTEGER(display_width=4))) # 0=inactive, 1=active
		self.tables['mirror_file']=Table('mirror_file', self.meta, #table with files on file mirrors
			Column('mfid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=True),
			Column('fid', Integer, ForeignKey("file.fid")),
			Column('mid', INTEGER(display_width=4), ForeignKey("mirror.mid")), # mirror id
			Column('path', VARCHAR(length=1024)), # relative to (mfid.url_prefix) path
			Column('lastcheck', DATETIME(timezone=False)), # last time checksum/existence was checked
			Column('status', INTEGER(display_width=4)), # 0=inactive, 1 = active, 2 = marked for recheck, 3 = broken, 4 = archived (=possible deleted)
			UniqueConstraint('fid', 'mid'))
		self.tables['file']=Table('file', self.meta, #all known files
			Column('fid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=True), #primary key of file
			Column('uid', INTEGER(display_width=10), default=0, nullable=False), # owner uid of file
			Column('filename', VARCHAR(length=255), nullable=False, unique=False), # filename (without path)
			Column('path', VARCHAR(length=1024), default='', nullable=False), # relative path where file is (without filename!)
			Column('size', INTEGER(display_width=11), nullable=False), # file size
			Column('status', INTEGER(display_width=11), nullable=False), # 0=inactive, 1 = active, 2 = marked for recheck, 3 = broken
			Column('timestamp', TIMESTAMP(timezone=False)),
			Column('md5', CHAR(length=32), unique=True),
			Column('sha1', CHAR(length=40)),
			Column('sha256', CHAR(length=64)),
			Column('name', VARCHAR(length=256)), #spring name of this file
			Column('version', VARCHAR(length=256)), #spring version of this file
			Column('cid', INTEGER(display_width=11)), #category of this file: game/map
			Column('sdp', VARCHAR(length=32),nullable=True, unique=True), #for this file
			Column('metadata', MEDIUMTEXT()),
			Column('name_without_version', VARCHAR(length=256),nullable=True), #spring name without the version part 
			Column('map_width', INTEGER(display_width=11),nullable=True), #map width
			Column('map_height', INTEGER(display_width=11),nullable=True), #map height
			Column('version_sort_number', FLOAT(),nullable=True), # version number for easier comparison/sorting
			UniqueConstraint('name', 'version', 'cid'),
			UniqueConstraint('filename', 'cid')
			)
		self.tables['file_keyword']=Table('file_keyword', self.meta, #table with keyword strings associated with each file
			Column('fid', Integer, ForeignKey("file.fid")), # file fid, delete cascade added by external SQL
			Column('keyword', VARCHAR(length=128),nullable=False), # keyword
			UniqueConstraint('fid', 'keyword'))

		#self.tables['rapidrepo']=Table('rapidrepo', self.meta,
		#	Column('rid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=True),
		#	Column('baseurl', VARCHAR(length=32), unique=True, nullable=False) # i.e. https://repos.springrts.com/ba/

		#self.tables['rapid']=Table('rapid', self.meta,
		#	Column('rid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=True),
		#	Column('fid', Integer, ForeignKey("file.fid"), nullable=True, unique=True),
		#	Column('repo', Integer, ForeignKey("rapid-repo.rid"), nullable=True, unique=True),
		#	Column('sdp', VARCHAR(length=32), unique=True),
		#	Column('timestamp', TIMESTAMP(timezone=False)),

		self.tables['tag']=Table('tag', self.meta,
			Column('tid', INTEGER(display_width=10), primary_key=True, nullable=False, autoincrement=True),
			Column('fid', Integer, ForeignKey("file.fid"), nullable=False),
			Column('tag', VARCHAR(length=128), unique=True))
		self.tables['categories']=Table('categories', self.meta, # file categories
			Column('cid', INTEGER(display_width=11), primary_key=True, nullable=False, autoincrement=True),
			Column('name', VARCHAR(length=24), nullable=False))
		self.tables['file_depends']=Table('file_depends', self.meta,
			Column('fid', Integer, ForeignKey("file.fid")),
			Column('depends_fid', Integer, ForeignKey("file.fid"), nullable=True), #id of other file, if null(couldn't be resolved), use depends_string
			Column('depends_string', VARCHAR(length=64), nullable=False),
			UniqueConstraint('fid', 'depends_string'))

		try:
			self.meta.create_all(self.engine)
		except Exception as e:
			raise Exception("Unable to initialize database %s:%s" %(databaseurl, e))
		self.meta.bind = self.engine

	def query(self, query):
		#logging.debug(query)
		res=None
		try:
			s = Session(self.engine)
			res=s.execute(query)
			s.commit()
		except Exception as e:
			logging.error("Error %s executing query %s" % (str(e), str(query)))
		return res

	def insert(self, table, values):
		"""
			insert values into tables, returns last insert id if primary key is autoincrement
		"""
		if not table in self.tables: # load structure from table
			self.tables[table]=Table(table, self.meta, autoload=True)
		for key in values.keys():
			if values[key].__class__==str:
				values[key]=values[key].replace("'", "\'")
		query=self.tables[table].insert(values)
		s=Session(self.engine)
		try:
			s.execute(query)
			s.commit()
		except IntegrityError as e:
			raise UpqDBIntegrityError("Integrity Error" + e.statement + str(values))
		finally:
			try:
				result=s.scalar("SELECT LAST_INSERT_ID()")
			except:
				result=s.scalar("SELECT last_insert_rowid()")
			s.close()
			logging.debug("%s (%s) id:%s", query, values, result)
		return result


