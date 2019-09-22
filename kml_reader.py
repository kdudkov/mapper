__author__ = 'madrider'

import xml.etree.cElementTree as etree
from pprint import pprint

def process(f):
    res = {'points': [], 'lines':[]}
    tree = etree.parse(open(f, 'r')).getroot()
    for f in tree.findall("*//%sPlacemark" % k):
        name = f.find('%sname' % k).text
        if f.find('%sLineString' % k):
            s = f.find('%sLineString/%scoordinates' % (k, k)).text
            c = []
            for ss in s.strip().split():
                lon, lat = ss.split(',')
                c.append((float(lon), float(lat)))
            res['lines'].append({'name':name, 'coords':c})

        elif f.find('%sPoint' % k):
            s = f.find('%sPoint/%scoordinates' % (k, k)).text.strip()
            lon, lat = s.split(',')
            res['points'].append({'name':name, 'lon':float(lon), 'lat':float(lat)})
    return res

k = '{http://www.opengis.net/kml/2.2}'
if __name__ == '__main__':
    pprint(process('holm.kml'))
  