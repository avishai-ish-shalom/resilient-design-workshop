from psycopg2 import Binary
from psycopg2.pool import PoolError
from connection_pool import WaitableThreadedConnectionPool
from contextlib import contextmanager
from logging import Logger
from statsd import StatsClient
import time

statsd = StatsClient(prefix='host.app')
logger = Logger('dao')


def get_connection_pool(minconn, maxconn, timeout, host, database, user, password):
    return WaitableThreadedConnectionPool(minconn, maxconn,
                                    database=database,
                                    host=host,
                                    user=user,
                                    password=password,
                                    timeout=timeout)


@contextmanager
def with_cursor(pool):
    s1 = time.time()

    try:
        connection = pool.getconn()
    except PoolError as e:
        logger.error('Error getting DB connection from pool: %s', e, exc_info=1)
        raise e

    statsd.timing('db_pool.get_conn', (time.time() - s1)*1000)

    with connection, connection.cursor() as c:
        yield c
    pool.putconn(connection)


def init_db(c):
    c.execute('CREATE TABLE image (id char(37) PRIMARY KEY, data bytea);')


def get_image(cursor, image_id):
    cursor.execute('SELECT data FROM image WHERE id=%s', (image_id,))
    data = cursor.fetchone()
    if data:
        return data[0]


def save_image(cursor, image_id, image):
    cursor.execute('INSERT INTO image (id, data) VALUES(%s, %s)', (image_id, Binary(image)))
    return cursor.rowcount == 1

def delete_image(cursor, image_id):
    cursor.execute('DELETE FROM image WHERE id=%s', (image_id,))
    return cursor.rowcount == 1