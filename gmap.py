# coding: utf-8
import random
import Image
import ImageDraw
import ImageEnhance
import gpslib
import kmlr

__author__ = 'madrider'

import os
import math
import urllib

class P(object):
    x = None
    y = None

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return "%i x %i" % (self.x, self.y)

class MapProvider(object):
    TILE_SIZE = 256
    map_img = None
    correction = True
    zoom = 17
    koeff_y = 1
    tx1 = ty1 = tx2 = ty2 = 0
    lon1 = lat1 = lon2 = lat2 = 0
    fullsize = None
    mapsize = None

    def lonlat_to_pixel(self, lon, lat):
        raise Exception('not implemented')

    def pixel_to_lonlat(self, lon, lat):
        raise Exception('not implemented')

    def get_tile(self, tx, ty, download=True):
        raise Exception('not implemented')

    def set_size(self, tx1, ty1, nx, ny, zoom):
        """
        устанавливаем размер для получения карты в тайлах
        """
        self.zoom = zoom
        self.tx1 = tx1
        self.tx2 = tx1 + nx - 1
        self.ty1 = ty1
        self.ty2 = ty1 + ny - 1
        self.mapsize = self.fullsize = P(nx * self.TILE_SIZE, ny * self.TILE_SIZE)
        self.xp1, self.yp1 = 0, 0
        self.xp2, self.yp2 = self.mapsize
        self.lon1, self.lat1 = self.pixel_to_lonlat(self.tx1 * self.TILE_SIZE, self.ty1 * self.TILE_SIZE)
        self.lon2, self.lat2 = self.pixel_to_lonlat((self.tx2 + 1) * self.TILE_SIZE, (self.ty2 + 1) * self.TILE_SIZE)

    def set_ll(self, lon1, lat1, lon2, lat2, zoom):
        """
        устанавливаем границы области для получения карты
        """
        self.lat1 = max(lat1, lat2)
        self.lat2 = min(lat1, lat2)
        self.lon1 = min(lon1, lon2)
        self.lon2 = max(lon1, lon2)
        self.zoom = zoom
        self.tx1, self.ty1 = self.lonlat2tile(self.lon1, self.lat1)
        self.tx2, self.ty2 = self.lonlat2tile(self.lon2, self.lat2)
        # size of image (int. number of tiles)
        self.fullsize = P((self.tx2 - self.tx1 + 1) * self.TILE_SIZE, (self.ty2 - self.ty1 + 1) * self.TILE_SIZE)
        self.calculate_size()

    def calculate_size(self):
        # coords. of exact image
        self.xp1, self.yp1 = self.lonlat2xy(self.lon1, self.lat1)
        self.xp2, self.yp2 = self.lonlat2xy(self.lon2, self.lat2)
        # size of exact image
        self.mapsize = P(self.xp2 - self.xp1, self.yp2 - self.yp1)

    def lonlat2xy(self, lon, lat):
        """
        перевод градусов в координаты на картинке
        """
        x, y = self.lonlat_to_pixel(lon, lat)
        x -= self.tx1 * self.TILE_SIZE
        y -= self.ty1 * self.TILE_SIZE
        y = int(y * self.koeff_y)
        return x, y

    def lonlat2tile(self, lon, lat):
        """Перевод из географических координат в номер тайла, содержащего точку"""
        gx, gy = self.lonlat_to_pixel(lon, lat)
        n = int(gx / self.TILE_SIZE)
        m = int(gy / self.TILE_SIZE)
        return n, m

    def get_map(self, download=True, crop=False):
        self.map_img = Image.new("RGBA", (self.fullsize.x, self.fullsize.y), (200, 200, 200))
        for ty in range(self.ty1, self.ty2 + 1):
            for tx in range(self.tx1, self.tx2 + 1):
                fname = self.get_tile(tx, ty, download)
                try:
                    img1 = Image.open(fname)
                except:
                    img1 = Image.new("RGBA", (256, 256), (200, 255, 200))
                xp, yp = self.TILE_SIZE * (tx - self.tx1), self.TILE_SIZE * (ty - self.ty1)
                self.map_img.paste(img1, (xp, yp))

        mx = gpslib.distance(gpslib.Point(self.lon1, self.lat1), gpslib.Point(self.lon2, self.lat1))[0]
        my = gpslib.distance(gpslib.Point(self.lon1, self.lat1), gpslib.Point(self.lon1, self.lat2))[0]

        if self.correction:
            desty = int(my * self.fullsize.x / mx)
            self.koeff_y = float(desty) / float(self.fullsize.y)
            self.map_img1 = self.map_img.resize((self.fullsize.x, desty), Image.BILINEAR)
            self.fullsize.y = desty
            self.mapsize.y = int(self.mapsize.y * self.koeff_y)
            self.map_img = self.map_img1
            self.calculate_size()
        self.m_per_pix = mx / self.mapsize.x
        self.m_per_pix_y = my / self.mapsize.y
        if crop:
            map_img1 = self.map_img.crop((self.xp1, self.yp1, self.xp2, self.yp2))
            map_img1.load()
            self.map_img_crop = map_img1

    def save(self, save_file):
        self.map_img.save(save_file, "JPEG")

    def draw_kml(self, kml):
        res = kmlr.process(kml)
        draw = ImageDraw.Draw(self.map_img)

        for l in res['lines']:
            points = []
            for p in l['coords']:
                points.append(self.lonlat2xy(p[0], p[1]))
            draw.line(points)

    def enhance(self, *args, **kw):
        pass

class GmapMap(MapProvider):

    def enhance(self, brightness=1.0, contrast=1.0, saturation=1.0, sharpness=1.0):
        if brightness != 1.0:
            self.map_img = ImageEnhance.Brightness(self.map_img).enhance(brightness)
        elif contrast != 1.0:
            self.map_img = ImageEnhance.Contrast(self.map_img).enhance(contrast)
        if saturation != 1.0:
            self.map_img = ImageEnhance.Color(self.map_img).enhance(saturation)
        if sharpness != 1.0:
            self.map_img = ImageEnhance.Sharpness(self.map_img).enhance(sharpness)


    def lonlat_to_pixel(self, lon, lat):
        """Перевод из географических координат в координаты на полной карте"""
        num = 2. ** self.zoom # число тайлов
        numpix = self.TILE_SIZE * num # пикселей на карте
        x = int((180. + lon) * numpix / 360.)
        c = math.sin(math.radians(lat))
        cm = math.pi * 2
        y0 = cm / 2 + 0.5 * math.log((1 + c)/(1 - c), math.e)
        y = int(numpix - y0 * numpix / cm)
        return x, y

    def pixel_to_lonlat(self, gx, gy):
        """Перевод координат на полной карте в географические координаты"""
        num = 2. ** self.zoom # число тайлов
        numpix = self.TILE_SIZE * num
        #sizex = 360.0 / num
        lon = gx * 360. / numpix - 180.
        cm = math.pi * 2
        y1 = (numpix - gy) * cm / numpix - cm / 2
        lat = math.degrees(math.atan(math.sinh(y1)))
        return lon, lat

    def get_tile(self, tx, ty, download=True):
        vers = 92
        fname = os.path.join('cache', str(self.zoom), '%i_%i.jpg' % (tx, ty))
        if not os.path.isdir(os.path.dirname(fname)):
            os.makedirs(os.path.dirname(fname))
        if not os.path.isfile(fname) and download:
            random.seed()
            num = random.choice([0, 1])
            s = 'Galileo'
            gal = s[:random.choice(range(1, len(s) + 1))]
            url = "http://khm%s.google.com/kh/v=%s&x=%i&y=%i&z=%s&s=%s" % (num, vers, tx, ty, self.zoom, gal)
            print "getting %i x %i" % (tx, ty)
            urllib.urlretrieve(url, fname)
        if os.path.isfile(fname):
            a = os.stat(fname)
            if a.st_size < 5000:
                print "invalid file?"
                os.unlink(fname)
        return fname

class OsmMap(MapProvider):
    nums = ['a', 'b', 'c']
    url = 'http://%(num)s.tile.openstreetmap.org/%(z)s/%(x)s/%(y)s.png'
    path = 'osm'
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

    def get_tile(self, tx, ty, download=True):
        fname = os.path.join('cache', self.path, str(self.zoom), '%i_%i.png' % (tx, ty))
        if not os.path.isdir(os.path.dirname(fname)):
            os.makedirs(os.path.dirname(fname))
        if not os.path.isfile(fname) and download:
            random.seed()
            num = random.choice(self.nums)
            url = self.url % {'num':num, 'z':self.zoom, 'x':tx, 'y':ty}
            print "getting %i x %i" % (tx, ty)
            urllib.urlretrieve(url, fname)
        if os.path.isfile(fname):
            a = os.stat(fname)
#            if a.st_size < 5000:
#                print "invalid file?"
#                os.unlink(fname)
        return fname

class CicleMap(OsmMap):
    nums = ['a', 'b']
    url = "http://%(num)s.tile.opencyclemap.org/cycle/%(z)s/%(x)s/%(y)s.png"
    path = 'osm_cicle'

class YandexSat(MapProvider):
    equatorLength = 40075016.685578488 # Длина экватора
    rn = 6378137. # Экваториальный радиус
    e = 0.0818191908426 # Эксцентриситет

    def lonlat_to_pixel(self, lon, lat):
        """Перевод из географических координат в координаты на полной карте"""
        num = 2. ** self.zoom # число тайлов
        numpix = self.TILE_SIZE * num # пикселей на карте
        a = numpix / self.equatorLength
        b = self.equatorLength / 2
        latr = math.radians(lat)
        lonr = math.radians(lon)

        esinLat = self.e * math.sin(latr)
        tan_temp = math.tan(math.pi / 4.0 + latr / 2.0)
        pow_temp = math.pow(math.tan(math.pi / 4.0 + math.asin(esinLat) / 2), self.e)
        u = tan_temp / pow_temp
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

    def get_tile(self, tx, ty, download=True):
        fname = os.path.join('cache', 'yandex', str(self.zoom), '%i_%i.jpg' % (tx, ty))
        if not os.path.isdir(os.path.dirname(fname)):
            os.makedirs(os.path.dirname(fname))
        if not os.path.isfile(fname) and download:
            random.seed()
            num = random.choice(['01', '02', '03', '04'])
            url = "http://sat%s.maps.yandex.net/tiles?l=sat&v=1.37.0&x=%s&y=%s&z=%s&lang=ru_RU" % (num, tx, ty, self.zoom)
            print "getting %i x %i" % (tx, ty)
            urllib.urlretrieve(url, fname)
        if os.path.isfile(fname):
            a = os.stat(fname)
        return fname


if __name__ == '__main__':

    lat1, lon1 = 60.3189, 29.3556
    lat2, lon2 = 60.3332, 29.3744
    zoom = 15
    m = OsmMap()
    m.set_ll(lon1, lat1, lon2, lat2, zoom)
    m.get_map()
    m.save('test_osm.jpg')
    m = YandexSat()
    m.set_ll(lon1, lat1, lon2, lat2, zoom)
    m.get_map()
    m.save('test_yand.jpg')
