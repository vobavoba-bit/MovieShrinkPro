"""Embed a JPEG/PNG banner inside a PyInstaller one-file EXE without a sidecar.
PyInstaller CArchive cookie is updated so the bootloader still locates the archive.
"""
import sys,struct
from pathlib import Path
MAGIC=b"MEI\x0c\x0b\x0a\x0b\x0e"
FMT="!8sIIII64s"
SIZE=struct.calcsize(FMT)
MARKER=b"MSPREFBANNER\x00"
def embed(executable,image):
    exe=Path(executable);data=exe.read_bytes();img=Path(image).read_bytes()
    if not (1024<=len(img)<=250000):raise ValueError("banner image must be 1-250 KB")
    cookie=list(struct.unpack(FMT,data[-SIZE:]))
    if cookie[0]!=MAGIC:raise ValueError("Not a PyInstaller CArchive executable")
    payload=data[:-SIZE]
    i=payload.rfind(MARKER)
    if i>=0:
        j=i+len(MARKER)
        oldlen=struct.unpack(">I",payload[j:j+4])[0]
        if j+4+oldlen==len(payload):
            payload=payload[:i]
            cookie[1]-=len(MARKER)+4+oldlen
    overlay=MARKER+struct.pack(">I",len(img))+img
    cookie[1]+=len(overlay)
    exe.write_bytes(payload+overlay+struct.pack(FMT,*cookie))
    new=exe.read_bytes()
    assert new.rfind(MARKER)>0
    assert struct.unpack(FMT,new[-SIZE:])[0]==MAGIC
    print(f"Banner embedded in {exe}: {len(img)} bytes, CArchive updated")
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: embed_banner.py EXE BANNER")
    embed(sys.argv[1],sys.argv[2])
