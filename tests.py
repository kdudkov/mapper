#!/usr/bin/env python
# coding utf-8
__author__ = 'kd'

from unittest2 import TestCase, main
import gmap

size = 256
n, m = 76228, 37822
lat, lon = 60.329548, 29.367313
zoom = 17

class T1(TestCase):

    def test_merkator(self):
        "test number of tile"
        n1, m1 = gmap.lonlat_to_pixel(lat, lon, zoom)
        self.assertEquals((n, m), (int(n1 / size), int(m1 / size)), "wrong number of tile")

    def test_koord(self):
        n1, m1 = gmap.lonlat_to_pixel(lat, lon, zoom)
        xn, yn = 79, 22
        n1 -= size * n
        m1 -= size * m
        #print n1, m1
        self.assertTrue(abs(n1 - xn) < 5)
        self.assertTrue(abs(m1 - yn) < 5)

    def test_back(self):
        """test back conversion"""
        gx, gy = gmap.lonlat_to_pixel(lat, lon, zoom)
        lat1, lon1 = gmap.pixel_to_lonlat(gx, gy, zoom)
        self.assertTrue(abs(lat - lat1) < 0.00001)
        self.assertTrue(abs(lon - lon1) < 0.00005)

if __name__ == '__main__':
    main()