# coding: utf-8
import json
from mapper import Mapper
from tempfile import NamedTemporaryFile

__author__ = 'madrider'


class Opts(object):
    def __init__(self):
        self.config = None
        self.title = None
        self.filename = 'test_file'
        self.provider = 'OSM'
        self.zoom = 15


class TestMapper(object):
    used = False

    def empty(self, *args, **kw):
        self.used = True

    def setUp(self):
        self.used = False
        self.opts = Opts()
        self.mapper = Mapper(self.opts)
        self.mapper.save_config = self.empty

    def parse_opts_test(self):
        self.opts.title = 'название 1'.decode('utf-8')
        self.mapper.prepare()
        assert (self.mapper.config['title'] == u'название 1')
        assert self.used

    def load_config_test(self):
        config = {'title': 'название 2'}
        f = NamedTemporaryFile()
        json.dump(config, f, encoding='utf-8')
        f.flush()
        self.opts.config = f.name
        self.mapper.prepare()
        assert (self.mapper.config['title'] == u'название 2')

    def get_pagesize_test(self):
        assert self.mapper.get_page_size('a4') == self.mapper.get_page_size('A4')
        x, y = self.mapper.get_page_size('a4')
        assert self.mapper.get_page_size('a4', True) == (y, x)
        assert self.mapper.get_page_size('a3', False) == (y, x * 2)

    def get_coords_test(self):
        assert self.mapper.get_coords('235,117.2') == [235., 117.2]
