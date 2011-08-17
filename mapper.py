#!/usr/bin/env python
# coding: utf-8
from math import floor

from reportlab.lib.units import cm, mm, inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4, A3, landscape
import Image
from gmap import TILE_SIZE, lonlat_to_pixel, get_tile

__author__ = 'madrider'

def main():
    dpi = 200
    page_size = A4
    # kanni
    lat1, lon1 = 60.3189, 29.3556
    lat2, lon2 = 60.3332, 29.3784

    zoom = 17
    x2tx = lambda x: int(x / TILE_SIZE)
    tx1, ty1 = map(x2tx, lonlat_to_pixel(lat1, lon1, zoom))
    tx2, ty2 = map(x2tx, lonlat_to_pixel(lat2, lon2, zoom))

    # size of map
    imgw, imgh = (tx2 - tx1) * TILE_SIZE, (ty1 - ty2) * TILE_SIZE
    if imgw > imgh:
        page_size = landscape(page_size)
    print "got %i x %i map" % (imgw, imgh)

    c = Canvas('map1.pdf', pagesize=page_size)
    maxx, maxy = page_size
    page_border = 1 * cm
    xp1, yp1 = page_border, page_border
    xp2, yp2 = maxx - page_border, maxy - page_border
    yp2 -= 10 + 4 # for page title
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

    dy = 0
    py = 1
    while dy < imgh:
        dx = 0
        px = 1
        while dx < imgw:
            c.setStrokeColorRGB(0.0, 0.0, 0.0)
            c.setFontSize(10)
            c.drawString(page_border, maxy - page_border - 10, 'Kannelyarvi, page %s-%s' % (px, py))


            img1 = map_img.crop((dx, dy, dx + imgw, dy + imgh))
            img1.copy()
            c.drawInlineImage(img1, xp1, yp1, xp2 - xp1, yp2 - yp1)
            c.rect(xp1, yp1, xp2 - xp1, yp2 - yp1)
            c.showPage()
            dx += int(imgw * 0.9)
            px += 1
        dy += int(imgh * 0.9)
        py += 1
    c.save()

if __name__ == '__main__':
    main()
  