# coding: utf-8

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
    fname = os.path.join('cache', str(zoom), '%i_%i.jpg' % (tx, ty))
    if not os.path.isdir(os.path.dirname(fname)):
        os.makedirs(os.path.dirname(fname))
    if not os.path.isfile(fname):
        url = "http://khm1.google.com/kh/v=89&x=%i&s=&y=%i&z=%s&s=" % (tx, ty, zoom)
        print "getting %i x %i" % (tx, ty)
        urllib.urlretrieve(url, fname)
    return fname

if __name__ == '__main__':

    lat1, lon1 = 60.3189, 29.3556
    lat2, lon2 = 60.3332, 29.3744
    zoom = 17
