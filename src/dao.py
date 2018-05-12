from psycopg2 import Binary
from psycopg2.pool import ThreadedConnectionPool 
from contextlib import contextmanager

def get_connection_pool(minconn, maxconn, host, database, user, password):
    return ThreadedConnectionPool(minconn, maxconn,
                                    database=database,
                                    host=host,
                                    user=user,
                                    password=password)


@contextmanager
def with_cursor(pool):
    try:
        connection = pool.getconn()
        with connection, connection.cursor() as c:
            yield c
    finally:
        pool.putconn(connection)


def init_db(c):
    c.execute('CREATE TABLE image (id char(37) PRIMARY KEY, data bytea);')


def get_image(cursor, image_id):
    cursor.execute('SELECT data FROM image WHERE id=%s', (image_id,))
    data = cursor.fetchone()
    return data[0]


def save_image(cursor, image_id, image):
    cursor.execute('INSERT INTO image (id, data) VALUES(%s, %s)', (image_id, Binary(image)))
    return cursor.rowcount == 1

def delete_image(cursor, image_id):
    cursor.execute('DELETE FROM image WHERE id=%s', (image_id,))
    return cursor.rowcount == 1