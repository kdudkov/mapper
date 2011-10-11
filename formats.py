#!/usr/bin/env python

from reportlab.lib import pagesizes
from reportlab.lib.units import cm, inch

__author__ = 'madrider'

k = 100

for ps in ['A0', 'A1', 'A2', 'A3', 'A4']:
    if ps in pagesizes.__dict__:
        page_size = pagesizes.__dict__[ps]
    else:
        raise Exception("smth. wrong")

    print "%s, 1:%s" % (ps, k * 1000)
    maxx, maxy = page_size
    page_border = 1 * cm

    xp1, yp1 = page_border, page_border
    xp2, yp2 = maxx - page_border, maxy - page_border
    yp2 -= 10 + 30 # for page title

    print "w = %s;\nh = %s" % (xp2 - xp1, yp2 - yp1)
