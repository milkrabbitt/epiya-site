from pathlib import Path
import math
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1]
lines=[]
for i in range(84):
 a=i/84*math.tau; points=[]
 for j in range(171):
  t=j/170*math.tau;r=1.3+.42*math.cos(3*t);tube=.19*math.cos(a);rise=.19*math.sin(a)
  x=(r+tube)*math.cos(2*t);y=(r+tube)*math.sin(2*t);z=.6*math.sin(3*t)+rise
  rx=-.65;ry=.28;rz=-.45
  y1=y*math.cos(rx)-z*math.sin(rx);z1=y*math.sin(rx)+z*math.cos(rx)
  x2=x*math.cos(ry)+z1*math.sin(ry);z2=-x*math.sin(ry)+z1*math.cos(ry)
  x3=x2*math.cos(rz)-y1*math.sin(rz);y3=x2*math.sin(rz)+y1*math.cos(rz)
  p=4.6/(4.6-z2);points.append((450+x3*202.5*p,450+y3*202.5*p))
 lines.append(points)
paths=[]
for i,pts in enumerate(lines):
 color=['#bacb82','#c6bb8b','#a5bd8c'][i//29 if i//29<3 else 2]
 d='M'+' L'.join(f'{x:.2f} {y:.2f}' for x,y in pts)
 paths.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width=".8" opacity="{.3+i%6*.07:.2f}"/>')
(R/'assets/sculpture.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 900">' + ''.join(paths)+'</svg>')
(R/'assets/favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#d7ff72"/><path d="M45 37H20c1 7 12 10 20 3l6 7C31 61 8 50 8 31 8 7 52 5 52 32v5zm-25-9h19c-1-9-17-9-19 0" fill="#111210"/></svg>')
im=Image.new('RGB',(1200,630),'#111210');d=ImageDraw.Draw(im)
for i,pts in enumerate(lines):
 d.line([(x*.78+480,y*.78-40) for x,y in pts],fill=['#7c8c52','#9b9572','#8d9e6d'][min(i//29,2)],width=1)
font='/System/Library/Fonts/Hiragino Sans GB.ttc'
sans='/System/Library/Fonts/Supplemental/Arial.ttf'
d.text((65,50),'epiya',fill='#f1f0e9',font=ImageFont.truetype(sans,52))
d.text((65,185),'智能，\n也有温度。',fill='#e9efdc',font=ImageFont.truetype(font,76),spacing=12)
d.text((68,465),'表达 · 记忆 · 判断',fill='#d7ff72',font=ImageFont.truetype(font,23))
d.text((68,560),'EPIYA / 杭州壹湃科技有限公司',fill='#a7ac9c',font=ImageFont.truetype(font,18))
im.save(R/'assets/share.png',optimize=True)
print('Original fiber sculpture / favicon / share image generated')
