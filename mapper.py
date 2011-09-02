#!/usr/bin/env python
# coding: utf-8

from optparse import OptionParser
import ImageEnhance

from reportlab.lib.units import cm, mm, inch
from reportlab.pdfbase import pdfmetrics, ttfonts
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4, A3, landscape
import Image, ImageDraw
from gmap import TILE_SIZE, lonlat_to_pixel, get_tile, lonlat2tile
import gpslib

PEREKR = 0.2

__author__ = 'madrider'

def deg2dms(deg):
    dd = deg
    d = int(dd)
    dd -= d
    dd *= 60
    m = int(dd)
    dd -= m
    s = dd * 60
    if s > 59.999:
        s = 0
        m += 1
    return d, m, s

def dms2deg(d, m, s):
    return d + m / 60. + s / 3600.

class P(object):
    x = 0
    y = 0

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return "%i x %i" % (self.x, self.y)
    
class Map(object):
    def __init__(self, lon1, lat1, lon2, lat2, zoom):
        self.lat1 = max(lat1, lat2)
        self.lon1 = min(lon1, lon2)
        self.lat2 = min(lat1, lat2)
        self.lon2 = max(lon1, lon2)
        self.zoom = zoom
        self.tx1, self.ty1 = lonlat2tile(self.lon1, self.lat1, zoom) # num of tiles
        self.tx2, self.ty2 = lonlat2tile(self.lon2, self.lat2, zoom)
        self.xp1, self.yp1 = lonlat_to_pixel(self.lon1, self.lat1, zoom)
        self.xp1 -= self.tx1 * TILE_SIZE
        self.yp1 -= self.ty1 * TILE_SIZE
        self.xp2, self.yp2 = lonlat_to_pixel(self.lon2, self.lat2, zoom)
        self.xp2 -= self.tx1 * TILE_SIZE
        self.yp2 -= self.ty1 * TILE_SIZE
        self.mapsize = P(self.xp2 - self.xp1, self.yp2 - self.yp1)
        self.fullsize = P((self.tx2 - self.tx1 + 1) * TILE_SIZE, (self.ty2 - self.ty1 + 1) * TILE_SIZE)


    def get_map(self, save=True):
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
        self.enhance(contrast=opts.contrast, brightness=opts.bright)

        mx = gpslib.distance(gpslib.Point(self.lon1, self.lat1), gpslib.Point(self.lon2, self.lat1))[0]
        my = gpslib.distance(gpslib.Point(self.lon1, self.lat1), gpslib.Point(self.lon1, self.lat2))[0]
        desty = int(my * self.fullsize.x / mx)
        self.y_koeff = float(desty) / float(self.fullsize.y)
        self.map_img1 = self.map_img.resize((self.fullsize.x, desty), Image.BILINEAR)
        self.fullsize.y = desty
        self.map_img = self.map_img1
        self.m_per_pix = mx / self.mapsize.x
        self.m_per_pix_y =  my / self.mapsize.y

        points = []
        for s in open('points.txt', 'r'):
            s = s.strip()
            if s:
                lon, lat = s.split(',')
                points.append(self.lonlat2xy(float(lon), float(lat)))
        if points:
            points.append(points[0])
            draw = ImageDraw.Draw(self.map_img)
            draw.line(points)

        if save:
            self.map_img.save("map.jpg", "JPEG")
            self.map_img1.save("map1.jpg", "JPEG")


    def enhance(self, brightness=1.0, contrast=1.0, saturation=1.0, sharpness=1.0):
        if brightness != 1.0:
            self.map_img = ImageEnhance.Brightness(self.map_img).enhance(brightness)
        elif contrast != 1.0:
            self.map_img = ImageEnhance.Contrast(self.map_img).enhance(contrast)
        if saturation != 1.0:
            self.map_img = ImageEnhance.Color(self.map_img).enhance(saturation)
        if sharpness != 1.0:
            self.map_img = ImageEnhance.Sharpness(self.map_img).enhance(sharpness)

    def lonlat2xy(self, lon, lat):
        x, y = lonlat_to_pixel(lon, lat, self.zoom)
        x -= self.tx1 * TILE_SIZE
        y -= self.ty1 * TILE_SIZE
        y = y * self.y_koeff
        return x, y

def main():
    DMS_GRID = (dms2deg(0, 30, 0), dms2deg(0, 10, 0), dms2deg(0, 1, 0), dms2deg(0, 0, 30), dms2deg(0, 0, 10), dms2deg(0, 0, 5), dms2deg(0, 0, 2), dms2deg(0, 0, 1))
    D_GRID = [1]
    for i in range(1, 5):
        for c in [5, 2, 1]:
            D_GRID.append(c * pow(10, -i))
    FONT = 'Droid'
    pdfmetrics.registerFont(ttfonts.TTFont(FONT, 'DroidSansMono.ttf'))
    page_size = A4
    if opts.land:
        page_size = landscape(page_size)
    try:
        c1 = map(lambda x: float(x), opts.c1.split(',', 1))
        c2 = map(lambda x: float(x), opts.c2.split(',', 1))
    except:
        print "smth wrong in command line!"
        return 1

    lat1, lat2 = max(c1[0], c2[0]), min(c1[0], c2[0])
    lon1, lon2 = min(c1[1], c2[1]), max(c1[1], c2[1])
    zoom = opts.zoom
    map_ = Map(lon1, lat1, lon2, lat2, zoom)
    map_.get_map()
    
    print "got %i x %i map" % (map_.fullsize.x, map_.fullsize.y)

    # page size
    c = Canvas(opts.filename, pagesize=page_size)
    maxx, maxy = page_size
    page_border = 1 * cm
    xp1, yp1 = page_border, page_border
    xp2, yp2 = maxx - page_border, maxy - page_border
    yp2 -= 10 + 30 # for page title

    if opts.scale:
        m1 = (xp2 - xp1) / cm * opts.scale
        imgw = int(m1 / map_.m_per_pix)
    else:
        imgw = int(map_.mapsize.x / (1. + (opts.numx - 1) * (1. - PEREKR)))
    imgh = int((yp2 - yp1) / (xp2 - xp1) * imgw)
    print "need %i x %i image for 1 page" % (imgw, imgh)

    koeffx = float(imgw) / (xp2 - xp1)
    koeffy = float(imgh) / (yp2 - yp1)

    # pixels in deg of x axis (lon)
    pdegx = lonlat_to_pixel(lon1 + 1, lat1, zoom)[0] - lonlat_to_pixel(lon1, lat1, zoom)[0]
    pdegx /= koeffx # to pdf pixels
    if opts.deg:
        grid = D_GRID
    else:
        grid = DMS_GRID
    d_deg_x = 1
    for i in grid:
        if i * pdegx < 1 * cm:
            break
        d_deg_x = i
    # pixels in deg of y axis (lat)
    pdegy = abs(lonlat_to_pixel(lon1, lat1 + 1, zoom)[1] - lonlat_to_pixel(lon1, lat1, zoom)[1])
    pdegy /= koeffy # to pdf pixels
    d_deg_y = 1
    for i in grid:
        if i * pdegy < 1 * cm:
            break
        d_deg_y = i
    m_in_cm_x = gpslib.distance(gpslib.Point(lon1, lat1), gpslib.Point(lon1 + cm / pdegx, lat1))[0]
    m_in_cm_y = gpslib.distance(gpslib.Point(lon1, lat1), gpslib.Point(lon1, lat1 + cm / pdegy))[0]
    print m_in_cm_x, m_in_cm_y
    
    # splitting map to pdf pages
    numpages = 0
    dy = map_.yp1
    py = 1
    while dy + (1 - PEREKR) * imgh <= map_.yp2:
        dx = map_.xp1
        px = 1
        while dx + (1 - PEREKR) * imgw <= map_.xp2:
            numpages += 1
            c.setFont(FONT, 10)
            c.drawString(xp1, maxy - page_border - 10, '%s, page %s-%s (1см = %iм)' % (opts.title, px, py, round(m_in_cm_x)))
            c.line(xp2 - cm, maxy - page_border - 5, xp2, maxy - page_border - 5)
            tmpw, tmph = min(imgw, map_.xp2 - dx), min(imgh, map_.yp2 - dy)
            img11 = map_.map_img.crop((dx, dy, dx + tmpw, dy + tmph))
            img11.load()
            if tmpw < imgw or tmph < imgh:
                img1 = Image.new("RGBA", (imgw, imgh), (250, 250, 250))
                img1.paste(img11, (0, 0))
            else:
                img1 = img11
            pfname = "tmp-%s-%s.jpg" % (px, py)
            img1.save(pfname, "JPEG")
            c.drawImage(pfname, xp1, yp1, xp2 - xp1, yp2 - yp1)
            #c.drawInlineImage(img1, xp1, yp1, xp2 - xp1, yp2 - yp1)
            c.setStrokeColorRGB(0.0, 0.0, 0.0)
            c.setLineWidth(1)
            c.rect(xp1, yp1, xp2 - xp1, yp2 - yp1)

            c.setStrokeAlpha(0.5)
            # draw x grid
            degx = int(lon1)
            while 1:
                degx += d_deg_x
                x, _ = map_.lonlat2xy(degx, lat1)
                if x <= dx:
                    continue
                if x >= dx + tmpw:
                    break
                xp = (x - dx) / koeffx
                d, m, s = deg2dms(degx)
                if m == 0 and s < 0.0001:
                    c.setLineWidth(3)
                    c.setStrokeColorRGB(1, 0, 0)
                elif s < 0.0001:
                    c.setLineWidth(2)
                    c.setStrokeColorRGB(0, 1, 0)
                else:
                    c.setLineWidth(1)
                    c.setStrokeColorRGB(0, 0, 0)
                c.line(xp + xp1, yp1, xp + xp1, yp2)
                c.setFont(FONT, 5)
                if opts.deg:
                    text = "%.4f" % degx
                else:
                    text = "%iº%0.2i'%0.2i\"" % (d, m, round(s))
                c.drawCentredString(xp + xp1, yp1 - 5, text)
                c.drawCentredString(xp + xp1, yp2 + 5, text)
            # draw y grid
            degy = int(lat1) + 1
            while 1:
                degy -= d_deg_y
                _, y = map_.lonlat2xy(lon1, degy)
                if y <= dy:
                    continue
                if y >= dy + tmph:
                    break
                yp = (y - dy) / koeffy
                d, m, s = deg2dms(degy)
                if m == 0 and (s < 0.0001 or s > 59.9999):
                    c.setLineWidth(3)
                    c.setStrokeColorRGB(1, 0, 0)
                elif s < 0.0001:
                    c.setLineWidth(2)
                    c.setStrokeColorRGB(0, 1, 0)
                else:
                    c.setLineWidth(1)
                    c.setStrokeColorRGB(0, 0, 0)
                c.line(xp1, yp2 - yp, xp2, yp2 - yp)
                c.setFont(FONT, 5)
                if opts.deg:
                    text = "%.4f" % degy
                else:
                    text = "%iº%0.2i'%0.2i\"" % (d, m, round(s))
                c.saveState()
                c.translate(xp1 - 5, yp2 - yp)
                c.rotate(90)
                c.drawCentredString(0, 0, text)
                c.restoreState()
                c.saveState()
                c.translate(xp2 + 10, yp2 - yp)
                c.rotate(90)
                c.drawCentredString(0, 0, text)
                c.restoreState()
            c.showPage()
            dx += int(imgw * (1. - PEREKR))
            px += 1
        dy += int(imgh * (1. - PEREKR))
        py += 1
    c.save()
    print "%s pages in pdf" % numpages

if __name__ == '__main__':
    global opts

    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                  help="output pdf name", metavar="FILE", default="map.pdf")
    parser.add_option("-t", "--title", dest="title",
                  help="map title", default="Каннельярви")
    parser.add_option("--coords1", dest="c1",
                  help="lover bottom corner", metavar="lat1,lon1", default="60.3167,29.35")
    parser.add_option("--coords2", dest="c2",
                  help="upper top corner", metavar="lat2,lon2", default="60.33,29.38")
    parser.add_option("-z", "--zoom", dest="zoom",
                  help="zoom (10-18)", metavar="n", type="int", default=17)
    parser.add_option("--deg", dest="deg", action="store_true",
                  help="use d.dddd instead of d mm' s.sss", default=False)
    parser.add_option("--scale", dest="scale", type="int",
                  help="scale in meters in cm", default=0)
    parser.add_option("--pages_x", dest="numx", type="int",
                  help="fit in n pages with", default=2)
#    parser.add_option("--pages_y", dest="numy", type="int",
#                  help="fit in n pages height", default=0)
    parser.add_option("--land", dest="land", action="store_true",
                  help="landscape page orientation", default=False)
    parser.add_option("--contrast", dest="contrast", type="float", default=1.5)
    parser.add_option("--bright", dest="bright", type="float", default=1.5)
    opts, args = parser.parse_args()

    main()
  