"""Assert that the ACTUAL Windows application screenshot visibly contains the colored action buttons."""
from PIL import Image
im=Image.open("MovieShrinkPro_Actual_Windows_Screenshot.png").convert("RGB")
w,h=im.size
assert w >= 900 and h >= 580, f"Wrong capture dimensions: {im.size}"
lower=im.crop((0,int(h*.55),w,h))
counts={"green":0,"red":0,"deep_blue":0}
for r,g,b in lower.getdata():
    if 30<r<170 and 80<g<245 and g>r*1.55 and g>b*1.15:
        counts["green"]+=1
    if r>130 and r>g*1.7 and r>b*1.55 and g<155:
        counts["red"]+=1
    if b>50 and b>r*1.3 and b>g*1.05 and r<130:
        counts["deep_blue"]+=1
assert counts["green"]>300, f"Green START button not visible: {counts}"
assert counts["red"]>300, f"Red STOP button not visible: {counts}"
print(f"ACTUAL screenshot verified ({w}x{h}): {counts}")
