from psycopg2.pool import ThreadedConnectionPool, PoolError
import threading
from functools import partial

class WaitableThreadedConnectionPool(ThreadedConnectionPool):
    def __init__(self, minconn, maxconn, *args, **kwargs):
        self._timeout = kwargs.get('timeout', 1)
        del kwargs['timeout']
        super().__init__(minconn, maxconn, *args, **kwargs)
        self._cv = threading.Condition(self._lock)
    
    def getconn(self, key=None):
        with self._cv:
            conn = self._cv.wait_for(partial(self._getconn_no_exc, key), self._timeout)
            if isinstance(conn, Exception):
                raise conn
            else:
                return conn
       
    def _getconn_no_exc(self, key):
        try:
            return self._getconn(key)
        except PoolError as e:
            return e