#!/usr/bin/env python
# coding: utf-8

import codecs
import json
import os
import pprint
import sys
from optparse import OptionParser
import tempfile
import logging

from reportlab.lib import pagesizes
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics, ttfonts
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import landscape

from maps import YandexSat, OsmMap, CycleMap

import gpslib

__author__ = 'madrider'

PEREKR = 0.2
WORKDIR = os.path.join(os.path.dirname(__file__), 'maps')


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
    if s < 0.001:
        s = 0
    return d, m, s


def dms2deg(d, m, s):
    return d + m / 60. + s / 3600.


class Mapper(object):
    FONT = 'Droid'
    config = {'provider': 'YSAT', 'deg': False, 'numx': 1, 'numy': 1, 'ps': 'A4', 'bright': 1, 'contrast': 1,
              'land': False}

    def __init__(self, opts):
        self.opts = opts
        self.pdf = None
        self.map_provider = None

    def run(self):
        self.prepare()
        self.calculate_coords()
        self.get_image()
        self.to_pdf()

    def prepare(self):
        if not os.path.isdir(WORKDIR):
            os.mkdir(WORKDIR)
        pdfmetrics.registerFont(ttfonts.TTFont(self.FONT, 'DroidSansMono.ttf'))
        self.parse_opts(self.opts)
        self.save_config()
        pprint.pprint(self.config)
        self.map_provider = self.get_provider()
        logging.info('Use %s map provider', self.map_provider.__class__.__name__)

    def parse_opts(self, opts):
        if opts.config:
            if not os.path.isfile(opts.config):
                logging.error("cannot found %s", opts.config)
                print "cannot found %s" % opts.config
                sys.exit(1)
            logging.info("load config from %s", opts.config)
            with codecs.open(opts.config, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        for k, v in opts.__dict__.iteritems():
            if v:
                self.config[k] = v
        if not self.config.get('config', ''):
            self.config['config'] = os.path.join(WORKDIR, self.config['filename'] + '.json')

    def save_config(self):
        fname = self.config['config']
        logging.info('save config to %s', fname)
        with codecs.open(fname, 'w', encoding='utf-8') as f:
            json.dump(self.config, f)

    def get_provider(self):
        if self.config['provider'].upper() == 'YSAT':
            return YandexSat()
        elif self.config['provider'].upper() == 'OSM':
            return OsmMap()
        elif self.config['provider'].upper() == 'OSMCYCLE':
            return CycleMap()
        else:
            raise Exception('invalid map provider')

    def get_grid(self):
        if self.config['deg']:
            grid = [1]
            for i in range(1, 5):
                for c in [5, 2, 1]:
                    grid.append(c * pow(10, -i))
            return grid
        else:
            return (dms2deg(0, 30, 0), dms2deg(0, 10, 0), dms2deg(0, 1, 0), dms2deg(0, 0, 30), dms2deg(0, 0, 10),
                    dms2deg(0, 0, 5), dms2deg(0, 0, 2), dms2deg(0, 0, 1))

    def get_page_size(self, ps, land=False):
        if ps.upper() in pagesizes.__dict__:
            page_size = pagesizes.__dict__[ps.upper()]
        else:
            raise Exception("%s is frong page format" % ps)
        if land:
            page_size = landscape(page_size)
        return page_size

    def get_coords(self, coords):
        return map(lambda x: float(x), coords.split(',', 1))

    def calculate_coords(self):
        self.maxx, self.maxy = self.get_page_size(self.config['ps'], self.config['land'])
        self.lon1, self.lat1 = self.get_coords(self.config['coords'])
        page_border = 1 * cm
        self.xp1, self.yp1 = page_border, page_border
        self.xp2, self.yp2 = self.maxx - page_border, self.maxy - page_border
        self.yp2 -= 10 + 30  # for page title

        self.full_size = (1. + (self.config['numx'] - 1) * (1. - PEREKR)) * (self.xp2 - self.xp1), (1. + (
            self.config['numy'] - 1) * (1. - PEREKR)) * (self.yp2 - self.yp1)
        logging.info("we need %i px x %i px image for pdf", self.full_size[0], self.full_size[1])
        # size in meters
        image_size_meters = map(lambda x: x / cm * self.config['scale'], self.full_size)
        mperdegx, mperdegy = gpslib.mperdeg(self.lon1, self.lat1)
        self.lon2, self.lat2 = self.lon1 + image_size_meters[0] / mperdegx, self.lat1 - image_size_meters[1] / mperdegy

    def get_image(self):
        self.map_provider.set_ll(self.lon1, self.lat1, self.lon2, self.lat2, self.config['zoom'])
        self.map_provider.get_map(download=self.config['download'])
        logging.info("got %i x %i map", self.map_provider.big_pixels.w, self.map_provider.big_pixels.h)
        self.map_provider.enhance(brightness=self.config['bright'], contrast=self.config['contrast'])
        if self.config.get('kml'):
            logging.info('applying kml from %s', self.config['kml'])
            self.map_provider.draw_kml(self.config['kml'])
        fname = os.path.join(WORKDIR, self.config['filename'] + '.jpg')
        logging.info("save to %s", fname)
        self.map_provider.save(fname)

    def mapxy_2_pdfxy(self, x, y):
        """ map image coordinates to pdf coordinates """
        width, height = self.map_provider.img.size
        koeffx = width / self.full_size[0]
        koeffy = height / self.full_size[1]
        return int(x / koeffx), int(y / koeffy)

    def pdfxy_2_mapxy(self, x, y):
        """ map image coordinates to pdf coordinates """
        width, height = self.map_provider.img.size
        koeffx = width / self.full_size[0]
        koeffy = height / self.full_size[1]
        return int(x * koeffx), int(y * koeffy)

    def format_coord(self, coord):
        if self.config['deg']:
            return "%.4f" % coord
        else:
            d, m, s = deg2dms(coord)
            return "%iº%0.2i'%0.2i\"" % (d, m, round(s))

    def get_grid_step(self, pdeg):
        d_deg = 1
        min_grid_with = 1. * cm
        for i in self.get_grid():
            if i * pdeg < min_grid_with:
                break
            d_deg = i
        return d_deg

    def get_x_grid(self, xm1, xm2, step):
        degx = int(self.lon1)
        while 1:
            degx += step
            x, _ = self.map_provider.lonlat2xy(degx, self.lat1)
            if x <= xm1:
                continue
            if x >= xm2:
                return
            yield x, degx

    def get_y_grid(self, ym1, ym2, step):
        degy = int(self.lat1) + 1
        while 1:
            degy -= step
            _, y = self.map_provider.lonlat2xy(self.lon1, degy)
            if y <= ym1:
                continue
            if y >= ym2:
                return
            yield y, degy

    def prepare_line(self, deg):
        if not self.config['deg']:
            d, m, s = deg2dms(deg)
            if m == 0 and s == 0:
                # degree line
                self.pdf.setStrokeAlpha(0.7)
                self.pdf.setLineWidth(1)
                self.pdf.setStrokeColorRGB(0, 0, 0)
            elif s == 0:
                # minute line
                self.pdf.setStrokeAlpha(0.5)
                self.pdf.setLineWidth(1)
                self.pdf.setStrokeColorRGB(0, 0, 0)
            else:
                self.pdf.setStrokeAlpha(0.2)
                self.pdf.setLineWidth(1)
                self.pdf.setStrokeColorRGB(0, 0, 0)
        else:
            self.pdf.setStrokeAlpha(0.5)
            self.pdf.setLineWidth(1)
            self.pdf.setStrokeColorRGB(0, 0, 0)

    def add_page(self, image, xm1, ym1, xm2, ym2):
        self.pdf.setFont(self.FONT, 10)
        self.pdf.setTitle(self.config['title'])
        self.pdf.drawString(self.xp1, self.yp2 + 20, u'%s (1см = %iм)' % (self.config['title'], self.config['scale']))

        pfname = tempfile.mktemp()
        image.save(pfname, 'JPEG')
        self.pdf.drawImage(pfname, self.xp1, self.yp1, self.xp2 - self.xp1, self.yp2 - self.yp1)
        self.pdf.setStrokeColorRGB(0.0, 0.0, 0.0)
        self.pdf.setLineWidth(1)
        self.pdf.rect(self.xp1, self.yp1, self.xp2 - self.xp1, self.yp2 - self.yp1)
        self.pdf.setFont(self.FONT, 4)
        # x grid
        pdegx = self.full_size[0] / abs(self.lon1 - self.lon2)
        x_grid_step = self.get_grid_step(pdegx)
        for x, degx in self.get_x_grid(xm1, xm2, x_grid_step):
            x1, _ = self.mapxy_2_pdfxy(x - xm1, 0)
            self.prepare_line(degx)
            self.pdf.line(self.xp1 + x1, self.yp1, self.xp1 + x1, self.yp2)
            text = self.format_coord(degx)
            self.pdf.drawCentredString(x1 + self.xp1, self.yp1 - 5, text)
            self.pdf.drawCentredString(x1 + self.xp1, self.yp2 + 5, text)
            # y grid
        pdegy = self.full_size[1] / abs(self.lat1 - self.lat2)
        y_grid_step = self.get_grid_step(pdegy)
        for y, degy in self.get_y_grid(ym1, ym2, y_grid_step):
            _, y1 = self.mapxy_2_pdfxy(0, y - ym1)
            self.prepare_line(degy)
            self.pdf.line(self.xp1, self.yp2 - y1, self.xp2, self.yp2 - y1)
            text = self.format_coord(degy)
            self.pdf.saveState()
            self.pdf.translate(self.xp1 - 5, self.yp2 - y1)
            self.pdf.rotate(90)
            self.pdf.drawCentredString(0, 0, text)
            self.pdf.restoreState()
            self.pdf.saveState()
            self.pdf.translate(self.xp2 + 10, self.yp2 - y1)
            self.pdf.rotate(90)
            self.pdf.drawCentredString(0, 0, text)
            self.pdf.restoreState()
        self.pdf.showPage()

    def to_pdf(self):
        self.pdf = Canvas(os.path.join(WORKDIR, self.config['filename'] + '.pdf'), pagesize=[self.maxx, self.maxy])
        one_page_size_x, one_page_size_y = self.pdfxy_2_mapxy(self.xp2 - self.xp1, self.yp2 - self.yp1)
        for py in range(self.config['numy']):
            for px in range(self.config['numx']):
                tx1 = int(one_page_size_x * (1. - PEREKR) * px)
                ty1 = int(one_page_size_y * (1. - PEREKR) * py)
                img = self.map_provider.img.crop((tx1, ty1, tx1 + one_page_size_x, ty1 + one_page_size_y))
                img.load()
                self.add_page(img, tx1, ty1, tx1 + one_page_size_x, ty1 + one_page_size_y)
        self.pdf.save()


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("--config", dest="config", help="config", metavar="FILE", default=None)
    parser.add_option("-f", "--file", dest="filename", help="output pdf name (without extensions)", metavar="FILE")
    parser.add_option("--provider", dest="provider", help="map provider", metavar="(YSAT, OSM, CYCLE)")
    parser.add_option("-t", "--title", dest="title", help="map title")
    parser.add_option("--coords", dest="coords", help="lover bottom corner", metavar="lon,lat")
    parser.add_option("-z", "--zoom", dest="zoom", help="zoom (10-18)", metavar="n", type="int")
    parser.add_option("--deg", dest="deg", action="store_true", help="use d.dddd instead of d mm' s.sss")
    parser.add_option("--scale", dest="scale", type="int", help="scale in meters in cm")
    parser.add_option("--px", "--pages_x", dest="numx", type="int", help="n pages with")
    parser.add_option("--py", "--pages_y", dest="numy", type="int", help="n pages height")
    parser.add_option("--page_size", dest="ps", help="page format (A4, A3, etc)")
    parser.add_option("--land", dest="land", action="store_true", help="landscape page orientation", default=False)
    parser.add_option("--contrast", dest="contrast", type="float", default=1)
    parser.add_option("--bright", dest="bright", type="float", default=1)
    parser.add_option("-k", "--kml", dest="kml", metavar="FILE", help="kml file")
    parser.add_option("--dry", dest="download", action="store_false", help="do not download tiles", default=True)

    opts, _ = parser.parse_args()
    logging.basicConfig(level='INFO')

    if not opts.config:
        if opts.title:
            opts.title = opts.title.decode('utf-8')
        if not opts.filename:
            parser.error('output pdf filename required')
        if not opts.zoom:
            parser.error('zoom value required')
        if not opts.coords:
            parser.error('coords required')

    try:
        m = Mapper(opts)
        m.run()
    except KeyboardInterrupt:
        print "interrupted"
#    except Exception, ex:
#        raise ex
