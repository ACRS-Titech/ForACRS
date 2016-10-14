# -*- coding:utf-8 -*-
import sqlite3
from PIL.ExifTags import TAGS,GPSTAGS
import time
import os
import sys
import numpy as np
from matplotlib import pylab as plt
from PIL import Image

# ExifからGPSの取得
def get_exif(file):
  img = Image.open(file)
  df=np.array(Image.open(file))
  exif = img._getexif()

  exif_data = []
  for id, value in exif.items():
    #print 'ID',TAGS.get(id),'\n'
    ID = TAGS.get(id)
    tag = TAGS.get(id, id),value
    #print 'Tag',tag,'\n'
    if ID == 'GPSInfo': 
      exif_data.extend(tag)
  return exif_data

#緯度・経度の算出関数（10進数）
def calculate(GPS):
  lat_ex=GPS[1][2]
  lon_ex=GPS[1][4]
  lat_a=float(lat_ex[0][0]/lat_ex[0][1])
  lat_b=float(lat_ex[1][0]/lat_ex[1][1])
  lat_c=float(lat_ex[2][0]/lat_ex[2][1])
  lat=lat_a+(lat_b/60.0)+(lat_c/60.0/60.0)

  lon_a=float(lon_ex[0][0]/lon_ex[0][1])
  lon_b=float(lon_ex[1][0]/lon_ex[1][1])
  lon_c=float(lon_ex[2][0]/lon_ex[2][1])
  lon=lon_a+(lon_b/60.0)+(lon_c/60.0/60.0)
  return lat,lon

def process_image(imagename,resultname,params="--edge-thresh 10 --peak-thresh 5"):
  if imagename[-3:] != 'pgm':
    # ダウンサンプリングpgmファイルを作成する
    im = np.array(Image.open(imagename).convert('L'))
    im= im[::15, ::15]
    im= Image.fromarray(np.uint8(im))
    im.save('tmp.pgm')
    imagename = 'tmp.pgm'

  cmmd = str("./sift "+imagename+" --output="+resultname+ " "+params)
  os.system(cmmd)
  print 'processed', imagename, 'to', resultname

def read_features_from_file(filename):

  f = np.loadtxt(filename)
  return f[:,:4],f[:,4:]

def create_DB():
  #はじめにデータベース作成を行う
  start=time.time()
  conn = sqlite3.connect("ACRS.db")
  cur = conn.cursor()
  cur.execute("""CREATE TABLE feature_Point(lat real,lon real,d text,img text,name text);""")
  path='Data_Box'
  imlist = [os.path.join(path,f) for f in os.listdir(path) if f.endswith('.jpg')]
  # データベース格納のための特徴点、GPS情報の算出
  Num=0
  for img_ex in imlist:
    im_grey = np.array(Image.open(img_ex).convert('L'))
    Num=Num+1
    RGB=np.array(Image.open(img_ex))
    name,ext=os.path.splitext(img_ex)
    sname = img_ex+'.sift'
    process_image(img_ex,sname)
    l_db,d_db = read_features_from_file(sname) 
    GPS_db=get_exif(img_ex)
    lat_db,lon_db=calculate(GPS_db)
    #print 'Data',lat_db,lon_db
    #データベースへ格納するため、stringへ変換
    img_str=str(im_grey)
    d_list=[]
    for j in range(len(d_db)):
      df=d_db[j]
      for k in range(len(d_db[1])):
        df_1=int(df[k])
        d_list.append(df_1)
    d_list=str(d_list)
    gray_list=[]
    for j in range(len(im_grey)):
      df=im_grey[j]
      gray=[]
      for k in range(len(im_grey[1])):
        df_1=int(df[k])
        gray.append(df_1)
      gray_list.append(gray)
    gray_list=str(gray_list)
    print 'GRAY',gray_list
    #データベースへ格納
    sql="""INSERT INTO feature_Point(lat,lon) VALUES(?,?)"""
    cur.execute(sql, (lat_db,lon_db))
    sql="""INSERT INTO feature_Point(d) VALUES(?)"""
    cur.execute(sql, ([d_list]))
    sql="""INSERT INTO feature_Point(img) VALUES(?)"""
    cur.execute(sql, [gray_list])
    sql="""INSERT INTO feature_Point(name) VALUES(?)"""
    cur.execute(sql, [name])
    conn.commit()
    elapsed_time = time.time() - start
    print ("elapsed_Databese_time:{0}".format(elapsed_time)) + "[sec]"

create_DB()
