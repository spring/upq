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
        self.engine = create_engine(self.databaseurl, encoding="utf-8", echo=True)
        self.logger.info("(%s) Opened DB connection.")
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
    def insert2(self, query):
        s=Session(self.engine)
        print query
        s.execute(query)
        res=s.scalar("SELECT LAST_INSERT_ID()")
        s.close()
        return res
    def insert(self, table, values):
        strkeys=""
        strvalues=""
        if not self.tables.has_key(table): # load structure from table
            self.tables['table']=Table(table, self.meta, autoload=True)
        query=self.tables['table'].insert(values)
        s=Session(self.engine)
        s.execute(query)
        result=s.scalar("SELECT LAST_INSERT_ID()")
        s.close()
        return result
    def tbl_upqueue(self):
        return self.tbl_upqueue
    def cleanup(self):
        try:
            self.engine.close()
            self.logger.info("(%s) Closed MySQL connection.", self.thread)
        except:
            pass

#TODO: remove all below this (move directly into files / use directly sql queries there / or use more sqlalchemy features)

    def get_from_files(self, fileid, what):
        """
        fileid  : (int   ) table files, column fid
        what    : (string) table files, column name
        returns : content of cell at table files, fid x column
        """

        result=self.query("SELECT %s FROM files WHERE fid = %s"%(what, fileid))
        if result:
            return result[what]
        else:
            return ""

    def set_result(self, job):
        """
        Set the result of a job in the DB

        job     : UpqJob object
        """
        result=self.query("UPDATE upqueue SET result = %(result)s, "\
        +"result_msg = %(result_msg)s WHERE jobid = %(jobid)s",
        {'result': int(job.result['success']),
        'result_msg': job.result['msg'],
        'jobid': job.jobid})
        cursor.close()

    def get_remote_hash_url(self, fmid):
        """
        Fetch URL of hash script for give file mirror

        returns: (str) URL to "deamon.php"
        """

        result=self.query("SELECT url_prefix, url_deamon FROM file_mirror WHERE fmid = %s", fmid)
        result = cursor.fetchone()
        cursor.close()
        if not result:
            return ""
        else:
            return result['url_prefix']+"/"+result['url_deamon']

    def get_remote_file_hash(self, fmfid=0, fmid=0, fid=0):
        """
        Fetch a row from table file_mirror_files (remote file hashes)

        Either fmfid or fid AND fmid must be set!

        returns: (dict) a row from file_mirror_files
        """
        if fmfid:
            where = "fmfid = %s"%fmfid
        elif fmid != 0 and fid != 0:
            where = "fmid = %s AND fid = %s"%(fmid, fid)
        else:
            self.logger.debug("This func must be called with either fmfid!=0 or fid!=0 AND fmid!=0.")
            return {}
        result=self.query("SELECT * FROM file_mirror_files WHERE %s"%where)
        result = cursor.fetchone()
        cursor.close()
        if not result:
            return {}
        else:
            return result

