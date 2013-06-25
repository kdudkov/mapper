#!/usr/bin/env python
# coding: utf-8

import tempfile
from optparse import OptionParser

import Image
from flask import Flask, request, send_file

from gmap import YandexSat, GmapMap

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/tms/<zoom>/")
def tms(zoom):
    x = int(request.args.get('x'))
    y = int(request.args.get('y'))
    provider = YandexSat()
    provider.zoom = zoom
    f = provider.get_tile(x, y)
    return send_file(f, mimetype='image/jpeg')


@app.route("/wms/")
def wms():
    w = int(request.args.get('w'))
    h = int(request.args.get('h'))
    bbox = request.args.get('bbox')
    lon1, lat1, lon2, lat2 = map(lambda x: float(x), bbox.split(','))
    map_ = YandexSat()
    #map_ = GmapMap()
    for z in range(17, 10, -1):
        map_.set_ll(lon1, lat1, lon2, lat2, z)
        if (map_.xp2 - map_.xp1) < w:
            z += 1
            break
    map_.set_ll(lon1, lat1, lon2, lat2, z)
    map_.get_map(download=True, crop=1)

    img1 = map_.map_img_crop.resize((w, h), Image.ANTIALIAS)
    img1.load()
    file_, fn = tempfile.mkstemp()
    img1.save(fn, 'JPEG')
    return send_file(fn, mimetype='image/jpeg')


if __name__ == "__main__":
    global opts

    parser = OptionParser()
    parser.add_option("-z", "--zoom", dest="zoom",
                      help="zoom (10-18)", metavar="n", type="int", default=17)
    opts, args = parser.parse_args()

    app.debug = True
    app.run()