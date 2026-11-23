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
# Exercise the actual FFmpeg conversion and capture its progress before completion.
app.output.set(str(pathlib.Path("test_ui_output").resolve()))
app.start()
for _ in range(260):
    app.update()
    if app.pct.get() >= 5:
        break
    time.sleep(.08)
assert app.pct.get() > 0 or app.items[0]["pct"] > 0, f"Actual conversion did not advance: status={app.status.get()} item={app.items[0]}"
app.update_idletasks()
x=app.winfo_rootx();y=app.winfo_rooty()
w=app.winfo_width();h=app.winfo_height()
ImageGrab.grab(bbox=(max(0,x),max(0,y),max(0,x)+w,max(0,y)+h),
               all_screens=True).save("MovieShrinkPro_Real_Progress_Test.png")
print("Real transcoding progress captured:",round(app.pct.get(),1),"%")
app.stop()
for _ in range(80):
    app.update()
    if not (app.worker and app.worker.is_alive()):break
    time.sleep(.05)
app.disable_preview()
app.destroy()
