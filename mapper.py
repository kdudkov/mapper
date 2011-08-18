#!/usr/bin/env python
# coding: utf-8
from math import floor
from optparse import OptionParser

from reportlab.lib.units import cm, mm, inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4, A3, landscape
import Image
from gmap import TILE_SIZE, lonlat_to_pixel, get_tile

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

def main():
    dpi = int(opts.dpi)
    page_size = A4
    title = 'Kannelyarvi'
    try:
        c1 = map(lambda x: float(x), opts.c1.split(',', 1))
        c2 = map(lambda x: float(x), opts.c2.split(',', 1))
    except:
        print "smth wrong in command line!"
        return 1

    lat1, lat2 = min(c1[0], c2[0]), max(c1[0], c2[0])
    lon1, lon2 = min(c1[1], c2[1]), max(c1[1], c2[1])

    zoom = opts.zoom
    x2tx = lambda x: int(x / TILE_SIZE)
    tx1, ty1 = map(x2tx, lonlat_to_pixel(lat1, lon1, zoom))
    tx2, ty2 = map(x2tx, lonlat_to_pixel(lat2, lon2, zoom))

    # size of map
    mapw, maph = (tx2 - tx1) * TILE_SIZE, (ty1 - ty2) * TILE_SIZE
    if mapw > maph:
        page_size = landscape(page_size)
    print "got %i x %i map" % (mapw, maph)

    c = Canvas(opts.filename, pagesize=page_size)
    maxx, maxy = page_size
    page_border = 1 * cm
    xp1, yp1 = page_border, page_border
    xp2, yp2 = maxx - page_border, maxy - page_border
    yp2 -= 10 + 14 # for page title
    # picture size we need to fit dpi
    imgw, imgh = map(lambda x: int(x / inch * dpi), (xp2 - xp1, yp2 - yp1))
    print "need %i x %i image for 1 page" % (imgw, imgh)


    # glue tiles to big picture
    map_img = Image.new("RGB", (abs(tx2 - tx1) * TILE_SIZE, abs(ty2 - ty1) * TILE_SIZE), (200, 200, 200))
    for ty in range(min(ty1, ty2), max(ty1, ty2) + 1):
        for tx in range(tx1, tx2 + 1):
            fname = get_tile(tx, ty, zoom)
            #print fname
            try:
                img1 = Image.open(fname)
            except:
                img1 = Image.new("RGB", (256, 256))
            xp, yp = TILE_SIZE * (tx - tx1), TILE_SIZE * (ty - min(ty1, ty2))
            map_img.paste(img1, (xp, yp))

    koeff = dpi / inch
    # pixels in deg of x axis (lon)
    pdegx = lonlat_to_pixel(lat1, lon1 + 1, zoom)[0] - lonlat_to_pixel(lat1, lon1, zoom)[0]
    pdegx /= koeff # to pdf pixels
    d_deg_x = 1
    for i in (dms2deg(0, 10, 0), dms2deg(0, 1, 0), dms2deg(0, 0, 30), dms2deg(0, 0, 10), dms2deg(0, 0, 5)):
        if i * pdegx < 1 * cm:
            break
        d_deg_x = i
    # pixels in deg of y axis (lat)
    pdegy = abs(lonlat_to_pixel(lat1 + 1, lon1, zoom)[1] - lonlat_to_pixel(lat1, lon1, zoom)[1])
    pdegy /= koeff # to pdf pixels
    d_deg_y = 1
    for i in (dms2deg(0, 30, 0), dms2deg(0, 10, 0), dms2deg(0, 1, 0), dms2deg(0, 0, 30), dms2deg(0, 0, 10), dms2deg(0, 0, 5)):
        if i * pdegy < 1 * cm:
            break
        d_deg_y = i
    #print deg2dms(d_deg_x), deg2dms(d_deg_y)
    
    dy = 0
    py = 1
    while dy < maph:
        dx = 0
        px = 1
        while dx < mapw:
            c.setFontSize(10)
            c.drawString(page_border, maxy - page_border - 10, '%s, page %s-%s' % (title, px, py))

            tmpw, tmph = min(imgw, mapw - dx), min(imgh, maph - dy)
            img11 = map_img.crop((dx, dy, dx + tmpw, dy + tmph))
            img11.copy()
            if tmpw < imgw or tmph < imgh:
                img1 = Image.new("RGB", (imgw, imgh), (250, 250, 250))
                img1.paste(img11, (0, 0))
            else:
                img1 = img11
            c.drawInlineImage(img1, xp1, yp1, xp2 - xp1, yp2 - yp1)
            c.setStrokeColorRGB(0.0, 0.0, 0.0)
            c.setLineWidth(1)
            c.rect(xp1, yp1, xp2 - xp1, yp2 - yp1)

            c.setStrokeAlpha(0.5)
            # draw x grid
            degx = int(lon1)
            x0, _ = lonlat_to_pixel(lat1, lon1, zoom)
            while 1:
                degx += d_deg_x
                x, _ = lonlat_to_pixel(lat1, degx, zoom)
                x -= x0
                if x <= dx:
                    continue
                if x >= dx + tmpw:
                    break
                xp = (x - dx) / koeff
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
                c.setFontSize(5)
                if opts.deg:
                    text = "%.4f" % degx
                else:
                    text = "%iº%i'%i\"" % (d, m, round(s))
                c.drawCentredString(xp + xp1, yp1 - 5, text)
                c.drawCentredString(xp + xp1, yp2 + 5, text)
            # draw y grid
            degy = int(lat2) + 1
            _, y0 = lonlat_to_pixel(lat2, lon1, zoom)
            while 1:
                degy -= d_deg_y
                _, y = lonlat_to_pixel(degy, lon1, zoom)
                y -= y0
                if y <= dy:
                    continue
                if y >= dy + tmph:
                    break
                yp = (y - dy) / koeff
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
                c.setFontSize(5)
                if opts.deg:
                    text = "%.4f" % degy
                else:
                    text = "%iº%i'%i\"" % (d, m, round(s))
                c.saveState()
                c.translate(xp1 - 5, yp2 - yp)
                c.rotate(90)
                c.drawCentredString(0, 0, text)
                c.restoreState()
                c.saveState()
                c.translate(xp2 + 5, yp2 - yp)
                c.rotate(90)
                c.drawCentredString(0, 0, text)
                c.restoreState()
            c.showPage()
            dx += int(imgw * 0.9)
            px += 1
        dy += int(imgh * 0.9)
        py += 1
    c.save()

if __name__ == '__main__':
    global opts

    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                  help="output pdf name", metavar="FILE", default="map.pdf")
    parser.add_option("--coords1", dest="c1",
                  help="lover bottom corner", metavar="lat1,lon1", default="60.3167,29.35")
    parser.add_option("--coords2", dest="c2",
                  help="upper top corner", metavar="lat2,lon2", default="60.33,29.38")
    parser.add_option("-z", "--zoom", dest="zoom",
                  help="zoom (10-18)", metavar="n", type="int", default="17")
    parser.add_option("-d", "--dpi", dest="dpi",
                  help="dpi", metavar="n", type="int", default="200")
    parser.add_option("--deg", dest="deg", action="store_true",
                  help="use d.dddd instead of d mm' s.sss", default=False)

    opts, args = parser.parse_args()

    main()
  