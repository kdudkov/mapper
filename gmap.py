import os
import urllib

__author__ = 'madrider'

from math import pi, sin, cos, log, exp, atan, floor, pow

# Constants used for degree to radian conversion, and vice-versa.
DTOR = pi / 180.
RTOD = 180. / pi
TILE_SIZE = 256

def lonlat_to_pixel(lat, lon, zoom):
    # Calculating the pixel x coordinate by multiplying the longitude
    #  value with with the number of degrees/pixel at the given
    #  zoom level.
    c = TILE_SIZE * pow(2, zoom)
    npix =  c / 2
    degpp = c / 360.  # degrees per pixel
    radpp = c / (2 * pi)
    px_x = round(npix + (lon * degpp))

    # Creating the factor, and ensuring that 1 or -1 is not passed in as the
    #  base to the logarithm.  Here's why:
    #   if fac = -1, we'll get log(0) which is undefined;
    #   if fac =  1, our logarithm base will be divided by 0, also undefined.
    fac = min(max(sin(DTOR * lat), -0.9999), 0.9999)

    # Calculating the pixel y coordinate.
    px_y = round(npix + (0.5 * log((1 + fac)/(1 - fac)) * (-1.0 * radpp)))

    # Returning the pixel x, y to the caller of the function.
    return px_x, px_y

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
    x2tx = lambda x: floor(x / TILE_SIZE)
    tx1, ty1 = map(x2tx, lonlat_to_pixel(lat1, lon1, zoom))
    tx2, ty2 = map(x2tx, lonlat_to_pixel(lat2, lon2, zoom))
    print "%i x %i px" % ((tx2 - tx1) * TILE_SIZE, (ty1 - ty2) * TILE_SIZE)
    for ty in range(ty2, ty1 + 1):
        for tx in range(tx1, tx2 + 1):
            fname = get_tile(tx, ty, zoom)
