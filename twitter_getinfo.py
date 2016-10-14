#!/usr/bin/env python
#-*- coding:utf-8 -*-
import Matching

def get_info(imagepath):
    
    lat,lon,name,inf=Matching.compare_img(imagepath)
    return lat, lon, name, inf

def getcamerainfo():
    cameraLoc = "hoge, piyo"
    return cameraLoc

def getLandScapeinfo():
    LandscapeName = "foo"
    return LandscapeName


