"""Capture the real MovieShrinkPro window running in Windows CI."""
import ctypes
import time
from pathlib import Path
from PIL import ImageGrab

user32=ctypes.windll.user32
user32.SetProcessDPIAware()
title="MovieShrink Pro — DVD / USB / MP4"
hwnd=0
for _ in range(30):
    hwnd=user32.FindWindowW(None,title)
    if hwnd:break
    time.sleep(0.5)
if not hwnd:raise RuntimeError("Real MovieShrink Pro window not found")
user32.ShowWindow(hwnd,9)
user32.MoveWindow(hwnd,8,8,970,640,True)
user32.SetForegroundWindow(hwnd)
time.sleep(2)
class RECT(ctypes.Structure):
    _fields_=[("left",ctypes.c_long),("top",ctypes.c_long),
              ("right",ctypes.c_long),("bottom",ctypes.c_long)]
rect=RECT()
if not user32.GetWindowRect(hwnd,ctypes.byref(rect)):
    raise RuntimeError("Cannot obtain real application window bounds")
bounds=(rect.left,rect.top,rect.right,rect.bottom)
if bounds[2]<=bounds[0] or bounds[3]<=bounds[1]:
    raise RuntimeError(f"Invalid window bounds: {bounds}")
image=ImageGrab.grab(bbox=bounds,all_screens=True)
out=Path("MovieShrinkPro_Actual_Windows_Screenshot.png")
image.save(out)
print(f"Captured real application window: {out} ({image.size})")
