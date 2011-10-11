#!/usr/bin/env python
# coding: utf-8

import math

MAJOR_AXIS = 6378137.0 # meters 
MINOR_AXIS = 6356752.3142
MAJOR_AXIS_POW_2 = pow(MAJOR_AXIS, 2)
MINOR_AXIS_POW_2 = pow(MINOR_AXIS, 2)

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


class Point(object):
    lat = 0.0
    lon = 0.0
    elev = 0.0
    name = None

    def __init__(self, lon, lat, elev=0, name=None):
        self.lat = float(lat)
        self.lon = float(lon)
        self.elev = elev
        self.name = name
    
    def to_dms(self):
        return ""

# get arrays with gps coordinates, returns earth terrestrial distance between 2 points 
def distance(p1, p2): 

    true_angle_1 = get_true_angle(p1)
    true_angle_2 = get_true_angle(p2) 
         
    point_radius_1 = get_point_radius(p1, true_angle_1) 
    point_radius_2 = get_point_radius(p2, true_angle_2) 
         
    earth_point_1_x = point_radius_1 * math.cos(math.radians(true_angle_1)) 
    earth_point_1_y = point_radius_1 * math.sin(math.radians(true_angle_1)) 
         
    earth_point_2_x = point_radius_2 * math.cos(math.radians(true_angle_2)) 
    earth_point_2_y = point_radius_2 * math.sin(math.radians(true_angle_2)) 
        
    x = math.sqrt(pow((earth_point_1_x - earth_point_2_x), 2) + pow((earth_point_1_y - earth_point_2_y), 2))
    y = math.pi * ((earth_point_1_x + earth_point_2_x) / 360.) * (p1.lon - p2.lon) 
    
    fdPhi = math.radians(p1.lat - p2.lat)
    fdLambda = math.radians(p1.lon - p2.lon)
    fz = 2 * math.asin(math.sqrt (
        pow(math.sin( fdPhi / 2.0), 2 ) + math.cos(math.radians(p2.lat))
        * math.cos(math.radians(p1.lat)) * pow(math.sin(fdLambda / 2.0), 2)
    ) )
    fAlpha = math.asin(math.cos(math.radians(p2.lat)) * math.sin(fdLambda) / math.sin(fz))
    d = round(abs(math.degrees(fAlpha)))

    if p1.lon <= p2.lon:
        if p1.lat > p2.lat:
            d = 180 - d
    else:
        if p1.lat > p2.lat:
            d += 180
        else:
            d = 360 - d

    return math.sqrt(pow(x,2) + pow(y,2)), d


# get point, returns true angle 
def get_true_angle(p): 
    return math.degrees(math.atan(((MINOR_AXIS_POW_2 / MAJOR_AXIS_POW_2) * math.tan(math.radians(p.lat)))))


# get point and true angle, returns radius of small circle (radius between meridians)  
def get_point_radius(p, true_angle): 
    return (1 / math.sqrt((pow(math.cos(math.radians(true_angle)), 2) / MAJOR_AXIS_POW_2) + (pow(math.sin(math.radians(true_angle)), 2) / MINOR_AXIS_POW_2))) + p.elev

def mperdeg(lon, lat):
    n1 = distance(Point(lon, lat), Point(lon + 1, lat))[0]
    n2 = distance(Point(lon, lat), Point(lon, lat + 1))[0]
    return n1, n2
