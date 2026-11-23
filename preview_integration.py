"""Run the ACTUAL MovieShrink Pro preview against a generated test clip in Windows CI.
Screenshot is clearly labeled a TEST VIDEO; no mocked player frame is used.
"""
import pathlib,subprocess,time,tkinter as tk
from PIL import ImageGrab
from MovieShrinkPro import MovieShrink,binary
from tkinter import messagebox
clip=pathlib.Path("movie_UI_TEST_video.mp4").resolve()
ff=binary("ffmpeg.exe")
cmd=[ff,"-hide_banner","-loglevel","error","-y","-f","lavfi",
     "-i","testsrc2=s=640x360:r=15:d=9","-c:v","mpeg4","-q:v","4",str(clip)]
subprocess.run(cmd,check=True,timeout=45)
app=MovieShrink()
app.title("MovieShrink Pro — DVD / USB / MP4")
app.add([str(clip)])
app.tree.selection_set("0")
app._selected()
app.enable_preview()
for _ in range(180):
    app.update()
    if app.current_preview_frame is not None:
        break
    time.sleep(.10)
if app.current_preview_frame is None:
    app.disable_preview()
    app.destroy()
    raise AssertionError("Real FFmpeg playback produced no preview frames")
app.update_idletasks()
x=app.winfo_rootx();y=app.winfo_rooty()
w=app.winfo_width();h=app.winfo_height()
ImageGrab.grab(bbox=(max(0,x),max(0,y),max(0,x)+w,max(0,y)+h),
               all_screens=True).save("MovieShrinkPro_Real_Preview_Test.png")
print(f"Real FFmpeg source preview passed, screenshot saved {w}x{h}")
app.disable_preview()
app.destroy()
