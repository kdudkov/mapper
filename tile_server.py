import random
from flask import Flask, request, send_file
from gmap import YandexSat
import Image

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
    map_.set_ll(lon1, lat1, lon2, lat2, 16)
    map_.get_map(download=True, crop=1)

    img1 = map_.map_img_crop.resize((w, h), Image.ANTIALIAS)
    img1.load()
    print map_.xp1, map_.yp1
    print map_.xp2, map_.yp2
    n = random.randint(0, 99999)
    fn = 'temp_%s.jpg' % n
    img1.save(fn, 'JPEG')
    return send_file(fn, mimetype='image/jpeg')


if __name__ == "__main__":
    app.debug = True
    app.run()