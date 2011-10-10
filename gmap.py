# coding: utf-8
import random
import Image
import ImageEnhance
import gpslib

__author__ = 'madrider'

import os
import math
import urllib

TILE_SIZE = 256

def lonlat_to_pixel(lon, lat, zoom):
    """Перевод из географических координат в координаты на полной карте"""
    num = pow(2., zoom) # число тайлов
    numpix = TILE_SIZE * num # пикселей на карте
    x = int((180. + lon) * numpix / 360.)
    c = math.sin(math.radians(lat))
    cm = math.pi * 2
    y0 = cm / 2 + 0.5 * math.log((1 + c)/(1 - c), math.e)
    y = int(numpix - y0 * numpix / cm)
    return x, y

def lonlat2tile(lon, lat, zoom):
    """Перевод из географических координат в номер тайла, содержащего точку"""
    gx, gy = lonlat_to_pixel(lon, lat, zoom)
    n = int(gx / TILE_SIZE)
    m = int(gy / TILE_SIZE)
    return n, m

def pixel_to_lonlat(gx, gy, zoom):
    """Перевод координат на полной карте в географические координаты"""
    num = pow(2., zoom)
    numpix = TILE_SIZE * num
    #sizex = 360.0 / num
    lon = gx * 360. / numpix - 180.
    cm = math.pi * 2
    y1 = (numpix - gy) * cm / numpix - cm / 2
    lat = math.degrees(math.atan(math.sinh(y1)))
    return lon, lat

def get_tile(tx, ty, zoom):
    vers = 92
    fname = os.path.join('cache', str(zoom), '%i_%i.jpg' % (tx, ty))
    if not os.path.isdir(os.path.dirname(fname)):
        os.makedirs(os.path.dirname(fname))
    if not os.path.isfile(fname):
        random.seed()
        num = random.choice([0, 1])
        s = 'Galileo'
        gal = s[:random.choice(range(1, len(s) + 1))]
        url = "http://khm%s.google.com/kh/v=%s&x=%i&y=%i&z=%s&s=%s" % (num, vers, tx, ty, zoom, gal)
        print "getting %i x %i" % (tx, ty)
        urllib.urlretrieve(url, fname)
    a = os.stat(fname)
    if a.st_size < 5000:
        print "invalid file?"
        os.unlink(fname)
    return fname

class P(object):
    x = None
    y = None

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return "%i x %i" % (self.x, self.y)

class GmapMap(object):
    correction = None
    zoom = None
    koeff_y = 1

    def __init__(self):
        pass

    def set_size(self, tx1, ty1, nx, ny, zoom):
        self.zoom = zoom
        self.tx1 = tx1
        self.tx2 = tx1 + nx - 1
        self.ty1 = ty1
        self.ty2 = ty1 + ny - 1
        self.mapsize = self.fullsize = P(nx * TILE_SIZE, ny * TILE_SIZE)
        self.xp1, self.yp1 = 0, 0
        self.xp2, self.yp2 = self.mapsize
        self.lon1, self.lat1 = pixel_to_lonlat(self.tx1 * TILE_SIZE, self.ty1 * TILE_SIZE, self.zoom)
        self.lon2, self.lat2 = pixel_to_lonlat((self.tx2 + 1) * TILE_SIZE, (self.ty2 + 1) * TILE_SIZE, self.zoom)

    def set_ll(self, lon1, lat1, lon2, lat2, zoom):
        self.lat1 = max(lat1, lat2)
        self.lat2 = min(lat1, lat2)
        self.lon1 = min(lon1, lon2)
        self.lon2 = max(lon1, lon2)
        self.zoom = zoom
        self.tx1, self.ty1 = lonlat2tile(self.lon1, self.lat1, zoom)
        self.tx2, self.ty2 = lonlat2tile(self.lon2, self.lat2, zoom)
        self.fullsize = P((self.tx2 - self.tx1 + 1) * TILE_SIZE, (self.ty2 - self.ty1 + 1) * TILE_SIZE)
        x1, y1 = lonlat_to_pixel(self.lon1, self.lat1, zoom)
        x2, y2 = lonlat_to_pixel(self.lon2, self.lat2, zoom)
        self.mapsize = P(x2 - x1, y2 - y1)
        self.xp1, self.yp1 = self.lonlat2xy(self.lon1, self.lat1)
        self.xp2, self.yp2 = self.lonlat2xy(self.lon2, self.lat2)

    def lonlat2xy(self, lon, lat):
        x, y = lonlat_to_pixel(lon, lat, self.zoom)
        x -= self.tx1 * TILE_SIZE
        y -= self.ty1 * TILE_SIZE
        y = y * self.koeff_y
        return x, y

    def enhance(self, brightness=1.0, contrast=1.0, saturation=1.0, sharpness=1.0):
        if brightness != 1.0:
            self.map_img = ImageEnhance.Brightness(self.map_img).enhance(brightness)
        elif contrast != 1.0:
            self.map_img = ImageEnhance.Contrast(self.map_img).enhance(contrast)
        if saturation != 1.0:
            self.map_img = ImageEnhance.Color(self.map_img).enhance(saturation)
        if sharpness != 1.0:
            self.map_img = ImageEnhance.Sharpness(self.map_img).enhance(sharpness)

    def get_map(self, save_file=None):
        self.map_img = Image.new("RGBA", (self.fullsize.x, self.fullsize.y), (200, 200, 200))
        for ty in range(self.ty1, self.ty2 + 1):
            for tx in range(self.tx1, self.tx2 + 1):
                fname = get_tile(tx, ty, self.zoom)
                try:
                    img1 = Image.open(fname)
                except:
                    img1 = Image.new("RGBA", (256, 256), (200, 255, 200))
                xp, yp = TILE_SIZE * (tx - self.tx1), TILE_SIZE * (ty - self.ty1)
                self.map_img.paste(img1, (xp, yp))

        mx = gpslib.distance(gpslib.Point(self.lon1, self.lat1), gpslib.Point(self.lon2, self.lat1))[0]
        my = gpslib.distance(gpslib.Point(self.lon1, self.lat1), gpslib.Point(self.lon1, self.lat2))[0]

        if self.correction:
            desty = int(my * self.fullsize.x / mx)
            self.y_koeff = float(desty) / float(self.fullsize.y)
            self.map_img1 = self.map_img.resize((self.fullsize.x, desty), Image.BILINEAR)
            self.fullsize.y = desty
            self.mapsize.y = int(self.mapsize.y * self.y_koeff)
            self.map_img = self.map_img1
        self.m_per_pix = mx / self.mapsize.x
        self.m_per_pix_y =  my / self.mapsize.y
#
#        if opts.kml:
#            res = kmlr.process(opts.kml)
#            draw = ImageDraw.Draw(self.map_img)
#
#            for l in res['lines']:
#                points = []
#                for p in l['coords']:
#                    points.append(self.lonlat2xy(p[0], p[1]))
#                draw.line(points)

        if save_file:
            self.map_img.save(save_file, "JPEG")


if __name__ == '__main__':

    lat1, lon1 = 60.3189, 29.3556
    lat2, lon2 = 60.3332, 29.3744
    zoom = 17
    m = GmapMap()
    m.set_ll(lon1, lat1, lon2, lat2, zoom)
    m.get_map(save_file='test1.jpg')
