# coding: utf-8

import logging
import random

import time
import gpslib
import kml_reader
#import gpx_reader
import os
import math
import requests

try:
    from PIL import Image
    from PIL import ImageDraw
    from PIL import ImageEnhance
except:
    import Image
    import ImageDraw
    import ImageEnhance

__author__ = 'madrider'

LOG = logging.getLogger(__name__)

class Point(object):
    x = None
    y = None

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return "%i x %i" % (self.x, self.y)


class Box(object):
    def __init__(self, x1, y1, x2, y2):
        self.p1 = Point(x1, y1)
        self.p2 = Point(x2, y2)

    @property
    def w(self):
        return abs(self.p2.x - self.p1.x)

    @property
    def h(self):
        return abs(self.p2.y - self.p1.y)

    @property
    def size(self):
        return Point(abs(self.p2.x - self.p1.x), abs(self.p2.y - self.p1.y))


class MapProvider(object):
    TILE_SIZE = 256
    ext = 'jpg'
    path = '---'

    def __init__(self):
        self.orig_img = None
        self.img = None
        self.resize = True
        self.zoom = 17
        self.koeff_y = 1
        self.tiles = None
        self.big_pixels = None
        self.lon1 = self.lat1 = self.lon2 = self.lat2 = 0
        self.m_per_pix = 0
        self.crop = False

    def set_tiles(self, tx1, ty1, nx, ny, zoom):
        """
        устанавливаем размер для получения карты в тайлах
        """
        self.zoom = zoom
        self.tiles = Box(tx1, ty1, tx1 + nx - 1, ty1 + ny - 1)
        self.big_pixels = Box(self.tiles.p1.x * self.TILE_SIZE,
                              self.tiles.p1.y * self.TILE_SIZE,
                              (self.tiles.p2.x + 1) * self.TILE_SIZE,
                              (self.tiles.p2.y + 1) * self.TILE_SIZE)
        self.lon1, self.lat1 = self.pixel_to_lonlat(self.big_pixels.p1.x, self.big_pixels.p1.y)
        self.lon2, self.lat2 = self.pixel_to_lonlat(self.big_pixels.p2.x, self.big_pixels.p2.y)

    def set_ll(self, lon1, lat1, lon2, lat2, zoom):
        """
        устанавливаем границы области для получения карты
        """
        self.lat1 = max(lat1, lat2)
        self.lat2 = min(lat1, lat2)
        self.lon1 = min(lon1, lon2)
        self.lon2 = max(lon1, lon2)
        self.zoom = zoom
        self.crop = True
        tx1, ty1 = self.lonlat2tile(self.lon1, self.lat1)
        tx2, ty2 = self.lonlat2tile(self.lon2, self.lat2)
        self.tiles = Box(tx1, ty1, tx2, ty2)
        self.big_pixels = Box(self.tiles.p1.x * self.TILE_SIZE,
                              self.tiles.p1.y * self.TILE_SIZE,
                              (self.tiles.p2.x + 1) * self.TILE_SIZE,
                              (self.tiles.p2.y + 1) * self.TILE_SIZE)

    def _get_tile(self, tx, ty):
        fname = os.path.join('cache', self.path, str(self.zoom), '%i_%i.%s' % (tx, ty, self.ext))
        if not os.path.isdir(os.path.dirname(fname)):
            os.makedirs(os.path.dirname(fname))
        if os.path.isfile(fname):
            a = os.stat(fname)
            if time.time() - a.st_mtime > 10 * 24 * 60 * 60:
                logging.info('old tile %s x %s, reget', tx, ty)
                self.get_tile(fname, tx, ty)
        else:
            logging.info('getting tile %s x %s', tx, ty)
            self.get_tile(fname, tx, ty)
        return fname

    def lonlat_to_pixel(self, lon, lat):
        raise Exception('not implemented')

    def pixel_to_lonlat(self, lon, lat):
        raise Exception('not implemented')

    def get_tile(self, fname, tx, ty):
        raise Exception('not implemented')

    def lonlat2xy(self, lon, lat):
        """
        перевод градусов в координаты на картинке
        """
        x, y = self.lonlat_to_pixel(lon, lat)
        x -= self.big_pixels.p1.x
        y -= self.big_pixels.p1.y
        y = int(y * self.koeff_y)
        return x, y

    def lonlat2tile(self, lon, lat):
        """Перевод из географических координат в номер тайла, содержащего точку"""
        gx, gy = self.lonlat_to_pixel(lon, lat)
        return int(gx / self.TILE_SIZE), int(gy / self.TILE_SIZE)

    def get_map(self, download=True):
        image = Image.new("RGBA", (self.big_pixels.w, self.big_pixels.h), (200, 200, 200))
        for ty in range(self.tiles.p1.y, self.tiles.p2.y + 1):
            for tx in range(self.tiles.p1.x, self.tiles.p2.x + 1):
                fname = self._get_tile(tx, ty)
                try:
                    img1 = Image.open(fname)
                except:
                    logging.exception('error getting tile')
                    img1 = Image.new("RGBA", (256, 256), (200, 255, 200))
                xp, yp = self.TILE_SIZE * (tx - self.tiles.p1.x), self.TILE_SIZE * (ty - self.tiles.p1.y)
                image.paste(img1, (xp, yp))
        self.orig_img = image

        meters_x = gpslib.distance(gpslib.Point(self.lon1, self.lat1), gpslib.Point(self.lon2, self.lat1))[0]
        meters_y = gpslib.distance(gpslib.Point(self.lon1, self.lat1), gpslib.Point(self.lon1, self.lat2))[0]

        if self.resize:
            desty = int(meters_y * self.big_pixels.w / meters_x)
            self.koeff_y = float(desty) / float(self.big_pixels.h)
            image_new = image.resize((self.big_pixels.w, desty), Image.BILINEAR)
            self.img = image_new
        else:
            self.img = self.orig_img

        self.m_per_pix = Point(meters_x / self.big_pixels.w, meters_y / self.big_pixels.h)
        if self.crop:
            self.crop_to_coords()

    def crop_to_coords(self):
        xp1, yp1 = self.lonlat2xy(self.lon1, self.lat1)
        xp2, yp2 = self.lonlat2xy(self.lon2, self.lat2)
        img1 = self.img.crop((xp1, yp1, xp2, yp2))
        img1.load()
        self.img = img1
        xp1, yp1 = self.lonlat_to_pixel(self.lon1, self.lat1)
        xp2, yp2 = self.lonlat_to_pixel(self.lon2, self.lat2)
        self.big_pixels = Box(xp1, yp1, xp2, yp2)

    def save(self, save_file):
        self.img.convert("RGB").save(save_file, "JPEG")

    def draw_kml(self, kml):
        res = kml_reader.process(kml)
        self.draw_lines(res)

    def draw_gpx(self, gpx):
        #res = gpx_reader.process(gpx)
        #self.draw_lines(res)
        pass

    def draw_lines(self, data):
        draw = ImageDraw.Draw(self.img)
        for l in data['lines']:
            points = []
            for p in l['coords']:
                points.append(self.lonlat2xy(p[1], p[0]))
            draw.line(points, fill=(255, 255, 255, 128), width=2)
            # for p in data['points']:
            #     draw.point((self.lonlat2xy(p['lon'], p['lat'])))

    def enhance(self, brightness=1.0, contrast=1.0, saturation=1.0, sharpness=1.0):
        if brightness != 1.0:
            self.img = ImageEnhance.Brightness(self.img).enhance(brightness)
        elif contrast != 1.0:
            self.img = ImageEnhance.Contrast(self.img).enhance(contrast)
        if saturation != 1.0:
            self.img = ImageEnhance.Color(self.img).enhance(saturation)
        if sharpness != 1.0:
            self.img = ImageEnhance.Sharpness(self.img).enhance(sharpness)


class OsmMap(MapProvider):
    path = 'osm'
    ext = 'png'
    nums = ['a', 'b', 'c']
    url = 'http://%(num)s.tile.openstreetmap.org/%(z)s/%(x)s/%(y)s.png'

    def lonlat_to_pixel(self, lon, lat):
        lat_rad = math.radians(lat)
        n = 2.0 ** self.zoom
        x = int((lon + 180.0) / 360.0 * n * self.TILE_SIZE)
        y = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n * self.TILE_SIZE)
        return x, y

    def pixel_to_lonlat(self, gx, gy):
        n = 2.0 ** self.zoom * self.TILE_SIZE
        lon_deg = gx / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * gy / n)))
        lat_deg = math.degrees(lat_rad)
        return lon_deg, lat_deg

    def get_tile(self, fname, tx, ty):
        random.seed()
        num = random.choice(self.nums)
        url = self.url % {'num': num, 'z': self.zoom, 'x': tx, 'y': ty}
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(fname, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)


class CycleMap(OsmMap):
    path = 'osm_cicle'
    nums = ['a', 'b']
    url = "http://%(num)s.tile.opencyclemap.org/cycle/%(z)s/%(x)s/%(y)s.png"


class YandexSat(MapProvider):
    path = 'ya_sat'
    ext = 'jpg'
    equatorLength = 40075016.685578488  # Длина экватора
    rn = 6378137.  # Экваториальный радиус
    e = 0.0818191908426  # Эксцентриситет

    def lonlat_to_pixel(self, lon, lat):
        """Перевод из географических координат в координаты на полной карте"""
        num = 2. ** self.zoom  # число тайлов
        numpix = self.TILE_SIZE * num  # пикселей на карте
        a = numpix / self.equatorLength
        b = self.equatorLength / 2
        latr = math.radians(lat)
        lonr = math.radians(lon)

        esinLat = self.e * math.sin(latr)
        tan_temp = math.tan(math.pi / 4.0 + latr / 2.0)
        pow_temp = math.pow(math.tan(math.pi / 4.0 + math.asin(esinLat) / 2), self.e)
        u = abs(tan_temp / pow_temp)
        mx, my = self.rn * lonr, self.rn * math.log(u)
        return int((b + mx) * a), int((b - my) * a)

    def pixel_to_lonlat(self, gx, gy):
        """Перевод координат на полной карте в географические координаты"""
        num = 2. ** self.zoom # число тайлов
        numpix = self.TILE_SIZE * num # пикселей на карте
        a = numpix / self.equatorLength
        b = self.equatorLength / 2
        mx = gx / a - b
        my = b - gy / a

        ab = 0.00335655146887969400
        bb = 0.00000657187271079536
        cb = 0.00000001764564338702
        db = 0.00000000005328478445

        xphi = math.pi / 2 - 2 * math.atan(1. / math.exp(my / self.rn))

        latr = xphi + ab * math.sin(2 * xphi) + bb * math.sin(4 * xphi) + cb * math.sin(6 * xphi) + db * math.sin(8 * xphi)
        lonr = mx / self.rn

        return math.degrees(lonr), math.degrees(latr)

    def get_tile(self, fname, tx, ty):
        random.seed()
        num = random.choice(['01', '02', '03', '04'])
        url = 'https://sat{}.maps.yandex.net/tiles?l=sat&v=3.497.0&x={}&y={}&z={}&lang=ru_RU'.format(num, tx, ty,
                                                                                                     self.zoom)
        LOG.debug('save to %s', fname)
        print(fname)
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(fname, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
        else:
            print(url, r.status_code)


if __name__ == '__main__':

    lat1, lon1 = 60.3189, 29.3556
    lat2, lon2 = 60.3332, 29.3744
    zoom = 15
    m = CycleMap()
    m.set_ll(lon1, lat1, lon2, lat2, zoom)
    m.get_map()
    m.save('test_osm.jpg')
    m = YandexSat()
    m.set_ll(lon1, lat1, lon2, lat2, zoom)
    m.get_map()
    m.save('test_yand.jpg')
