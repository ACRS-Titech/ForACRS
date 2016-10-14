# -*- coding:utf-8 -*-
import os
import sys
from PIL import Image
import numpy as np
import cv2
from matplotlib import pylab as plt
import sqlite3
from PIL.ExifTags import TAGS, GPSTAGS
import pickle
import time

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
  """ 画像を処理してファイルに結果を保存する """

  if imagename[-3:] != 'pgm':
    im = Image.open(imagename).convert('L')
    im.save('tmp.pgm')
    imagename = 'tmp.pgm'

  cmmd = str("./sift "+imagename+" --output="+resultname+ " "+params)
  os.system(cmmd)
  print 'processed', imagename, 'to', resultname

def read_features_from_file(filename):

  f = np.loadtxt(filename)
  return f[:,:4],f[:,4:]

def match(desc1,desc2):
  desc1 = np.array([d/np.linalg.norm(d) for d in desc1])
  desc2 = np.array([d/np.linalg.norm(d) for d in desc2])

  dist_ratio = 0.6
  desc1_size = desc1.shape

  matchscores = np.zeros(desc1_size[0],'int')
  desc2t = desc2.T

  for i in range(desc1_size[0]):
    dotprods = np.dot(desc1[i,:],desc2t)
    dotprods = 0.9999*dotprods
    indx = np.argsort(np.arccos(dotprods))

    if np.arccos(dotprods)[indx[0]] < dist_ratio * np.arccos(dotprods)[indx[1]]:
      matchscores[i] = int(indx[0])
  return matchscores

def compare_img(img):
  #<特徴点抽出>
  #データベース接続
  conn = sqlite3.connect("ACRS.db")
  cur = conn.cursor()
  sname=img+'.sift'
  process_image(img,sname)
  l1,d1 = read_features_from_file(sname) 
  #print 'Image',im_grey
  #print 'size',d1.ndim
  # print '\n'
  # <EXIF情報の取得>
  #もしEXIFがなければ０を返す
  try:
    start=time.time() 
    GPS=get_exif(img)
    lat,lon=calculate(GPS)
  except AttributeError:
    start=time.time() 
    lat=0
    lon=0
  cur.execute( "select * from feature_Point" )
  #データベースの格納画像数
  Num=2
  Num_list=['0','1','2','3','4','5','6','7','8','9']
  list_img=[]
  for i in range(4*Num): 
    data_db=cur.fetchone()
    for k in range(5):
      df=data_db[k]
      if df != None:
        list_img.append(df)
    if len(list_img)==5:
      list_name=[]
      name_fin=str( )
      for n in range(len(list_img[4])):
        if n>8:
          df_n=str(list_img[4][n])
          name_fin=name_fin+df_n
      list_name.append(name_fin)
      list_Pre=[]
      list_inf=[]
      N_fin=str(0)
      for j in range(len(list_img[2])):
        N=str(list_img[2][j])
        # print N
        for k in Num_list:
          if N==k:
            N_fin=N_fin+N
            #print N_fin
        if N==',':
          list_Pre.append(int(N_fin))
          N_fin=str(0)
        if N==']':
          list_Pre.append(int(N_fin))          
        if len(list_Pre)==128:
          list_inf.append(list_Pre)
          list_Pre=[]
      list_inf=np.array(list_inf)
      # creation for return img
      list_ret=[]
      list_ret_Pre=[]
      df_ret=str(0)
      for k in range(len(list_img[3])):
        img_df=str(list_img[3][k])
        for l in Num_list:
          if img_df==l:
            df_ret=df_ret+img_df
        if img_df==' ':
            list_ret_Pre.append(int(df_ret))
            df_ret=str(0)
        if img_df==']':
          if len(list_ret_Pre)>1:
            list_ret.append(list_ret_Pre)
            list_ret_Pre=[]
      if lat>0 and lon>0:
        if abs(lat-list_img[0])<0.5 and abs(lon-list_img[1])<0.5:
          d_db=list_inf
          #入力画像とフィルタ通過したデータベース画像の特徴点マッチング開始
          matches = match(d1,d_db)
          #共通特徴点数の閾値
          nbr_matches = sum(matches > 0)
          if nbr_matches>50:
            print 'number of matches = ', nbr_matches
            #matchscores[i,j] = nbr_matches
            # print 'imagename:{0}'.format(img_ex)
            #次のプロセス画像としてリターンされる画像のRGB
            lat,lon=lat_fin,lon_fin
            return lat_fin,lon_fin,list_name[0],list_inf
          if nbr_matches<49:
            print 'not mutch'
            lat_fin,lon_fin=0,0
        elapsed_time = time.time() - start
        list_img=[]
        print ("elapsed_time:{0}".format(elapsed_time)) + "[sec]"
      if lat ==0 and lon==0:
        lat_fin=list_img[0]
        lon_fin=list_img[1]
        print 'No_GPS'
        d_db=list_inf
        #入力画像とデータベース画像の特徴点マッチング開始
        matches = match(d1,d_db)
        print matches
        #共通特徴点数の閾値
        nbr_matches = sum(matches > 0)
        if nbr_matches>50:
          print 'number of matches = ', nbr_matches
          #matchscores[i,j] = nbr_matches
          # print 'imagename:{0}'.format(img_ex)
          #次のプロセス画像としてリターンされる画像のRGB
          return lat_fin,lon_fin,list_name[0],list_inf
        if nbr_matches<49:
          print 'not mutch'
          lat_fin,lon_fin=0,0
      list_img=[]
      elapsed_time = time.time() - start
      print ("elapsed_Matchingtime:{0}".format(elapsed_time)) + "[sec]"

#img='KandaMyoujin.jpg'
#lat,lon,name,inf=compare_img(img)
