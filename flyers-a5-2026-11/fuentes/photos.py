import sys, numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageOps, ImageEnhance
U='/mnt/user-data/uploads/'; out=sys.argv[1]
AR = 154/143.0
# Man: remove shirt brand logo, B&W
im = Image.open(U+'stocksnap-people-2576682_1920.jpg').convert('RGB')
patch = im.crop((1400,452,1450,492))
mask = Image.new('L', patch.size, 0); ImageDraw.Draw(mask).ellipse((2,2,46,38), fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(3))
im.paste(patch, (1437,399), mask)
ImageEnhance.Contrast(ImageOps.grayscale(im)).enhance(1.12).save(out+'/full_hombre.png')
im = im.crop((540,0,1640,int(1100/AR)))
g = ImageOps.grayscale(im); g = ImageEnhance.Contrast(g).enhance(1.12)
g.save(out+'/foto_hombre.png'); 
# Woman: crop out egg carton, B&W
im = Image.open(U+'sunriseforever-housewife-5509154_1920.jpg').convert('RGB')
import cv2  # caja de huevos con texto ruso: se borra rellenando con la encimera
arr = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
msk = np.zeros(arr.shape[:2], np.uint8)
cv2.fillPoly(msk, [np.array([[808,1000],[900,935],[1060,935],[1125,1000],[1125,1075],[1060,1125],[905,1125],[808,1080]])], 255)
msk = cv2.dilate(msk, np.ones((9,9),np.uint8))
arr = cv2.inpaint(arr, msk, 25, cv2.INPAINT_TELEA)
rng = np.random.default_rng(1); noise = rng.normal(0, 5, arr.shape[:2])
m = cv2.GaussianBlur(msk.astype(float)/255, (31,31), 0)
arr = np.clip(arr + (noise*m)[...,None], 0, 255).astype(np.uint8)
im = Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))
ImageEnhance.Contrast(ImageOps.grayscale(im)).enhance(1.15).save(out+'/full_mujer.png')
w = 1290; h = int(w/AR); im = im.crop((430,0,430+w,h))
g = ImageOps.grayscale(im); g = ImageEnhance.Contrast(g).enhance(1.15); g = ImageEnhance.Brightness(g).enhance(0.97)
g.save(out+'/foto_mujer.png')
# Banknote: zoomed crop (shown >125% of real size), CMYK with black generation
im = Image.open(U+'cosmix-euro-note-1205315_1920.jpg').convert('RGB')
w = int(1080*AR); im = im.crop((1920-w,0,1920,1080))
im.save(out+'/foto_billete_rgb.png')
a = np.asarray(im).astype(float)/255
k = 1-a.max(axis=2); d = np.clip(1-k,1e-6,1)
c = (1-a[...,0]-k)/d; m=(1-a[...,1]-k)/d; y=(1-a[...,2]-k)/d
cmyk = np.stack([c,m,y,k*0.95],axis=2)
Image.fromarray((np.clip(cmyk,0,1)*255).astype('uint8'),'CMYK').save(out+'/foto_billete_cmyk.tif')
Image.open(out+'/foto_hombre.png').crop((800,300,1100,560)).save(out+'/chk_shirt.png')
print('ok')
