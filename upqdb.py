# This file is part of the "upq" program used on springfiles.com to manage file
# uploads, mirror distribution etc. It is published under the GPLv3.
#
#Copyright (C) 2011 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# UpqDB: DB tool class
#
# UpqDB is kind of a factory for UpqThreadedDB objects, that do the real work.
#
# I had lots of problems with lost mysql connections and invalid cursors. Took
# a while until I realized that MySQLdb is not thread safe! :(
# Then I couldn't find a connection-pool library, so I thought it'd just give
# each thread its own connection (it's waisting ressources I know...), but that
# didn't work either - not sure why, I guess MySQL just doesn't want so much
# connections - no idea...? Anyway - now things just make new connections when
# old ones are broken (probably breaking another connection).
# TODO: db connection pool

import cPickle
import MySQLdb

import log
import module_loader

ori_defaulterrorhandler = None

def retry_errorhandler(cursor, errorclass, errorvalue):
    """
    Trys to reconnect on disconnect.
    If not successfull calls the original defaulterrorhandler()
    """
    global ori_defaulterrorhandler
    
    log.getLogger().error("(%s) cursor=%s errorclass=%s errorvalue=%s",
                          cursor.thread, cursor, errorclass, errorvalue)
    if errorvalue[0] == 2006 or errorvalue[0] == 2013:
        log.getLogger().info("(%s) DB connection was interrupted, "\
                             +"reconnecting...", cursor.thread)
        UpqDB().getdb(cursor.thread).connect()
    else:
        log.getLogger().error("(%s) unknown errorvalue, calling "\
                              +"defaulterrorhandler()", cursor.thread)
        ori_defaulterrorhandler(UpqDB().getdb(cursor.thread).conn, cursor,
                                errorclass, errorvalue)

class UpqDB():
    """
    Factory that creates a UpqThreadedDB obj with a DB connection per thread
    (MySQLdb is not thread safe)
    """
    # Borg design pattern (pythons cooler singleton)
    __shared_state = {}
    
    # this dict holds an UpqThreadedDB-obj per thread
    utdbs = {}
    
    def __init__(self):
        self.__dict__ = self.__shared_state
        self.logger = log.getLogger("upq")
    
    def set_connection(self, host, user, password, db):
        self.host = host
        self.user = user
        self.password = password
        self.db = db
    
    def getdb(self, thread_id):
        try:
            return self.utdbs[thread_id]
        except KeyError:
            utdb = UpqThreadedDB(self.host, self.user, self.password, self.db,
                                 thread_id)
            utdb.paths = self.paths
            self.utdbs[thread_id] = utdb
            return utdb

class UpqThreadedDB():
    def __init__(self, host, user, password, db, thread_id):
        global ori_defaulterrorhandler
        
        self.host     = host
        self.user     = user
        self.password = password
        self.db       = db
        self.thread   = thread_id
        
        self.logger   = log.getLogger("upq")
        
        self.connect()
    
    def connect(self):
        self.cleanup()
        
        try:
            self.conn = MySQLdb.connect (host   = self.host,
                                         user   = self.user,
                                         passwd = self.password,
                                         db     = self.db)
            self.logger.info("(%s) Opened MySQL connection.", self.thread)
        except MySQLdb.Error, e:
            self.logger.error("Could not connect to DB: '%s'", e)
            raise Exception("Could not connect to DB: '%s'"%e)
        
        #if not ori_defaulterrorhandler:
        ori_defaulterrorhandler = self.conn.errorhandler
        self.conn.errorhandler = retry_errorhandler
    
    def get_cursor(self, cursorclass=None):
        cursor = self.conn.cursor(cursorclass)
        try:
            cursor.execute("SELECT VERSION()")
        except:
            self.logger.error("(%s) DB connection seems broken, will retry...",
                              self.thread)
            self.connect()
            cursor = self.conn.cursor(cursorclass)
        cursor.thread = self.thread
        return cursor
    
    def version(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT VERSION()")
        row = cursor.fetchone()
        self.logger.info("MySQL server version: '%s'", row[0])
        cursor.close()
    
    def cleanup(self):
        try:
            self.conn.close()
            self.logger.info("(%s) Closed MySQL connection.", self.thread)
        except:
            pass
    
    def get_from_files(self, fileid, what):
        """
        fileid  : (int   ) table files, column fid
        what    : (string) table files, column name
        returns : content of cell at table files, fid x column
        """
        
        cursor = self.get_cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT %s FROM files WHERE fid = %s"%(what, fileid))
        result = cursor.fetchone()
        cursor.close()
        if result:
            return result[what]
        else:
            return ""
    
    def get_from_filehashes(self, fileid):
        """
        fileid  : (int) table filehash, column fid
        returns : {'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}
        """
        
        cursor = self.get_cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM filehash WHERE fid = %s", fileid)
        result = cursor.fetchone()
        cursor.close()
        if not result: result = ""
        return result
    
    def persist_job(self, job):
        """
        Serializes a UpqJob and its state in DB.
        
        job     : UpqJob object to serialize
        returns : (int) jobid
        """
        
        pickled = cPickle.dumps(job, -1)
        
        cursor = self.get_cursor()
        cursor.execute("INSERT INTO upqueue (jobname, state, pickle_blob) "\
                       +"VALUES (%s, %s, %s)", (job.jobname, 'new', pickled))
        job.jobid = int(cursor.lastrowid)
        cursor.close()
    
    def update_state(self, job, newstate):
        """
        Change the state of a job in the DB to "newstate"
        
        job     : UpqJob object to change
        newstate: (str) new state to save to DB
        """
        cursor = self.get_cursor()
        cursor.execute("UPDATE upqueue SET state = %s WHERE jobid = %s",
                       (newstate, job.jobid))
        cursor.close()
    
    def set_time(self, job, column):
        """
        Change the time of a job in the "column" to "NOW()"
        
        job     : UpqJob object to change
        column  : (str) column to change (ctime,, start_time, end_time)
        """
        cursor = self.get_cursor()
        cursor.execute("UPDATE upqueue SET %s = NOW() WHERE jobid = %d"%
                       (column, job.jobid))
        cursor.close()
    
    def set_result(self, job):
        """
        Set the result of a job in the DB
        
        job     : UpqJob object
        """
        cursor = self.get_cursor()
        cursor.execute("UPDATE upqueue SET result = %(result)s, "\
                       +"result_msg = %(result_msg)s WHERE jobid = %(jobid)s",
        {'result': int(job.result['success']),
         'result_msg': job.result['msg'],
         'jobid': job.jobid})
        cursor.close()
    
    def revive_jobs(self):
        """
        Fetches all jobs from DB that are in state "new" or "running", and
        recreates the objects from its pickled representation.
        
        returns  : list of alive, unqueued jobs
        """
        
        cursor = self.get_cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM upqueue WHERE state = 'new' OR "\
                       +"state = 'running'")
        result_set = cursor.fetchall()
        cursor.close()
        jobs = []
        for line in result_set:
            module_loader.load_module(line['jobname'], self.paths['jobs_dir'])
            obj = cPickle.loads(line['pickle_blob'])
            obj.jobid = int(line['jobid'])
            obj.thread = "Thread-revived-UpqJob"
            jobs.append(obj)
        self.logger.debug("revived jobs='%s'", jobs)
        return jobs
        
    