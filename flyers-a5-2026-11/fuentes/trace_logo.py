import sys, json, numpy as np
from PIL import Image, ImageFilter
import potrace
src, out, prev = sys.argv[1], sys.argv[2], sys.argv[3]
im = Image.open(src).convert('L').crop((60,20,440,230))
a = np.array(im)
ys, xs = np.where(a < 110)
x0,x1,y0,y1 = xs.min()-2, xs.max()+3, ys.min()-2, ys.max()+3
im = im.crop((x0,y0,x1,y1))
S = 8
big = im.resize((im.width*S, im.height*S), Image.LANCZOS).filter(ImageFilter.GaussianBlur(S*0.35))
mask = np.array(big) < 128
bmp = potrace.Bitmap(~mask)
path = bmp.trace(turdsize=20, alphamax=1.0, opticurve=True, opttolerance=0.2)
W, H = big.width, big.height
curves = []
for c in path:
    segs = []
    for s in c.segments:
        if s.is_corner:
            segs.append(['L', s.c.x, s.c.y, s.end_point.x, s.end_point.y])
        else:
            segs.append(['C', s.c1.x, s.c1.y, s.c2.x, s.c2.y, s.end_point.x, s.end_point.y])
    curves.append({'start':[c.start_point.x, c.start_point.y], 'segs':segs})
json.dump({'w':W,'h':H,'curves':curves}, open(out,'w'))
# preview svg->png via PIL draw
from PIL import ImageDraw
pv = Image.new('RGB',(W//2,H//2),(250,183,20))
# quick raster preview using the mask
m = Image.fromarray((~mask*255).astype('uint8')).resize((W//2,H//2))
pv.paste((0,0,0), mask=Image.eval(m, lambda v:255-v))
pv.save(prev)
print(W,H,len(curves))
