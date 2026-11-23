"""Capture the genuine 1280x720 Windows app with GDI PrintWindow, no mocks."""
import ctypes,time
from ctypes import wintypes
from PIL import Image
from pathlib import Path
u=ctypes.windll.user32
g=ctypes.windll.gdi32
u.SetProcessDPIAware()
hwnd=0
for i in range(24):
    hwnd=u.FindWindowW(None,"MovieShrink Pro — DVD / USB / MP4")
    if hwnd:break
    time.sleep(.5)
if not hwnd:raise RuntimeError("Cannot locate the real window")
u.MoveWindow(hwnd,0,0,1280,720,True)
u.ShowWindow(hwnd,9)
time.sleep(2)
class RECT(ctypes.Structure):
    _fields_=[("left",wintypes.LONG),("top",wintypes.LONG),
              ("right",wintypes.LONG),("bottom",wintypes.LONG)]
rect=RECT()
u.GetWindowRect(hwnd,ctypes.byref(rect))
width=rect.right-rect.left;height=rect.bottom-rect.top
src=u.GetWindowDC(hwnd);mem=g.CreateCompatibleDC(src)
bitmap=g.CreateCompatibleBitmap(src,width,height)
g.SelectObject(mem,bitmap)
ok=u.PrintWindow(hwnd,mem,2)
if not ok:raise RuntimeError("PrintWindow did not render")
class BITMAPINFOHEADER(ctypes.Structure):
    _fields_=[("biSize",wintypes.DWORD),("biWidth",wintypes.LONG),
      ("biHeight",wintypes.LONG),("biPlanes",wintypes.WORD),
      ("biBitCount",wintypes.WORD),("biCompression",wintypes.DWORD),
      ("biSizeImage",wintypes.DWORD),("biXPelsPerMeter",wintypes.LONG),
      ("biYPelsPerMeter",wintypes.LONG),("biClrUsed",wintypes.DWORD),
      ("biClrImportant",wintypes.DWORD)]
class BITMAPINFO(ctypes.Structure):
    _fields_=[("bmiHeader",BITMAPINFOHEADER),("bmiColors",wintypes.DWORD*3)]
info=BITMAPINFO()
info.bmiHeader.biSize=ctypes.sizeof(BITMAPINFOHEADER)
info.bmiHeader.biWidth=width
info.bmiHeader.biHeight=-height
info.bmiHeader.biPlanes=1
info.bmiHeader.biBitCount=32
info.bmiHeader.biCompression=0
buffer=ctypes.create_string_buffer(width*height*4)
n=g.GetDIBits(mem,bitmap,0,height,buffer,ctypes.byref(info),0)
g.DeleteObject(bitmap);g.DeleteDC(mem);u.ReleaseDC(hwnd,src)
if n!=height:raise RuntimeError(f"GetDIBits returned {n} rows, need {height}")
im=Image.frombytes("RGB",(width,height),buffer.raw,"raw","BGRX")
out=Path("MovieShrinkPro_Real_Large_Window.png")
im.save(out)
print("Captured",str(out),im.size)
