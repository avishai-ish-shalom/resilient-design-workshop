#!/usr/bin/env python

from flask import Flask, g, abort, request, make_response, Response
from flask import jsonify
from psycopg2 import IntegrityError

from PIL import ImageFilter, Image
from uuid import uuid4
import dao
from typing import Tuple
from io import BytesIO
import time, random, os
import json
import logging

logging.config.dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

try:
    with open('./config.json', 'r') as f:
        config = json.load(f)
        print('Configuration loaded')
except Exception:
    config = {'db_pool_timeout': 10, 'db_pool_connections': 2}

def _wait_for(func):
    res = None
    while not res:
        try:
            res = func()
        except Exception:
            time.sleep(0.1)
    return res

db_host = os.environ.get('DB_HOST', 'localhost')

app = Flask('resilient-design')

db_pool = _wait_for(lambda: dao.get_connection_pool(config['db_pool_connections'], config['db_pool_connections'], config['db_pool_timeout'], db_host, 'resilient-design', 'app', 'password'))

@app.route('/')
def home():
    return jsonify(status='ok')


@app.route('/sleep')
def sleep():
    duration = float(request.args.get('time', 0.2))
    jitter = float(request.args.get('jitter', ))
    delta = (random.random() - 0.5) * jitter
    sleep_time = duration + delta
    app.logger.info('Sleeping for %f seconds', sleep_time)
    time.sleep(sleep_time)
    return 'ZZZZZZZ\n'

@app.route('/image/<id>')
def get_image(id):
    with dao.with_cursor(db_pool) as cursor:
        img_blob = dao.get_image(cursor, str(id))

    if img_blob is None:
        abort(404)
    else:
        img = Image.open(BytesIO(img_blob))

        size = parse_size(request.args.get('size', ''))
        if size:
            img = resize(img, size)

        blur = request.args.get('blur') is not None
        if blur:
            img = img.filter(ImageFilter.BLUR)

        resp = make_img_response(img)
        return resp


@app.route('/image/', methods=['PUT'])
def put_image():
    if not request.data:
        abort(400)
    saved_id = _save_img(str(uuid4()), request.data)
    if saved_id:
        return saved_id
    else:
        return make_response('Could not save image\n', 500)


@app.route('/image/<image_id>', methods=['POST'])
def post_image(image_id):
    if not request.data:
        abort(400)
    
    try:
        saved_id = _save_img(image_id, request.data)
        if saved_id:
            return saved_id
        else:
            return make_response('Could not save image\n', 500)
    except IntegrityError:
        return make_response('Image already exists\n', 409)


def _save_img(image_id, img):
    with dao.with_cursor(db_pool) as cursor:
        if dao.save_image(cursor, image_id, img):
            return image_id



@app.route('/image/<image_id>', methods=['DELETE'])
def delete_image(image_id):
    with dao.with_cursor(db_pool) as c:
        deleted = dao.delete_image(c, image_id)

    if deleted:
        return make_response('DELETED\n', 204)
    else:
        abort(404)

@app.cli.command('initdb')
def init_db():
    with dao.with_cursor(db_pool) as c:
        dao.init_db(c)

def resize(img: Image, size: Tuple[int, int]) -> Image:
    return img.resize(size) if size else img

def parse_size(size_spec: str) -> Tuple[int, int]:
    try:
        res = tuple(map(int, size_spec.split('x', 1)))
        return res if len(res) == 2 else None
    except ValueError:
        return None

def make_img_response(img: Image) -> Response:
    b = BytesIO()
    img.save(b, 'PNG')
    resp = make_response(b.getvalue())
    resp.headers['Content-Type'] = 'image/png'
    return resp