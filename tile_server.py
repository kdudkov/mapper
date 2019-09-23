#!/usr/bin/env python3
# coding: utf-8

import tempfile
from optparse import OptionParser
from flask import Flask, request, send_file

try:
    from PIL import Image
except:
    import Image

from providers import YandexSat

app = Flask(__name__)


@app.route("/")
@app.route("/wms/")
def wms():
    if request.args.get('REQUEST') == 'GetCapabilities':
        return send_file('capabilites.xml', mimetype='application/vnd.ogc.wms_xml')

    if request.args.get('REQUEST') == 'GetMap':
        w = int(request.args.get('WIDTH'))
        h = int(request.args.get('HEIGHT'))
        bbox = request.args.get('BBOX')
        lon1, lat1, lon2, lat2 = map(lambda x: float(x), bbox.split(','))
        map_ = YandexSat()
        z = 17
        for z in range(17, 4, -1):
            map_.set_ll(lon1, lat1, lon2, lat2, z)
            if map_.big_pixels.w <= w:
                break
        app.logger.info('using z = %s (%s px) for width %s px', z, map_.big_pixels.w, w)
        map_.get_map(download=True)
        app.logger.info('%s x %s tiles', map_.tiles.w, map_.tiles.h)
        img1 = map_.img.resize((w, h), Image.ANTIALIAS)
        img1.load()
        file_, fn = tempfile.mkstemp()
        img1.convert('RGB').save(fn, 'JPEG')
        return send_file(fn, mimetype='image/jpeg')


if __name__ == "__main__":

    parser = OptionParser()
    opts, _ = parser.parse_args()

    app.debug = True
    app.logger.setLevel('DEBUG')
    app.run()
