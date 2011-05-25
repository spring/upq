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
        results=self.query("SELECT VERSION()")
        for res in results:
            self.logger.info("MySQL server version: %s", res[0])
    def connect(self, databaseurl):
        self.cleanup()
        self.databaseurl = databaseurl
        self.engine = create_engine(self.databaseurl, encoding="utf-8", echo=False)
        self.logger.info("Opened DB connection.")
        self.meta=MetaData()
        """ TODO: use this?
        #Maybe this can be used later on...
        self.tbl_upqueue = Table('upqueue', metadata,
            Column('jobid', Integer, Sequence('jobid_seq'), primary_key=True),
            Column('jobname', String),
            Column('state', String),
            Column('pickle_blob', PickleType),
            Column('result', String),
            Column('result_msg', String),
            Column('ctime', DateTime),
            Column('start_time', DateTime),
            Column('end_time', DateTime),
        )
        self.meta.create_all(self.engine)
        """
        self.meta.bind = self.engine
    def query(self, query):
        self.logger.debug(query)
        return self.engine.execute(query)
    """
		insert values into tables, returns last insert id if primary key is autoincrement
    """
    def insert(self, table, values):
        strkeys=""
        strvalues=""
        if not self.tables.has_key(table): # load structure from table
            self.tables['table']=Table(table, self.meta, autoload=True)
        query=self.tables['table'].insert(values)
        s=Session(self.engine)
        try:
			s.execute(query)
        except IntegrityError as e:
			raise UpqDBIntegrityError("Integrity Error" + e.statement)
        finally:
            result=s.scalar("SELECT LAST_INSERT_ID()")
            s.close()
            self.logger.debug(str(query)+" id:"+str(result))
        return result
    def tbl_upqueue(self):
        return self.tbl_upqueue
    def cleanup(self):
        try:
            self.engine.close()
            self.logger.info("(%s) Closed MySQL connection.", self.thread)
        except:
            pass

