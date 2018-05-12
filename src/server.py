#!/usr/bin/env python

from flask import Flask, g, abort, request, make_response, Response
from flask import jsonify

from circonusapi import circonusapi
from circonusapi import config
from PIL import ImageFilter, Image
from uuid import uuid4
import dao
from typing import Tuple
from io import BytesIO

c = config.load_config()

app = Flask('resilient-design')

db_pool = dao.get_connection_pool(1, 2, 'localhost', 'resilient-design', 'user', 'password')

@app.route('/')
def home():
    return jsonify(status='ok')


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
    with dao.with_cursor(db_pool) as cursor:
        image_id = str(uuid4())
        if dao.save_image(cursor, image_id, request.data):
            return image_id
        else:
            return make_response('Could not save image', 500)


@app.route('/image/<image_id>', methods=['DELETE'])
def delete_image(image_id):
    with dao.with_cursor(db_pool) as c:
        if dao.delete_image(c, image_id):
            abort(204)
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