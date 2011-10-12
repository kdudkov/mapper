#!/usr/bin/env python
# coding: utf-8

import os
import glob
from optparse import OptionParser

from reportlab.lib import pagesizes
from reportlab.lib.units import cm, mm, inch
from reportlab.pdfbase import pdfmetrics, ttfonts
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import landscape
from gmap import GmapMap

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

def main():
    DMS_GRID = (dms2deg(0, 30, 0), dms2deg(0, 10, 0), dms2deg(0, 1, 0), dms2deg(0, 0, 30), dms2deg(0, 0, 10), dms2deg(0, 0, 5), dms2deg(0, 0, 2), dms2deg(0, 0, 1))
    D_GRID = [1]
    for i in range(1, 5):
        for c in [5, 2, 1]:
            D_GRID.append(c * pow(10, -i))
    FONT = 'Droid'
    pdfmetrics.registerFont(ttfonts.TTFont(FONT, 'DroidSansMono.ttf'))
    if opts.ps.upper() in pagesizes.__dict__:
        page_size = pagesizes.__dict__[opts.ps.upper()]
    else:
        raise Exception("%s is frong page format" % opts.ps)
    if opts.land:
        page_size = landscape(page_size)
    try:
        lon1, lat1 = map(lambda x: float(x), opts.c.split(',', 1))
    except:
        print "smth wrong in command line!"
        return 1

    # page size
    c = Canvas(opts.filename + '.pdf', pagesize=page_size)
    maxx, maxy = page_size
    page_border = 1 * cm
    xp1, yp1 = page_border, page_border
    xp2, yp2 = maxx - page_border, maxy - page_border
    yp2 -= 10 + 30 # for page title

    # full area size
    full_size = (1. + (opts.numx - 1) * (1. - PEREKR)) * (xp2 - xp1), (1. + (opts.numy - 1) * (1. - PEREKR)) * (yp2 - yp1)
    print "we need %i x %i image for pdf" % full_size
    # size in meters
    size_m = map(lambda x: x / cm * opts.scale, full_size)
    kx, ky = gpslib.mperdeg(lon1, lat1)
    lon2, lat2 = lon1 + size_m[0] / kx, lat1 - size_m[1] / ky
    zoom = opts.zoom
    map_ = GmapMap()
    map_.set_ll(lon1, lat1, lon2, lat2, zoom)
    map_.get_map(download=opts.download)
    map_.enhance(brightness=opts.bright, contrast=opts.contrast)
    if opts.kml:
        map_.draw_kml(opts.kml)
    map_.save(opts.filename + '.jpg')

    print "got %i x %i map" % (map_.fullsize.x, map_.fullsize.y)
    # map to pdf pixels
    koeffx, koeffy = map_.mapsize.x / full_size[0], map_.mapsize.y / full_size[1]
    one_page_size_x, one_page_size_y = int((xp2 - xp1) * koeffx), int((yp2 - yp1) * koeffy)
    dpi = inch * one_page_size_x / (xp2 - xp1)
    print "result is %i dpi" % dpi
    
    # pixels in deg of x axis (lon)
    pdegx = abs(map_.lonlat2xy(lon1 + 1, lat1)[0] - map_.lonlat2xy(lon1, lat1)[0])
    pdegx /= koeffx # to pdf pixels

    if opts.deg:
        grid = D_GRID
    else:
        grid = DMS_GRID
    d_deg_x = 1
    min_grid_with = 2 * cm
    for i in grid:
        if i * pdegx < min_grid_with:
            break
        d_deg_x = i
    # pixels in deg of y axis (lat)
    pdegy = abs(map_.lonlat2xy(lon1, lat1 + 1)[1] - map_.lonlat2xy(lon1, lat1)[1])
    pdegy /= koeffy # to pdf pixels
    d_deg_y = 1
    for i in grid:
        if i * pdegy < min_grid_with:
            break
        d_deg_y = i
    m_in_cm_x = gpslib.distance(gpslib.Point(lon1, lat1), gpslib.Point(lon1 + cm / pdegx, lat1))[0]
    m_in_cm_y = gpslib.distance(gpslib.Point(lon1, lat1), gpslib.Point(lon1, lat1 + cm / pdegy))[0]
    #print m_in_cm_x, m_in_cm_y

    # splitting map to pdf pages
    for py in range(opts.numy):
        for px in range(opts.numx):
            c.setFont(FONT, 10)
            c.drawString(xp1, maxy - page_border - 10, '%s (1см = %iм)' % (opts.title, round(m_in_cm_x)))
            # draw 1cm angle
            xx1 = xp2
            yy1 = maxy - page_border - 5
            c.line(xx1 - cm, yy1, xx1, yy1)
            c.line(xx1, yy1, xx1, yy1 - cm)
            tx1 = map_.xp1 + int(one_page_size_x * (1. - PEREKR) * px)
            ty1 = map_.yp1 + int(one_page_size_y * (1. - PEREKR) * py)

            img1 = map_.map_img.crop((tx1, ty1, tx1 + one_page_size_x, ty1 + one_page_size_y))
            img1.load()
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
                if x <= tx1:
                    continue
                if x >= tx1 + one_page_size_x:
                    break
                xp = (x - tx1) / koeffx
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
                if y <= ty1:
                    continue
                if y >= ty1 + one_page_size_y:
                    break
                yp = (y - ty1) / koeffy
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
    c.save()

if __name__ == '__main__':
    global opts

    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                  help="output pdf name", metavar="FILE", default="map")
    parser.add_option("-t", "--title", dest="title",
                  help="map title", default="Каннельярви")
    parser.add_option("--coords", dest="c",
                  help="lover bottom corner", metavar="lon,lat", default="29.35,60.3167")
    parser.add_option("-z", "--zoom", dest="zoom",
                  help="zoom (10-18)", metavar="n", type="int", default=17)
    parser.add_option("--deg", dest="deg", action="store_true",
                  help="use d.dddd instead of d mm' s.sss", default=False)
    parser.add_option("--scale", dest="scale", type="int",
                  help="scale in meters in cm", default=0)
    parser.add_option("--px", "--pages_x", dest="numx", type="int",
                  help="n pages with", default=1)
    parser.add_option("--py", "--pages_y", dest="numy", type="int",
                  help="n pages height", default=1)
    parser.add_option("--page_size", dest="ps",
                  help="page format (A4, A3, etc)", default="A4")
    parser.add_option("--land", dest="land", action="store_true",
                  help="landscape page orientation", default=False)
    parser.add_option("--contrast", dest="contrast", type="float", default=1.5)
    parser.add_option("--bright", dest="bright", type="float", default=1.5)
    parser.add_option("-k", "--kml", dest="kml", metavar="FILE",
                  help="kml file", default='')
    parser.add_option("--dry", dest="download", action="store_false",
                  help="do not download tiles", default=True)
    opts, args = parser.parse_args()

    try:
        main()
    except KeyboardInterrupt:
        print "interrupted"
    except Exception, ex:
        raise ex
    finally:
        print "deleting temp files"
        for s in glob.glob('tmp*.jpg'):
            os.unlink(s)
            pass

  