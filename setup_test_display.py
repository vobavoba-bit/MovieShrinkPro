"""Best-effort request for a larger CI Windows desktop to inspect the actual application."""
import ctypes
from ctypes import wintypes

class POINTL(ctypes.Structure):
    _fields_=[("x",wintypes.LONG),("y",wintypes.LONG)]
class DEVMODEW(ctypes.Structure):
    _fields_=[
        ("dmDeviceName",ctypes.c_wchar*32),
        ("dmSpecVersion",wintypes.WORD),("dmDriverVersion",wintypes.WORD),
        ("dmSize",wintypes.WORD),("dmDriverExtra",wintypes.WORD),
        ("dmFields",wintypes.DWORD),("dmPosition",POINTL),
        ("dmDisplayOrientation",wintypes.DWORD),("dmDisplayFixedOutput",wintypes.DWORD),
        ("dmColor",wintypes.SHORT),("dmDuplex",wintypes.SHORT),
        ("dmYResolution",wintypes.SHORT),("dmTTOption",wintypes.SHORT),
        ("dmCollate",wintypes.SHORT),("dmFormName",ctypes.c_wchar*32),
        ("dmLogPixels",wintypes.WORD),("dmBitsPerPel",wintypes.DWORD),
        ("dmPelsWidth",wintypes.DWORD),("dmPelsHeight",wintypes.DWORD),
        ("dmDisplayFlags",wintypes.DWORD),("dmDisplayFrequency",wintypes.DWORD),
        ("dmICMMethod",wintypes.DWORD),("dmICMIntent",wintypes.DWORD),
        ("dmMediaType",wintypes.DWORD),("dmDitherType",wintypes.DWORD),
        ("dmReserved1",wintypes.DWORD),("dmReserved2",wintypes.DWORD),
        ("dmPanningWidth",wintypes.DWORD),("dmPanningHeight",wintypes.DWORD)]
u=ctypes.windll.user32
modes=[]
for idx in range(512):
    d=DEVMODEW();d.dmSize=ctypes.sizeof(d)
    if not u.EnumDisplaySettingsW(None,idx,ctypes.byref(d)):break
    if d.dmPelsWidth>=1366 and d.dmPelsHeight>=768:
        modes.append((d.dmPelsWidth,d.dmPelsHeight,idx))
if modes:
    candidate=min(modes,key=lambda x:abs(x[0]-1366)+abs(x[1]-768))
    mode=DEVMODEW();mode.dmSize=ctypes.sizeof(mode)
    u.EnumDisplaySettingsW(None,candidate[2],ctypes.byref(mode))
    rc=u.ChangeDisplaySettingsW(ctypes.byref(mode),0)
    print(f"Display request {candidate[:2]} returned {rc}")
else:
    print("No supported mode >=1366x768; keeping existing Windows runner screen")
