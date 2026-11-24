"""MovieShrink Pro: free Windows 10 video batch converter (unencrypted sources only)."""
import os, sys, pathlib, subprocess, json, shutil, threading, queue, tempfile, time, base64, re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
P=pathlib.Path
EXT={".mp4",".mkv",".mov",".avi",".m4v",".mpg",".mpeg",".webm",".ts"}
def binary(name):
    root=P(getattr(sys,"_MEIPASS",P(__file__).parent))
    for p in (root/"bin"/name,root/name,P(sys.executable).parent/name):
        if p.exists():return str(p)
    return shutil.which(name)
def probe(path):
    p=subprocess.run([binary("ffprobe.exe"),"-v","error","-show_streams","-show_format","-of","json",str(path)],capture_output=True,text=True,encoding="utf-8",errors="replace",creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),timeout=60)
    if p.returncode:raise RuntimeError(p.stderr[-300:] or "Αποτυχία ανάγνωσης")
    j=json.loads(p.stdout);s=j.get("streams",[]);v=next((x for x in s if x.get("codec_type")=="video"),None)
    if not v:raise RuntimeError("Δεν βρέθηκε εικόνα.")
    a=next((x for x in s if x.get("codec_type")=="audio"),None)
    return float(j.get("format",{}).get("duration") or v.get("duration") or 0),int(v.get("width",0)),int(v.get("height",0)),a
def run(cmd,**kw):
    return subprocess.run(cmd,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),**kw)
def self_test():
    try:
        f=binary("ffmpeg.exe");p=binary("ffprobe.exe")
        if not f or not p:raise RuntimeError("FFmpeg/FFprobe missing")
        with tempfile.TemporaryDirectory() as d:
            out=P(d)/"t.mp4"
            x=run([f,"-v","error","-y","-f","lavfi","-i","color=c=blue:s=160x90:r=10","-t","1","-c:v","mpeg4",str(out)],capture_output=True,timeout=60)
            if x.returncode or probe(out)[1]!=160:raise RuntimeError("Conversion failed")
        return 0
    except Exception as e:
        (P(tempfile.gettempdir())/"MovieShrinkPro-selftest.txt").write_text(str(e),encoding="utf-8")
        return 1
def read_srt_cues(path):
    """Parse external subtitles for genuine live subtitle preview."""
    data=None
    for codec in ("utf-8-sig","utf-8","cp1253","cp1252"):
        try:
            data=P(path).read_text(encoding=codec)
            break
        except UnicodeError:continue
    if data is None:return []
    data=data.replace("\r\n","\n").replace("\r","\n")
    rx=re.compile(r"(\d\d:\d\d:\d\d[,.]\d{1,3})\s*-->\s*"
                  r"(\d\d:\d\d:\d\d[,.]\d{1,3})[^\n]*\n(.*?)(?=\n\s*\n|\Z)",re.S)
    def seconds(v):
        hh,mm,other=v.split(":")
        sec,frac=re.split(r"[,.]",other,1)
        return 3600*int(hh)+60*int(mm)+int(sec)+int(frac.ljust(3,"0")[:3])/1000
    return [(seconds(m.group(1)),seconds(m.group(2)),
             re.sub(r"<[^>]*>","",m.group(3).strip())) for m in rx.finditer(data)
            if m.group(3).strip()]

def style_srt_as_ass(source, destination, size_percent=100, position="Κάτω", delay_seconds=0.0):
    """Create an editable external ASS subtitle file with genuine style and timing.
    Uses no codecs or third-party deps; returns the number of cues written.
    """
    source=P(source);destination=P(destination)
    data=None
    for encoding in ("utf-8-sig","utf-8","cp1253","cp1252"):
        try:
            data=source.read_text(encoding=encoding)
            break
        except UnicodeError:
            continue
    if data is None:raise ValueError("Δεν είναι δυνατή η ανάγνωση SRT.")
    data=data.replace("\r\n","\n").replace("\r","\n")
    pattern=re.compile(r"(?:^|\n)\s*(?:\d+\s*\n)?"
        r"(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*"
        r"(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{1,3})[^\n]*\n"
        r"(?P<text>.*?)(?=\n\s*\n|\Z)",re.S)
    def time_ms(raw):
        h,m,rest=raw.split(":")
        sec,ms=re.split(r"[,.]",rest,1)
        return ((int(h)*60+int(m))*60+int(sec))*1000+int(ms.ljust(3,"0")[:3])
    def ass_time(ms):
        ms=max(0,round(ms))
        n=ms//10
        return f"{n//360000:01d}:{(n//6000)%60:02d}:{(n//100)%60:02d}.{n%100:02d}"
    font_size=max(12,min(68,round(28*float(size_percent)/100)))
    align=8 if position=="Πάνω" else 5 if position=="Κέντρο" else 2
    lines=["[Script Info]","Title: MovieShrink Pro SRT styling",
           "ScriptType: v4.00+","PlayResX: 1280","PlayResY: 720","WrapStyle: 0","",
           "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           f"Style: Default,Arial,{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,{align},30,30,28,1",
           "","[Events]","Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    count=0;delay=int(float(delay_seconds)*1000)
    for m in pattern.finditer(data):
        begin=max(0,time_ms(m.group("start"))+delay)
        end=max(begin+10,time_ms(m.group("end"))+delay)
        content=m.group("text").strip()
        if not content:continue
        content=content.replace("\\","\\\\").replace("{",r"\{").replace("}",r"\}")
        content=re.sub(r"<i>",r"{\\i1}",content,flags=re.I)
        content=re.sub(r"</i>",r"{\\i0}",content,flags=re.I)
        content=re.sub(r"<[^>]+>","",content)
        content=content.replace("\n",r"\N")
        lines.append(f"Dialogue: 0,{ass_time(begin)},{ass_time(end)},Default,,0,0,0,,{content}")
        count+=1
    if count==0:raise ValueError("Δεν εντοπίστηκαν έγκυροι χρόνοι υποτίτλων SRT.")
    destination.write_text("\n".join(lines)+"\n",encoding="utf-8-sig")
    return count

class MovieShrink(tk.Tk):
    def __init__(self):
        super().__init__();self.title("MovieShrink Pro — DVD / USB / MP4")
        screen_w=self.winfo_screenwidth();screen_h=self.winfo_screenheight()
        window_w=min(1480,max(950,screen_w-26))
        window_h=min(920,max(610,screen_h-64))
        self.geometry(f"{window_w}x{window_h}+12+12")
        self.minsize(950,610)
        self.items=[];self.events=queue.Queue();self.worker=None;self.process=None;self.stopflag=False
        self.quality=tk.StringVar(value="Ισορροπημένη");self.size=tk.StringVar(value="1080p")
        self.audio=tk.StringVar(value="AAC Stereo");self.format=tk.StringVar(value="MP4")
        self.output=tk.StringVar(value=str(P.home()/"Videos"/"MovieShrinkPro"))
        self.pct=tk.DoubleVar();self.allpct=tk.DoubleVar();self.status=tk.StringVar(value="Έτοιμο")
        self.current_percent=tk.StringVar(value="0%");self.overall_percent=tk.StringVar(value="0%")
        self.metrics=tk.StringVar(value="Ταχύτητα: — FPS | Χρόνος: —")
        self.source_progress_label=tk.StringVar(value="Αρχική ταινία: —")
        self.output_progress_label=tk.StringVar(value="Μετατροπή σε 1080p • Συνολική πρόοδος")
        self.preview_stop=threading.Event();self.preview_pause=threading.Event()
        self.preview_generation=0;self.preview_proc=None
        self.preview_enabled=False;self.preview_thread=None
        self.preview_seek=5.0;self.preview_duration=0.0
        self.preview_position=tk.DoubleVar(value=0)
        self.preview_clock=tk.StringVar(value="00:00 / --:--")
        self.preview_seek_drag=False
        self.external_subtitles={}
        self.smart_guard_enabled=tk.BooleanVar(value=True)
        self.subtitle_size=tk.StringVar(value="Μεσαίο (100%)")
        self.subtitle_position=tk.StringVar(value="Κάτω")
        self.subtitle_delay=tk.StringVar(value="0.0")
        self.current_preview_frame=None
        self.preview_subtitle_cues=[]
        self.ui()
        if hasattr(self,"brand_image"):self.iconphoto(True,self.brand_image)
        self.after(100,self.poll)
        for v in (self.quality,self.size,self.format,self.audio):v.trace_add("write",self.update_quality_hint)
        for v in (self.pct,self.allpct):v.trace_add("write",self.update_progress_labels)
        self.size.trace_add("write",self.update_progress_target)
        self.update_quality_hint();self.update_progress_target();self.update_progress_labels()
        self.protocol("WM_DELETE_WINDOW",self.close_app)
        self.bind("<Configure>",self.auto_layout)
    def glossy_button(self,parent,label,command,colors,width=218,height=48):
        """Large crisp beveled action control with true gradient and hover/disabled skins."""
        from PIL import Image,ImageDraw,ImageFont,ImageTk
        top_hex,bottom_hex,outline_hex=colors
        def rgb(c):return tuple(int(c[i:i+2],16) for i in (1,3,5))
        def blend(a,b,t):return tuple(round(a[k]*(1-t)+b[k]*t) for k in range(3))
        def art(mode="normal"):
            k=3;w=width*k;h=height*k
            im=Image.new("RGBA",(w,h),(0,0,0,0))
            d=ImageDraw.Draw(im)
            # Shadow, inset border and a polished two-stop face.
            d.rounded_rectangle((4,7,w-5,h-3),radius=28,fill=(5,22,37,105))
            t=rgb(top_hex);bottom=rgb(bottom_hex)
            if mode=="hover":
                t=blend(t,(255,255,255),.22);bottom=blend(bottom,(255,255,255),.15)
            if mode=="disabled":
                t=blend(t,(195,206,215),.66);bottom=blend(bottom,(155,170,185),.66)
            border=rgb(outline_hex)
            d.rounded_rectangle((3,3,w-5,h-9),radius=26,fill=border+(255,))
            fill=Image.new("RGB",(w,h))
            fd=ImageDraw.Draw(fill)
            for y in range(h):
                fraction=y/max(1,h-1)
                frac=fraction/.48*.55 if fraction<.48 else .55+((fraction-.48)/.52)*.45
                fd.line((0,y,w,y),fill=blend(t,bottom,frac))
            mask=Image.new("L",(w,h),0)
            ImageDraw.Draw(mask).rounded_rectangle((8,8,w-10,h-14),radius=21,fill=255)
            im.paste(fill,(0,0),mask)
            d=ImageDraw.Draw(im)
            d.rounded_rectangle((9,9,w-11,h//2),radius=18,
                                outline=(241,253,255,130),width=4)
            d.line((30,h-19,w-32,h-19),fill=(0,0,0,75),width=3)
            iconx=51;icony=h//2-3
            if label=="ΕΝΑΡΞΗ":
                d.polygon([(iconx-18,icony-28),(iconx-18,icony+29),
                           (iconx+29,icony)],fill=(255,255,255,255))
            else:
                d.rounded_rectangle((iconx-21,icony-23,iconx+23,icony+22),
                                    radius=4,fill=(255,255,255,255))
            try:
                font=ImageFont.truetype(os.path.join(os.environ.get("WINDIR","C:\\Windows"),
                                                    "Fonts","segoeuib.ttf"),60)
            except OSError:
                font=ImageFont.load_default()
            bbox=d.textbbox((0,0),label,font=font)
            tw=bbox[2]-bbox[0];th=bbox[3]-bbox[1]
            cx=(w+105-tw)/2
            cy=(h-th)/2-bbox[1]-5
            d.text((cx,cy+4),label,font=font,fill=(1,13,32,130))
            d.text((cx,cy),label,font=font,fill="white",
                   stroke_width=1,stroke_fill="#f3ffff")
            return ImageTk.PhotoImage(im.resize((width,height),Image.Resampling.LANCZOS))
        normal,hover,disabled=art(),art("hover"),art("disabled")
        if not hasattr(self,"_styled_button_images"):self._styled_button_images=[]
        self._styled_button_images.extend((normal,hover,disabled))
        button=tk.Button(parent,image=normal,command=command,relief="flat",bd=0,
                         bg="#d9eafd",activebackground="#d9eafd",
                         highlightthickness=0,cursor="hand2")
        button._action_images=(normal,hover,disabled)
        def sync_skin(_=None):
            button.configure(image=disabled if str(button.cget("state"))=="disabled"
                             else hover if getattr(button,"_is_hovered",False) else normal)
        button._update_skin=sync_skin
        def enter(_):
            button._is_hovered=True
            sync_skin()
        def leave(_):
            button._is_hovered=False
            sync_skin()
        button.bind("<Enter>",enter);button.bind("<Leave>",leave)
        return button
    def cinema_progressbar(self,parent,variable,kind):
        """AA rounded progress rails with chrome highlights, green/blue liquid fill."""
        from PIL import Image,ImageDraw,ImageTk
        rail=tk.Canvas(parent,bg="#f9fcff",height=23,highlightthickness=0,
                       borderwidth=0,relief="flat")
        rail._photo=None
        rail._last_render=None
        top,bottom,border=(("#72ee7c","#078332","#126a30") if kind=="green"
                           else ("#69d7ff","#076ab8","#0c5b9f"))
        def rgb(hexstr):return tuple(bytes.fromhex(hexstr[1:]))
        def interpolate(a,b,t):return tuple(int(a[i]*(1-t)+b[i]*t) for i in range(3))
        def paint(*_):
            width=max(10,rail.winfo_width())
            value=max(0,min(100,float(variable.get())))
            signature=(width,round(value,2))
            if signature==rail._last_render:return
            rail._last_render=signature
            scale=2;w=width*scale;h=44
            im=Image.new("RGBA",(w,h),(0,0,0,0))
            d=ImageDraw.Draw(im)
            d.rounded_rectangle((1,3,w-3,h-4),radius=13,
                                fill="#b8cadd",outline="#5c7f9e",width=3)
            d.rounded_rectangle((6,8,w-8,h-9),radius=10,fill="#eaf4fc")
            if value>0:
                fillwidth=max(5,int((w-15)*value/100))
                xend=min(w-8,7+fillwidth)
                mask=Image.new("L",(w,h),0)
                ImageDraw.Draw(mask).rounded_rectangle((7,9,xend,h-10),radius=9,fill=255)
                ink=Image.new("RGBA",(w,h),(0,0,0,0))
                gd=ImageDraw.Draw(ink)
                for yy in range(9,h-9):
                    t=(yy-9)/(h-18)
                    gd.line((7,yy,xend,yy),fill=interpolate(rgb(top),rgb(bottom),t)+(255,))
                im.paste(ink,(0,0),mask)
                d=ImageDraw.Draw(im)
                d.line((13,12,max(14,xend-8),12),fill=(249,255,255,145),width=3)
                d.line((13,h-12,max(14,xend-8),h-12),fill=rgb(border)+(200,),width=2)
            rail._photo=ImageTk.PhotoImage(im.resize((width,22),Image.Resampling.LANCZOS))
            rail.delete("all")
            rail.create_image(0,0,anchor="nw",image=rail._photo)
        rail.bind("<Configure>",paint)
        variable.trace_add("write",paint)
        rail._paint=paint
        return rail
    def metallic_toolbar_button(self,parent,caption,action,symbol,width=204):
        """Antialiased silver-blue ribbon control (not native flat ttk)."""
        from PIL import Image,ImageDraw,ImageFont,ImageTk
        h=42;W=width*2;H=h*2
        def render(hover=False):
            img=Image.new("RGBA",(W,H),(0,0,0,0))
            d=ImageDraw.Draw(img)
            rect=(3,3,W-4,H-4)
            d.rounded_rectangle(rect,radius=12,fill="#afc7e1",outline="#4d82b6",width=3)
            for y in range(7,H-7):
                t=(y-7)/(H-14)
                start=(247,252,255) if not hover else (230,249,255)
                end=(172,200,228) if not hover else (137,192,238)
                c=tuple(round(start[k]*(1-t)+end[k]*t) for k in range(3))
                d.line((8,y,W-9,y),fill=c+(255,),width=1)
            d.rounded_rectangle((5,5,W-6,H-6),radius=10,outline="#74a8d4",width=2)
            d.line((14,13,W-16,13),fill="#ffffff",width=3)
            # Draw icons ourselves; font support is not needed for these symbols.
            iconx=33;icony=H//2
            if symbol=="disc":
                d.ellipse((iconx-20,icony-20,iconx+20,icony+20),fill="#3c9fe1",outline="#174e91",width=4)
                d.ellipse((iconx-7,icony-7,iconx+7,icony+7),fill="#e8f4fb",outline="#155b98",width=2)
            elif symbol=="folder":
                d.rounded_rectangle((iconx-21,icony-13,iconx+24,icony+17),radius=4,fill="#ffbd22",outline="#a97506",width=3)
                d.rectangle((iconx-17,icony-20,iconx+5,icony-12),fill="#ffd75c")
            elif symbol=="usb":
                d.rounded_rectangle((iconx-9,icony-22,iconx+9,icony+21),radius=4,fill="#4d94cc",outline="#1d4b7b",width=3)
                d.rectangle((iconx-5,icony-26,iconx+5,icony-18),fill="#d8eafd")
            elif symbol=="remove":
                d.line((iconx-16,icony-15,iconx+16,icony+15),fill="#c72431",width=9)
                d.line((iconx+16,icony-15,iconx-16,icony+15),fill="#c72431",width=9)
            elif symbol=="settings":
                d.ellipse((iconx-19,icony-19,iconx+19,icony+19),fill="#22679a",outline="#063d76",width=4)
                d.ellipse((iconx-7,icony-7,iconx+7,icony+7),fill="#d6eeff")
            elif symbol=="info":
                d.ellipse((iconx-20,icony-20,iconx+20,icony+20),fill="#2d8ece",outline="#0c5184",width=4)
                d.ellipse((iconx-3,icony-12,iconx+3,icony-6),fill="white")
                d.rounded_rectangle((iconx-3,icony-2,iconx+3,icony+14),radius=2,fill="white")
            try:
                f=ImageFont.truetype(os.path.join(os.environ.get("WINDIR","C:\\Windows"),"Fonts","segoeuib.ttf"),30)
            except OSError:f=ImageFont.load_default()
            d.text((66,(H-30)/2),caption,font=f,fill="#173c61")
            return ImageTk.PhotoImage(img.resize((width,h),Image.Resampling.LANCZOS))
        normal=render();hot=render(True)
        if not hasattr(self,"_styled_button_images"):self._styled_button_images=[]
        self._styled_button_images.extend((normal,hot))
        button=tk.Button(parent,image=normal,command=action,bg="#c7daee",
                         activebackground="#c7daee",relief="flat",
                         bd=0,highlightthickness=0,cursor="hand2")
        button.bind("<Enter>",lambda e:button.configure(image=hot))
        button.bind("<Leave>",lambda e:button.configure(image=normal))
        return button
    def update_progress_labels(self,*_):
        self.current_percent.set(f"{self.pct.get():.0f}%")
        self.overall_percent.set(f"{self.allpct.get():.1f}%".replace(".0%","%"))
    def auto_layout(self,event):
        if event.widget is not self:return
        if hasattr(self,"preview_box"):
            desired=max(98,min(263,event.height-537))
            if self.preview_box.cget("height")!=desired:
                self.preview_box.configure(height=desired)
    def ui(self):
        """Functional DVD Shrink-inspired skin, responsive down to 970x640."""
        from PIL import Image, ImageDraw, ImageFont, ImageTk
        dark="#061b3b";navy="#0a427a";paper="#eaf3fe";white="#f9fcff";ink="#122f50"
        self.configure(bg="#bdcfe4")
        style=ttk.Style(self);style.theme_use("clam")
        style.configure("TFrame",background=paper)
        style.configure("TLabel",background=paper,foreground=ink,font=("Segoe UI",9))
        style.configure("TButton",font=("Segoe UI",9,"bold"),padding=(7,5),
                        background="#d2e7fc",foreground="#123f6e",bordercolor="#7eabd1")
        style.map("TButton",background=[("active","#a9d6fc")])
        style.configure("Treeview",font=("Segoe UI",10),rowheight=28,
                        background="#f9fcff",fieldbackground="#f9fcff",foreground=ink)
        style.configure("Treeview.Heading",font=("Segoe UI",9,"bold"),background="#c0d8f3",
                        foreground=navy,padding=6)
        style.map("Treeview",background=[("selected","#9bcffa")],foreground=[("selected","#103052")])
        style.configure("TRadiobutton",font=("Segoe UI",9),background=paper,foreground=ink,padding=(0,1))
        style.map("TRadiobutton",background=[("active","#d5eafd")])
        style.configure("TCheckbutton",font=("Segoe UI",9),background=paper,foreground=ink)
        style.configure("TCombobox",font=("Segoe UI",9))
        for style_name,background,foreground in (
                ("PreviewPlay.TButton","#bdf0d2","#0b6a30"),
                ("PreviewPause.TButton","#cfe6fc","#0c4c85"),
                ("PreviewStop.TButton","#ffd8db","#9d1724"),
                ("PreviewFrame.TButton","#dfecfa","#27527d")):
            style.configure(style_name,font=("Segoe UI",9,"bold"),padding=(5,5),
                            background=background,foreground=foreground,
                            bordercolor="#7a9db9",relief="raised")
            style.map(style_name,background=[("active","#a8dcf8")])

        style.configure("Green.Horizontal.TProgressbar",background="#19bd42",troughcolor="#b3cce6",thickness=18)
        style.configure("Blue.Horizontal.TProgressbar",background="#1595e1",troughcolor="#b3cce6",thickness=18)
        def load_font(size,bold=False):
            fn="segoeuib.ttf" if bold else "segoeui.ttf"
            path=os.path.join(os.environ.get("WINDIR","C:\\Windows"),"Fonts",fn)
            try:return ImageFont.truetype(path,size)
            except OSError:return ImageFont.load_default()
        # One fully rendered blue/cyan cinema banner instead of overlapping Tk labels.
        # All pixels, labels and symbols belong to the actual interactive application.
        from PIL import ImageFilter
        import math
        banner_width=min(1480,max(950,self.winfo_screenwidth()))
        W,H=banner_width*2,236
        banner=Image.new("RGB",(W,H))
        pix=ImageDraw.Draw(banner)
        for y in range(H):
            t=y/(H-1)
            color=(4+round(3*t),13+round(22*t),37+round(52*t))
            pix.line((0,y,W,y),fill=color)
        # Blue diagonal light and the curved electric wave of the reference.
        glow=Image.new("RGBA",(W,H),(0,0,0,0))
        gd=ImageDraw.Draw(glow)
        for k in range(22,0,-1):
            alpha=max(5,round(85*(1-k/24)))
            pts=[]
            for x in range(W):
                y=192-32*math.sin(2*math.pi*x/W*1.55)+14*math.sin(2*math.pi*x/W*.72)+k/3
                pts.append((x,int(y)))
            gd.line(pts,fill=(2,148,255,alpha),width=max(2,k))
        for x in range(0,W,2):
            y=int(192-32*math.sin(2*math.pi*x/W*1.55)+14*math.sin(2*math.pi*x/W*.72))
            gd.line((x,y-3,x,y+3),fill=(111,223,255,190),width=2)
        gd.polygon([(int(W*.77),0),(int(W*.83),0),(int(W*.70),H),(int(W*.67),H)],
                   fill=(0,94,219,75))
        banner=Image.alpha_composite(banner.convert("RGBA"),glow.filter(ImageFilter.GaussianBlur(3)))
        bd=ImageDraw.Draw(banner)
        bd.line((0,H-5,W,H-5),fill="#28b9ff",width=4)
        bd.line((0,1,W,1),fill="#5daddd",width=2)
        try:
            root=P(getattr(sys,"_MEIPASS",P(__file__).resolve().parent))
            logo=Image.open(root/"assets"/"movieshrink_logo.jpg").convert("RGBA")
            # Crop just the film-reel / disc / MP4 artwork to avoid duplicate text in the header.
            # Draw sharp, resolution-independent reel/DVD/MP4 insignia.
            art=Image.new("RGBA",(382,202),(0,0,0,0))
            dr=ImageDraw.Draw(art)
            dr.ellipse((0,132,350,193),outline="#eeb53b",width=6)
            dr.ellipse((12,10,205,198),fill="#273854",outline="#d9f5ff",width=8)
            dr.ellipse((31,29,186,178),fill="#abb9cc",outline="#f6fcff",width=5)
            for cx,cy in ((104,56),(156,105),(103,150),(55,104)):
                dr.ellipse((cx-23,cy-23,cx+23,cy+23),fill="#07162b",outline="#69839c",width=4)
            dr.ellipse((94,76,247,195),fill="#9ec5e9",outline="#ffffff",width=6)
            dr.arc((96,77,245,194),45,185,fill="#7ae1ff",width=13)
            dr.arc((99,81,241,190),195,335,fill="#ffe49b",width=10)
            dr.ellipse((164,125,199,159),fill="#112b4a",outline="#ebfcff",width=5)
            dr.polygon([(221,102),(276,102),(276,85),(311,121),(279,156),(279,141),(221,141)],fill="#00c5fa",outline="#d1faff")
            dr.rounded_rectangle((277,36,375,175),radius=12,fill="#07366e",outline="#32d4ff",width=5)
            dr.polygon([(281,37),(371,27),(376,61),(290,71)],fill="#ffffff")
            for n in range(3):
                px=290+n*26
                dr.polygon([(px,37),(px+11,34),(px+25,65),(px+13,67)],fill="#081d37")
            dr.polygon([(310,86),(310,128),(352,107)],fill="white")
            art=art.resize((438,212),Image.Resampling.LANCZOS)
            banner.alpha_composite(art,(4,7))
            self.brand_image=ImageTk.PhotoImage(logo.resize((64,64),Image.Resampling.LANCZOS))
        except Exception:
            bd.ellipse((22,20,190,188),fill="#0e5b9c",outline="#68cbff",width=6)
        def font(sz,bold=True,italic=False):
            face="segoeuiz.ttf" if bold and italic else ("segoeuib.ttf" if bold else "segoeui.ttf")
            try:return ImageFont.truetype(os.path.join(os.environ.get("WINDIR","C:\\Windows"),"Fonts",face),sz)
            except OSError:return ImageFont.load_default()
        titlefont=font(103,True,True)
        smallfont=font(27,True)
        bd=ImageDraw.Draw(banner)
        bd.text((457,25),"MovieShrink",font=titlefont,fill="#020d21",stroke_width=5,stroke_fill="#05132c")
        bd.text((453,20),"MovieShrink",font=titlefont,fill="#ffffff",stroke_width=1,stroke_fill="#afdfff")
        title_size=bd.textbbox((0,0),"MovieShrink",font=titlefont)
        wordx=453+title_size[2]-title_size[0]+10
        bd.text((wordx+4,26),"Pro",font=titlefont,fill="#06101f",stroke_width=5,stroke_fill="#05132c")
        bd.text((wordx,21),"Pro",font=titlefont,fill="#ffca44",stroke_width=1,stroke_fill="#ffe99c")
        bd.text((468,144),"DVD / USB / MP4   •   Full HD 1080p & 4K",
                font=smallfont,fill="#c5e8ff")
        # Right-hand badges shrink to compact marks on smaller laptop screens.
        badges=(("DVD",95),("USB",95),("MP4",100),("1080p",132),("4K",79))
        total=sum(width for _,width in badges)+12*(len(badges)-1)
        rx=W-total-23
        badgefont=font(27)
        for label,bw in badges:
            is_gold=label in ("1080p","4K")
            bd.rounded_rectangle((rx,62,rx+bw,147),radius=12,
                fill="#0e315d",outline="#ffcb4b" if is_gold else "#6db8f3",width=3)
            bbox=bd.textbbox((0,0),label,font=badgefont)
            tx=rx+(bw-(bbox[2]-bbox[0]))/2
            bd.text((tx,83),label,font=badgefont,fill="#ffd75c" if is_gold else "#ffffff")
            rx+=bw+12
        # Optional embedded reference banner: kept *inside* the single-file EXE.
        # The bootloader is independently tested with this archive extension.
        if getattr(sys,"frozen",False):
            try:
                import struct,io
                marker=b"MSPREFBANNER\x00"
                exe_path=P(sys.executable)
                with exe_path.open("rb") as stream:
                    stream.seek(max(0,exe_path.stat().st_size-300000))
                    tail=stream.read()
                at=tail.rfind(marker)
                if at>=0:
                    at+=len(marker)
                    length=struct.unpack(">I",tail[at:at+4])[0]
                    if 1024<=length<=250000:
                        raw=tail[at+4:at+4+length]
                        if len(raw)==length:
                            original=Image.open(io.BytesIO(raw)).convert("RGB")
                            banner=original.resize((W,H),Image.Resampling.LANCZOS)
            except Exception:
                pass
        self.header_img=ImageTk.PhotoImage(banner.convert("RGB").resize((banner_width,120),Image.Resampling.LANCZOS))
        head=tk.Frame(self,bg="#071a35",height=120)
        head.pack(side="top",fill="x");head.pack_propagate(False)
        tk.Label(head,image=self.header_img,bg="#071a35",bd=0,anchor="nw").pack(fill="both",expand=True)
        bar=tk.Frame(self,bg="#c7daee",height=49,highlightbackground="#79a5c9",highlightthickness=1)
        bar.pack(side="top",fill="x");bar.pack_propagate(False)
        available=self.winfo_screenwidth()
        roomy=available>=1200
        specs=(("Προσθήκη DVD" if roomy else "DVD",self.adddvd,"disc"),
               ("Προσθήκη φακέλου" if roomy else "Φάκελος",self.addfolder,"folder"),
               ("Προσθήκη USB / MP4" if roomy else "USB / MP4",self.addfiles,"usb"),
               ("Αφαίρεση",self.remove,"remove"),
               ("Ρυθμίσεις",self.open_settings,"settings"),
               ("Πληροφορίες",self.show_about,"info"))
        width=min(210,max(128,(available-76)//6))
        for cap,act,icon_id in specs:
            self.metallic_toolbar_button(bar,cap,act,icon_id,width=width).pack(
                side="left",padx=(5,0),pady=4)
        # Bottom is packed BEFORE the growing center: always remains visible.
        bottom=tk.Frame(self,bg=white,highlightbackground="#5987b9",highlightthickness=2)
        bottom.pack(side="bottom",fill="x",padx=8,pady=(2,3))
        tk.Label(bottom,text="▥   ΠΡΟΟΔΟΣ ΜΕΤΑΤΡΟΠΗΣ",bg="#0c477d",fg="white",
                 font=("Segoe UI",11,"bold"),anchor="w",padx=11,pady=3).pack(fill="x")
        inner=tk.Frame(bottom,bg=white);inner.pack(fill="x",padx=10,pady=(1,0))
        # Single pair of main actions: vertical, right-aligned, with no duplicates.
        controls=tk.Frame(inner,bg="#d9eafd",highlightbackground="#638cb7",
                          highlightthickness=2,padx=7,pady=4)
        controls.pack(side="right",padx=(8,0),pady=(0,1))
        self.action_panel=controls
        self.btn=self.glossy_button(controls,"ΕΝΑΡΞΗ",self.start,
                                    ("#62eb77","#08772e","#075322"),width=215,height=49)
        self.btn.pack(side="top",pady=(0,3),anchor="center")
        self.stop_btn=self.glossy_button(controls,"ΔΙΑΚΟΠΗ",self.stop,
                                         ("#ff8888","#b00920","#790719"),width=215,height=49)
        self.stop_btn.pack(side="top",anchor="center")
        bframe=tk.Frame(inner,bg=white);bframe.pack(side="left",fill="both",expand=True)
        for var,style_name,percentage,percentage_text in (
              (self.source_progress_label,"Green.Horizontal.TProgressbar",self.pct,self.current_percent),
              (self.output_progress_label,"Blue.Horizontal.TProgressbar",self.allpct,self.overall_percent)):
            tk.Label(bframe,textvariable=var,bg=white,fg=navy,
                     font=("Segoe UI",10,"bold"),anchor="w").pack(fill="x",pady=(0,1))
            barrow=tk.Frame(bframe,bg=white);barrow.pack(fill="x",pady=(0,3))
            tk.Label(barrow,textvariable=percentage_text,bg=white,fg="#173453",
                     font=("Segoe UI",12,"bold"),width=7,anchor="e").pack(side="right",padx=(8,0))
            self.cinema_progressbar(barrow,percentage,
                                    "green" if percentage is self.pct else "blue").pack(
                                        side="left",fill="x",expand=True,pady=3)
        foot=tk.Frame(bottom,bg=white);foot.pack(fill="x",padx=10,pady=(0,1))
        tk.Label(foot,textvariable=self.status,bg=white,fg="#23547e",
                 font=("Segoe UI",9,"bold"),anchor="w").pack(side="left")
        tk.Label(foot,textvariable=self.metrics,bg=white,fg="#23547e",
                 font=("Segoe UI",9,"bold"),anchor="e").pack(side="right")
        # Three true interactive panels, preserving functionality.
        main=tk.Frame(self,bg="#bfcfe0")
        main.pack(side="top",fill="both",expand=True,padx=5,pady=(5,3))
        for col,wt,minsize in ((0,33,280),(1,34,290),(2,33,290)):
            main.grid_columnconfigure(col,weight=wt,minsize=minsize)
        main.grid_rowconfigure(0,weight=1)
        def panel(index,title,icon_kind):
            out=tk.Frame(main,bg=paper,highlightbackground="#397da9",highlightthickness=2)
            out.grid(row=0,column=index,sticky="nsew",padx=3)
            # Section header is a single image; text is baked into the gloss,
            # so no overlapping solid-color labels break the visual gradient.
            hdr=tk.Label(out,bg="#0b467f",bd=0,height=32)
            hdr.pack(side="top",fill="x")
            def redraw(e=None):
                width=max(270,hdr.winfo_width())
                sig=(width,title)
                if getattr(hdr,"_sig",None)==sig:return
                hdr._sig=sig
                from PIL import Image,ImageDraw,ImageFont,ImageTk
                scale=2;w=width*scale;h=66
                im=Image.new("RGB",(w,h));draw=ImageDraw.Draw(im)
                for y in range(h):
                    f=y/max(1,h-1)
                    if f<.35:
                        top=(34,113,190);bot=(16,78,139)
                        t=f/.35
                    else:
                        top=(16,78,139);bot=(4,48,100)
                        t=(f-.35)/.65
                    c=tuple(round(top[i]*(1-t)+bot[i]*t) for i in range(3))
                    draw.line((0,y,w,y),fill=c)
                draw.line((2,2,w-3,2),fill="#d4efff",width=3)
                draw.line((2,h-3,w-3,h-3),fill="#002f68",width=3)
                # Compact white panel pictograms.
                draw.rounded_rectangle((17,17,52,49),radius=4,
                                       outline="#eaf9ff",width=4)
                if icon_kind=="queue":
                    for yy in (23,33,43):
                        draw.line((26,yy,45,yy),fill="#effaff",width=3)
                elif icon_kind=="preview":
                    draw.polygon([(28,24),(28,43),(44,34)],fill="#eafaff")
                else:
                    draw.ellipse((26,25,43,42),outline="#eafaff",width=4)
                    draw.ellipse((32,31,37,36),fill="#eafaff")
                try:
                    titlefont=ImageFont.truetype(
                        os.path.join(os.environ.get("WINDIR","C:\\Windows"),
                                     "Fonts","segoeuib.ttf"),27)
                except OSError:titlefont=ImageFont.load_default()
                draw.text((67,14),title,font=titlefont,fill="white",
                          stroke_width=1,stroke_fill="#0b3660")
                hdr._art=ImageTk.PhotoImage(im.resize((width,33),Image.Resampling.LANCZOS))
                hdr.configure(image=hdr._art)
            hdr.bind("<Configure>",redraw)
            out._header=hdr
            return out
        left=panel(0,"Ουρά επεξεργασίας","queue")
        center=panel(1,"Ζωντανή προεπισκόπηση","preview")
        right=panel(2,"Ρυθμίσεις εξόδου","settings")
        # Queue includes duration and source dimensions, populated asynchronously.
        lst=tk.Frame(left,bg=paper);lst.pack(fill="both",expand=True,padx=3,pady=(3,0))
        cols=("checked","file","duration","resolution","pct","state")
        self.tree=ttk.Treeview(lst,columns=cols,show="headings",selectmode="extended",height=8)
        for key,label,w in (("checked","✓",30),("file","Όνομα αρχείου",155),("duration","Διάρκεια",65),
                            ("resolution","Πηγή",75),("pct","%",42),("state","Κατάσταση",92)):
            self.tree.heading(key,text=label)
            self.tree.column(key,width=w,minwidth=30,stretch=(key=="file"))
        yscroll=ttk.Scrollbar(lst,orient="vertical",command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side="right",fill="y")
        self.tree.pack(side="left",fill="both",expand=True)
        self.empty_queue_hint=tk.Label(lst,text="🎬\n\nΠροσθήκη ταινιών\nMP4 • MKV • AVI\n\nΕπίλεξε ταινίες ή φάκελο από τα επάνω κουμπιά",
                     font=("Segoe UI",10),fg="#557899",bg="#f7fbff",justify="center")
        self.empty_queue_hint.place(relx=.5,rely=.5,anchor="center")
        self.tree.tag_configure("even",background="#f7fbff")
        self.tree.tag_configure("odd",background="#dfeeff")
        self.tree.tag_configure("active",background="#b6deff",foreground="#07542a",font=("Segoe UI",9,"bold"))
        self.tree.tag_configure("completed",background="#d9f6e0",foreground="#0f5630")
        self.tree.tag_configure("error",background="#ffe1e0",foreground="#8e1d1d")
        self.tree.bind("<<TreeviewSelect>>",self._selected)
        self.tree.bind("<Button-1>",self.toggle_queue_checkbox)
        self.queue_summary=tk.StringVar(value="0 ταινίες στην ουρά")
        tk.Label(left,textvariable=self.queue_summary,bg="#cfe1f3",fg=navy,
                 font=("Segoe UI",9,"bold"),anchor="w",padx=7,pady=4).pack(side="bottom",fill="x")
        # Center preview + explicit enable/pause/off; subtitle copy is a real setting.
        preview_box=tk.Frame(center,bg="#071525",height=220)
        self.preview_box=preview_box
        preview_box.pack(fill="x",padx=5,pady=(4,1));preview_box.pack_propagate(False)
        self.image=tk.Label(preview_box,text="▶\nΠροεπισκόπηση απενεργοποιημένη",
                            bg="#071525",fg="#bcd9f2",font=("Segoe UI",10))
        self.image.pack(fill="both",expand=True,padx=3,pady=3)
        self.preview_subtitle_overlay=tk.Label(preview_box,text="",bg="#071525",fg="white",
                                             font=("Segoe UI",11,"bold"),justify="center")
        self.preview_subtitle_overlay.place(relx=.5,rely=.88,anchor="center")
        transport=tk.Frame(center,bg="#112d48",height=33)
        transport.pack(fill="x",padx=5,pady=(0,2))
        tk.Label(transport,textvariable=self.preview_clock,bg="#112d48",fg="#e2f2ff",
                 font=("Segoe UI",8,"bold")).pack(side="left",padx=(6,3))
        self.preview_slider=ttk.Scale(transport,from_=0,to=100,
                                       variable=self.preview_position,orient="horizontal")
        self.preview_slider.pack(side="left",fill="x",expand=True,padx=(3,6))
        self.preview_slider.bind("<ButtonPress-1>",self.preview_seek_begin)
        self.preview_slider.bind("<ButtonRelease-1>",self.preview_seek_end)
        tk.Label(transport,text="🔇",bg="#112d48",fg="#e2f2ff",
                 font=("Segoe UI",10)).pack(side="right",padx=5)
        pc=tk.Frame(center,bg=paper);pc.pack(fill="x",padx=4,pady=(1,1))
        self.preview_button=ttk.Button(pc,text="▶ Παίξε",command=self.enable_preview,style="PreviewPlay.TButton")
        self.preview_button.pack(side="left",padx=(0,2))
        self.preview_pause_button=ttk.Button(pc,text="⏸ Παύση",command=self.pause_preview,state="disabled",style="PreviewPause.TButton")
        self.preview_pause_button.pack(side="left",padx=(0,2))
        self.preview_off_button=ttk.Button(pc,text="■ Κλείσιμο",command=self.disable_preview,state="disabled",style="PreviewStop.TButton")
        self.preview_off_button.pack(side="left",padx=(0,2))
        self.preview_capture_button=ttk.Button(pc,text="▣",width=3,command=self.save_preview_frame,state="disabled",style="PreviewFrame.TButton")
        self.preview_capture_button.pack(side="left")
        self.preview_state=tk.StringVar(value="Κλειστή • εξοικονόμηση CPU")
        tk.Label(center,textvariable=self.preview_state,bg=paper,fg="#406b94",
                 font=("Segoe UI",9,"bold"),anchor="w",padx=7).pack(fill="x")
        self.current_detail=tk.StringVar(value="Επίλεξε ταινία από την ουρά")
        tk.Label(center,textvariable=self.current_detail,bg=paper,fg=navy,
                 font=("Segoe UI",9,"bold"),anchor="w",wraplength=295,
                 justify="left",padx=7,pady=3).pack(fill="x")
        subs=tk.Frame(center,bg="#d3e7fa",highlightbackground="#8eb9dd",highlightthickness=1)
        subs.pack(fill="x",padx=5,pady=(2,3))
        tk.Label(subs,text="Aa   Εξωτερικοί υπότιτλοι SRT / ASS",bg="#b6d4f1",fg=navy,
                 font=("Segoe UI",10,"bold"),anchor="w",padx=7,pady=4).pack(fill="x")
        self.subtitle_info=tk.StringVar(value="Αυτόματη ανίχνευση SRT / ASS")
        tk.Label(subs,textvariable=self.subtitle_info,bg="#d3e7fa",fg="#1e507e",
                 font=("Segoe UI",9),anchor="w",wraplength=300,padx=7,pady=3).pack(fill="x")
        self.copy_subtitles=tk.BooleanVar(value=True)
        subrow=tk.Frame(subs,bg="#d3e7fa");subrow.pack(fill="x",padx=6,pady=(1,3))
        ttk.Checkbutton(subrow,text="Χρήση υποτίτλων",
                        variable=self.copy_subtitles).pack(side="left")
        ttk.Button(subrow,text="📂 SRT / ASS",command=self.browse_subtitle).pack(side="right")
        # Clearly separated settings tabs, without scrolling through one huge form.
        settings_root=tk.Frame(right,bg=paper)
        # Right settings are packed after the fixed footer.
        style.configure("Output.TNotebook",background="#c4dcf5",borderwidth=1)
        style.configure("Output.TNotebook.Tab",font=("Segoe UI",10,"bold"),
                        padding=(13,8),background="#c9dff3",foreground=navy)
        style.map("Output.TNotebook.Tab",
                  background=[("selected","#f8fbff"),("active","#deefff")],
                  foreground=[("selected","#0a467f")])
        tabs=ttk.Notebook(settings_root,style="Output.TNotebook")
        tabs.pack(side="top",fill="both",expand=True)
        self.settings_tabs=tabs
        picture=tk.Frame(tabs,bg=paper)
        pic_canvas=tk.Canvas(picture,bg=paper,highlightthickness=0)
        pic_scroll=ttk.Scrollbar(picture,orient="vertical",command=pic_canvas.yview)
        pic_canvas.configure(yscrollcommand=pic_scroll.set)
        pic_scroll.pack(side="right",fill="y")
        pic_canvas.pack(side="left",fill="both",expand=True)
        picture_form=tk.Frame(pic_canvas,bg=paper,padx=5,pady=3)
        pic_window=pic_canvas.create_window((0,0),window=picture_form,anchor="nw")
        picture_form.bind("<Configure>",lambda e:pic_canvas.configure(scrollregion=pic_canvas.bbox("all")))
        pic_canvas.bind("<Configure>",lambda e:pic_canvas.itemconfigure(pic_window,width=e.width))
        pic_canvas.bind("<MouseWheel>",lambda e:pic_canvas.yview_scroll(-int(e.delta/120),"units"))
        audio_page=tk.Frame(tabs,bg=paper,padx=5,pady=5)
        subtitle_page=tk.Frame(tabs,bg=paper,padx=5,pady=5)
        tabs.add(picture,text="▣ Εικόνα")
        tabs.add(audio_page,text="♪ Ήχος")
        tabs.add(subtitle_page,text="Aa Υπότιτλοι")
        def group(parent,title):
            box=tk.Frame(parent,bg="#f3f8ff",
                         highlightbackground="#9dbfe1",highlightthickness=1)
            box.pack(fill="x",padx=2,pady=(2,7))
            tk.Label(box,text=title,bg="#c4dff7",fg=navy,anchor="w",
                     font=("Segoe UI",10,"bold"),padx=9,pady=4).pack(fill="x")
            return box
        def choices(box,var,entries):
            radios=[]
            for value,label in entries:
                rb=tk.Radiobutton(box,text=label,variable=var,value=value,
                    bg="#f3f8ff",fg=ink,activebackground="#dceeff",
                    selectcolor="#e4f3ff",anchor="w",justify="left",
                    font=("Segoe UI",10),highlightthickness=0,borderwidth=0,
                    padx=7,pady=1)
                rb.pack(fill="x",padx=5)
                radios.append((value,rb))
            def selected(*_):
                for value,rb in radios:
                    is_selected=var.get()==value
                    rb.configure(bg="#b7ddff" if is_selected else "#f3f8ff",
                                 font=("Segoe UI",10,"bold" if is_selected else "normal"))
            var.trace_add("write",selected)
            selected()
        choices(group(picture_form,"▣  Προφίλ ποιότητας"),self.quality,
                (("Μέγιστη","Μέγιστη ποιότητα"),
                 ("Ισορροπημένη","Ισορροπημένο (προτεινόμενο)"),
                 ("Μικρότερο αρχείο","Μικρότερο αρχείο")))
        choices(group(picture_form,"▣  Ανάλυση εξόδου"),self.size,
                (("Πρωτότυπη","Πρωτότυπη (χωρίς αλλαγή)"),
                 ("1080p","Full HD · 1920 × 1080"),
                 ("4K","Ultra HD · 3840 × 2160")))
        choices(group(picture_form,"▣  Μορφή εξόδου"),self.format,
                (("MP4","MP4 (συμβατό)"),("MKV","MKV")))
        sound=group(audio_page,"♪  Μορφή ήχου")
        choices(sound,self.audio,
                (("AAC Stereo","AAC Stereo · συμβατό"),
                 ("Dolby Digital AC3","Dolby Digital AC3"),
                 ("Αρχικός ήχος","Διατήρηση αρχικού ήχου")))
        details=group(subtitle_page,"Aa  Εμφάνιση υποτίτλων")
        def option(parent,label,var,values):
            line=tk.Frame(parent,bg="#f3f8ff")
            line.pack(fill="x",padx=8,pady=4)
            tk.Label(line,text=label,bg="#f3f8ff",fg=navy,
                     font=("Segoe UI",9,"bold"),width=12,anchor="w").pack(side="left")
            ttk.Combobox(line,textvariable=var,values=values,
                         font=("Segoe UI",9),state="readonly",
                         width=15).pack(side="left",fill="x",expand=True)
        option(details,"Μέγεθος",self.subtitle_size,
               ("Μικρό (80%)","Μεσαίο (100%)","Μεγάλο (120%)","Πολύ μεγάλο (140%)"))
        option(details,"Θέση",self.subtitle_position,("Κάτω","Κέντρο","Πάνω"))
        line=tk.Frame(details,bg="#f3f8ff");line.pack(fill="x",padx=8,pady=(4,9))
        tk.Label(line,text="Καθυστέρηση",bg="#f3f8ff",fg=navy,
                 font=("Segoe UI",9,"bold"),width=12,anchor="w").pack(side="left")
        ttk.Entry(line,textvariable=self.subtitle_delay,width=7).pack(side="left")
        tk.Label(line,text="δευτερόλεπτα",bg="#f3f8ff",fg="#48627c",
                 font=("Segoe UI",9)).pack(side="left",padx=6)

        # Always-visible compact footer. The guard shows only real warnings.
        footer=tk.Frame(right,bg=paper)
        footer.pack(side="bottom",fill="x",padx=6,pady=(0,2))
        settings_root.pack(side="top",fill="both",expand=True,padx=6,pady=(3,2))
        guard=tk.Frame(footer,bg="#fff0c6",highlightbackground="#ddb655",
                       highlightthickness=1)
        guard.pack(fill="x",pady=(1,2))
        guard_header=tk.Frame(guard,bg="#ffe09b")
        guard_header.pack(fill="x")
        tk.Label(guard_header,text="⚠  Smart Quality Guard",bg="#ffe09b",
                 fg="#6a4706",font=("Segoe UI",10,"bold"),
                 padx=8,pady=2).pack(side="left",fill="x",expand=True)
        switch=tk.Canvas(guard_header,width=57,height=26,bg="#ffe09b",
                         highlightthickness=0,cursor="hand2")
        switch.pack(side="right",padx=7,pady=1)
        def render_guard_switch(*_):
            from PIL import Image,ImageDraw,ImageFont,ImageTk
            enabled=self.smart_guard_enabled.get()
            im=Image.new("RGBA",(114,52),(0,0,0,0))
            d=ImageDraw.Draw(im)
            d.rounded_rectangle((2,2,112,50),radius=24,
                                fill="#14ad43" if enabled else "#8e9ea7",
                                outline="#11823c" if enabled else "#68747b",width=3)
            dotx=78 if enabled else 26
            d.ellipse((dotx-18,8,dotx+18,44),
                      fill="#ffffff",outline="#c8e3ef",width=3)
            switch._skin=ImageTk.PhotoImage(im.resize((57,26),Image.Resampling.LANCZOS))
            switch.delete("all")
            switch.create_image(0,0,anchor="nw",image=switch._skin)
        switch.bind("<Button-1>",lambda _:(self.smart_guard_enabled.set(not self.smart_guard_enabled.get()),
                                           self.update_quality_hint()))
        self.smart_guard_enabled.trace_add("write",render_guard_switch)
        self.smart_guard_enabled.trace_add("write",lambda *_:self.update_quality_hint())
        render_guard_switch()
        self.guard_switch=switch
        self.quality_description=tk.StringVar()
        self.quality_warning=tk.StringVar()
        self.guard_message=tk.Label(guard,textvariable=self.quality_warning,
                 bg="#fff0c6",fg="#7a4908",font=("Segoe UI",9),
                 anchor="w",justify="left",wraplength=295,padx=8,pady=3)
        self.guard_message.pack(fill="x")
        actions=tk.Frame(footer,bg=paper)
        actions.pack(fill="x",pady=(0,2))
        ttk.Button(actions,text="✓ Προτεινόμενες",
                   command=self.recommended_settings).pack(
                       side="left",fill="x",expand=True,padx=(0,3))
        ttk.Button(actions,text="↺ Επαναφορά",
                   command=self.recommended_settings).pack(
                       side="left",fill="x",expand=True,padx=(3,0))
        location=tk.Frame(footer,bg="#d4e7f8",highlightbackground="#a1c0db",
                          highlightthickness=1)
        location.pack(fill="x",pady=(1,0))
        tk.Label(location,text="▣ Έξοδος",bg="#d4e7f8",fg=navy,
                 font=("Segoe UI",9,"bold"),width=9,anchor="w").pack(
                     side="left",padx=(5,2))
        ttk.Button(location,text="…",width=2,command=self.destination).pack(
                     side="right",padx=(1,4),pady=3)
        ttk.Entry(location,textvariable=self.output).pack(
                     side="left",fill="x",expand=True,padx=(0,3),pady=3)
    def open_settings(self):
        self.settings_tabs.select(0)
        self.settings_tabs.focus_set()
    def show_about(self):
        messagebox.showinfo("MovieShrink Pro","MovieShrink Pro για Windows 10.\n"
              "MP4 / MKV, 1080p / 4K, ουρά μετατροπής, FFmpeg.\n"
              "Η πλήρης εισαγωγή DVD VIDEO_TS και οι ρυθμίσεις εμφάνισης υποτίτλων "
              "δεν έχουν ολοκληρωθεί ακόμη.")
    def update_progress_target(self,*_):
        target=self.size.get()
        if target=="Πρωτότυπη":target="αρχική ανάλυση"
        self.output_progress_label.set(f"Μετατροπή σε {target} • Συνολική πρόοδος")
    def recommended_settings(self):
        self.quality.set("Ισορροπημένη")
        self.size.set("1080p")
        self.format.set("MP4")
        self.audio.set("AAC Stereo")
    def update_quality_hint(self,*_):
        if not hasattr(self,"quality_warning"):return
        # No permanent explanatory paragraph: warn only when a real risk applies.
        warning=""
        if not self.smart_guard_enabled.get():
            self.quality_warning.set("")
            if hasattr(self,"guard_message"):self.guard_message.pack_forget()
            return
        if self.size.get()=="4K":
            warning="4K: πολύ αργή μετατροπή · το upscaling δεν προσθέτει λεπτομέρεια."
        elif self.audio.get()=="Dolby Digital AC3":
            warning="Το AC3 δεν δημιουργεί πραγματικό surround από stereo."
        elif self.format.get()=="MP4" and self.audio.get()=="Αρχικός ήχος":
            warning="Ο αρχικός ήχος ίσως δεν είναι συμβατός με MP4."
        self.quality_warning.set(warning)
        if hasattr(self,"guard_message"):
            if warning:self.guard_message.pack(fill="x")
            else:self.guard_message.pack_forget()
    def toggle_queue_checkbox(self,event):
        if self.worker and self.worker.is_alive():return
        if self.tree.identify_region(event.x,event.y)!="cell":return
        if self.tree.identify_column(event.x)!="#1":return
        row=self.tree.identify_row(event.y)
        if not row:return
        i=int(row)
        if 0<=i<len(self.items):
            self.items[i]["enabled"]=not self.items[i].get("enabled",True)
            self.refresh()
        return "break"
    def _selected(self,event=None):
        if not self.items:return
        selected=self.tree.selection()
        if not selected:return
        i=int(selected[0])
        if i>=len(self.items):return
        path=self.items[i]["path"]
        self.current_detail.set(path.name)
        self.preview_duration=self.items[i].get("duration_seconds",0.0)
        self.preview_seek=5.0
        self.preview_position.set(0)
        self.preview_clock.set("00:00 / "+self.clock_string(self.preview_duration))
        sub=self.sub(path)
        self.subtitle_info.set("Υπότιτλοι: "+sub.name if sub else "Δεν βρέθηκαν εξωτερικοί SRT / ASS")
        self.preview_subtitle_cues=read_srt_cues(sub) if sub and sub.suffix.lower()==".srt" else []
        if self.preview_enabled:self.preview()
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i,x in enumerate(self.items):
            self.tree.insert("","end",iid=str(i),tags=(("active" if x["state"]=="Επεξεργασία" else "completed" if x["state"]=="Έτοιμο" else "error" if x["state"]=="Σφάλμα" else "odd" if i%2 else "even"),),values=("☑" if x.get("enabled",True) else "☐",x["path"].name,x.get("duration_text","—"),x.get("resolution","—"),f'{x["pct"]:.0f}%',x["state"]))
        enabled=[x for x in self.items if x.get("enabled",True)]
        self.allpct.set(sum(x["pct"] for x in enabled)/len(enabled) if enabled else 0)
        if hasattr(self,"empty_queue_hint"):
            if self.items:self.empty_queue_hint.place_forget()
            else:self.empty_queue_hint.place(relx=.5,rely=.5,anchor="center")
        if hasattr(self,"queue_summary"):self.queue_summary.set(f"{sum(x.get('enabled',True) for x in self.items)}/{len(self.items)} επιλεγμένες  ·  {sum(x['state']=='Έτοιμο' for x in self.items)} ολοκληρωμένες")
    def sub(self,p):
        custom=self.external_subtitles.get(str(p))
        if custom and custom.is_file():return custom
        return next((p.with_suffix(ext) for ext in (".srt",".ass",".ssa") if p.with_suffix(ext).is_file()),None)
    def add(self,paths):
        seen={str(x["path"]) for x in self.items}
        for name in paths:
            p=P(name)
            if p.is_file() and p.suffix.lower() in EXT and str(p) not in seen:
                self.items.append(dict(path=p,state="Αναμονή",pct=0,enabled=True));seen.add(str(p))
                index=len(self.items)-1
                def metadata(i=index,filename=p):
                    try:
                        duration,w,h,_=probe(filename)
                        hh=int(duration)//3600;mm=int(duration)%3600//60;ss=int(duration)%60
                        self.events.put(("metadata",i,f"{hh:02d}:{mm:02d}:{ss:02d}",f"{w}×{h}",duration))
                    except Exception:pass
                threading.Thread(target=metadata,daemon=True).start()
        self.refresh()
    def addfiles(self):
        self.add(filedialog.askopenfilenames(filetypes=[("Βίντεο","*.mp4 *.mkv *.avi *.mov *.m4v *.mpg *.mpeg *.ts *.webm")]))
    def addfolder(self):
        d=filedialog.askdirectory()
        if d:self.add(sorted(P(d).iterdir()))
    def adddvd(self):
        d=filedialog.askdirectory(title="Επιλογή DVD VIDEO_TS")
        if not d:return
        p=P(d);p=p/"VIDEO_TS" if (p/"VIDEO_TS").exists() else p
        # VOB DVD multi-part/title navigation is not implemented in this beta.
        messagebox.showinfo("DVD","Η ανάγνωση πλήρους DVD VIDEO_TS δεν είναι ακόμη διαθέσιμη στην έκδοση αυτή. Για δοκιμή επίλεξε απλό MP4 ή MKV.")
    def remove(self):
        if self.worker and self.worker.is_alive():return
        indexes={int(i) for i in self.tree.selection()}
        self.items=[x for i,x in enumerate(self.items) if i not in indexes];self.refresh()
    def destination(self):
        p=filedialog.askdirectory()
        if p:self.output.set(p)
    def clock_string(self,seconds):
        seconds=max(0,int(seconds or 0))
        return f"{seconds//3600:02d}:{(seconds%3600)//60:02d}:{seconds%60:02d}"
    def preview_seek_begin(self,event=None):
        self.preview_seek_drag=True
    def preview_seek_end(self,event=None):
        self.preview_seek_drag=False
        if not self.preview_enabled:return
        selected=self.tree.selection()
        index=int(selected[0]) if selected else 0
        if index>=len(self.items):return
        duration=self.items[index].get("duration_seconds",0.0)
        if duration<=0:return
        self.preview_seek=max(0,min(duration-1,duration*self.preview_position.get()/100))
        self.preview()
    def browse_subtitle(self):
        selected=self.tree.selection()
        if not selected:
            messagebox.showinfo("Υπότιτλοι","Επίλεξε πρώτα ταινία από τη λίστα.")
            return
        index=int(selected[0])
        if index>=len(self.items):return
        path=filedialog.askopenfilename(title="Επιλογή υποτίτλων",
             filetypes=[("Υπότιτλοι","*.srt *.ass *.ssa")])
        if path:
            self.external_subtitles[str(self.items[index]["path"])]=P(path)
            self.subtitle_info.set("Υπότιτλοι: "+P(path).name)
            self.copy_subtitles.set(True)
            self.preview_subtitle_cues=read_srt_cues(path) if path.lower().endswith(".srt") else []
    def update_live_subtitles(self,position):
        overlay=self.preview_subtitle_overlay
        if not self.copy_subtitles.get() or not self.preview_subtitle_cues:
            overlay.configure(text="")
            return
        try:delay=float(self.subtitle_delay.get().replace(",","."))
        except ValueError:delay=0
        display=""
        for st,en,body in self.preview_subtitle_cues:
            if st+delay<=position<=en+delay:
                display=body
                break
            if st+delay>position:break
        scale={"Μικρό (80%)":9,"Μεσαίο (100%)":11,
               "Μεγάλο (120%)":13,"Πολύ μεγάλο (140%)":15}
        valign={"Πάνω":.13,"Κέντρο":.50,"Κάτω":.86}
        overlay.configure(text=display,
                          font=("Segoe UI",scale.get(self.subtitle_size.get(),11),"bold"))
        overlay.place_configure(rely=valign.get(self.subtitle_position.get(),.86))
    def save_preview_frame(self):
        if self.current_preview_frame is None:
            messagebox.showinfo("Καρέ","Ενεργοποίησε την προεπισκόπηση πρώτα.")
            return
        filename=filedialog.asksaveasfilename(defaultextension=".png",
            filetypes=[("Εικόνα PNG","*.png")],title="Αποθήκευση καρέ")
        if filename:
            self.current_preview_frame.save(filename)
    def enable_preview(self):
        if not self.preview_enabled:self.toggle_preview()
    def toggle_preview(self):
        if self.preview_enabled:
            self.disable_preview()
        else:
            if not self.items:
                messagebox.showinfo("Προεπισκόπηση","Πρόσθεσε πρώτα μια ταινία.")
                return
            self.preview_enabled=True
            self.preview_button.configure(state="disabled")
            self.preview_off_button.configure(state="normal")
            self.preview_capture_button.configure(state="disabled")
            self.preview_pause_button.configure(state="normal",text="⏸ Παύση")
            self.preview_pause.clear()
            self.preview()
    def pause_preview(self):
        if not self.preview_enabled:return
        if self.preview_pause.is_set():
            self.preview_pause.clear()
            self.preview_pause_button.configure(text="⏸ Παύση")
            self.preview_state.set("Προεπισκόπηση: παίζει χωρίς ήχο")
        else:
            self.preview_pause.set()
            self.preview_pause_button.configure(text="▶ Συνέχεια")
            self.preview_state.set("Προεπισκόπηση: σε παύση")
    def disable_preview(self):
        self.preview_enabled=False
        self.preview_generation+=1
        self.preview_stop.set()
        self.preview_pause.clear()
        proc=self.preview_proc
        if proc and proc.poll() is None:
            try:proc.terminate()
            except OSError:pass
        self.preview_button.configure(text="▶ Παίξε",state="normal")
        self.preview_off_button.configure(state="disabled")
        self.preview_capture_button.configure(state="disabled")
        self.preview_pause_button.configure(state="disabled",text="⏸ Παύση")
        self.preview_state.set("Προεπισκόπηση: κλειστή")
        self.preview_clock.set("00:00 / "+self.clock_string(self.preview_duration))
        self.image.configure(image="",text="▶\n\nΠροεπισκόπηση απενεργοποιημένη")
        self.pic=None
        self.current_preview_frame=None
        self.preview_subtitle_overlay.configure(text="")
    def preview(self):
        """CPU-friendly silent video playback, separately switchable from conversion."""
        if not self.preview_enabled or not self.items:return
        index=int(self.tree.selection()[0]) if self.tree.selection() else 0
        if index>=len(self.items):return
        self.preview_generation+=1
        generation=self.preview_generation
        self.preview_stop.set()
        old=self.preview_proc
        if old and old.poll() is None:
            try:old.terminate()
            except OSError:pass
        stop=threading.Event()
        self.preview_stop=stop
        self.preview_pause.clear()
        self.preview_pause_button.configure(text="⏸ Παύση")
        self.preview_state.set("Προεπισκόπηση: φόρτωση…")
        path=self.items[index]["path"]
        self.preview_duration=self.items[index].get("duration_seconds",self.preview_duration)
        start_time=self.preview_seek
        def worker():
            proc=None
            try:
                ff=binary("ffmpeg.exe")
                if not ff:raise RuntimeError("Δεν βρέθηκε FFmpeg.")
                if not self.preview_duration:
                    try:
                        duration,_,_,_=probe(path)
                        self.events.put(("preview_duration",generation,duration))
                    except Exception:pass
                # 480x270 at 5 fps: crisp at window size while remaining CPU-conscious.
                cmd=[ff,"-hide_banner","-loglevel","error","-ss",str(start_time),"-i",str(path),
                     "-an","-vf","fps=5,scale=480:270:force_original_aspect_ratio=decrease,"
                     "pad=480:270:(ow-iw)/2:(oh-ih)/2",
                     "-pix_fmt","rgb24","-f","rawvideo","pipe:1"]
                proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                                      creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                self.preview_proc=proc
                frame_bytes=480*270*3
                frame_index=0
                while not stop.is_set() and generation==self.preview_generation:
                    if self.preview_pause.is_set():
                        time.sleep(.08)
                        continue
                    frame=proc.stdout.read(frame_bytes)
                    if len(frame)!=frame_bytes:break
                    if self.events.qsize()<8:
                        self.events.put(("preview_frame",generation,frame,start_time+frame_index/5))
                    frame_index+=1
                    time.sleep(.19)
            except Exception as e:
                self.events.put(("preview_error",generation,str(e)))
            finally:
                if proc is not None:
                    if proc.poll() is None:
                        try:proc.terminate()
                        except OSError:pass
                    try:proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                if generation==self.preview_generation:
                    self.events.put(("preview_end",generation))
        self.preview_thread=threading.Thread(target=worker,daemon=True)
        self.preview_thread.start()
    def close_app(self):
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("Μετατροπή σε εξέλιξη","Σταμάτησε πρώτα τη μετατροπή.")
            return
        if self.preview_enabled:self.disable_preview()
        self.destroy()
    def start(self):
        if self.worker and self.worker.is_alive():return
        if not any(x.get("enabled",True) for x in self.items):
            messagebox.showwarning("Προσοχή","Επίλεξε ταινίες για μετατροπή.");return
        if not binary("ffmpeg.exe") or not binary("ffprobe.exe"):messagebox.showerror("Σφάλμα","Λείπουν τα ενσωματωμένα εργαλεία μετατροπής.");return
        try:
            P(self.output.get()).mkdir(parents=True,exist_ok=True)
            if self.smart_guard_enabled.get() and self.size.get()=="4K" and any(probe(x["path"])[2]<1080 for x in self.items):
                if not messagebox.askyesno("Smart Quality Guard","Το 4K upscaling δεν προσθέτει πραγματική λεπτομέρεια. Συνέχεια;"):return
            if self.smart_guard_enabled.get() and self.audio.get()=="Dolby Digital AC3" and any((probe(x["path"])[3] or {}).get("channels",0)<6 for x in self.items):
                if not messagebox.askyesno("Smart Quality Guard","Μερικές ταινίες δεν έχουν ήχο 5.1. Δεν μπορούμε να δημιουργήσουμε πραγματικό surround. Συνέχεια;"):return
        except Exception as e:messagebox.showerror("Σφάλμα",str(e));return
        # Freeze all Tk values on the GUI thread. The transcoding worker must never
        # read Tk variables, which can fail with "main thread is not in main loop".
        try:
            cfg=dict(output=self.output.get(),size=self.size.get(),audio=self.audio.get(),
                     format=self.format.get(),quality=self.quality.get(),
                     copy_subtitles=self.copy_subtitles.get(),
                     subtitle_size=self.subtitle_size.get(),
                     subtitle_position=self.subtitle_position.get(),
                     subtitle_delay=self.subtitle_delay.get(),
                     custom_subtitles=dict(self.external_subtitles))
        except tk.TclError as exc:
            messagebox.showerror("Ρυθμίσεις",str(exc));return
        self.stopflag=False;self.btn.configure(state="disabled");self.btn._update_skin()
        self.worker=threading.Thread(target=self.convert,args=(cfg,),daemon=True);self.worker.start()
    def stop(self):
        self.stopflag=True
        if self.process and self.process.poll() is None:self.process.terminate()
    def convert(self,cfg):
        for i,x in enumerate(self.items):
            if self.stopflag:break
            if not x.get("enabled",True) or x["state"]=="Έτοιμο":continue
            tmp=None
            try:
                source=x["path"];duration,w,h,a=probe(source);x["state"]="Επεξεργασία"
                src_label=f"{w}×{h}" + (f" ({h}p)" if h in (480,576,720,1080,1440,2160) else "")
                dest_label=cfg["size"]
                if dest_label=="Πρωτότυπη":dest_label=f"{h}p (χωρίς αλλαγή ανάλυσης)"
                self.events.put(("resolution",i,src_label,dest_label))
                suffix=".mp4" if cfg["format"]=="MP4" else ".mkv"
                out=P(cfg["output"])/(source.stem+(" (4K)" if cfg["size"]=="4K" else " (1080p)" if cfg["size"]=="1080p" else "")+suffix)
                if out.resolve()==source.resolve():raise RuntimeError("Η έξοδος συμπίπτει με την πηγή.")
                if out.exists():out=out.with_name(out.stem+"_"+str(int(time.time()))+suffix)
                tmp=out.with_name(out.stem+".partial"+suffix)
                cmd=[binary("ffmpeg.exe"),"-y","-hide_banner","-i",str(source),"-map","0:v:0","-map","0:a:0?","-c:v","libx264","-preset","veryfast","-crf",str({"Μέγιστη":18,"Ισορροπημένη":21,"Μικρότερο αρχείο":25}[cfg["quality"]]),"-pix_fmt","yuv420p"]
                size=cfg["size"]
                if size!="Πρωτότυπη":
                    width,height=(1920,1080) if size=="1080p" else (3840,2160)
                    cmd+=["-vf",f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"]
                audio=cfg["audio"]
                if audio=="Αρχικός ήχος":cmd+=["-c:a","copy"]
                elif audio=="Dolby Digital AC3":cmd+=["-c:a","ac3","-b:a","384k"]
                else:cmd+=["-c:a","aac","-b:a","192k","-ac","2"]
                if suffix==".mp4":cmd+=["-movflags","+faststart"]
                cmd+=["-progress","pipe:1","-nostats",str(tmp)]
                self.process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                start=time.monotonic();fps=0
                for line in self.process.stdout:
                    if self.stopflag:break
                    key,sep,val=line.strip().partition("=")
                    if key=="fps":
                        try:fps=float(val)
                        except ValueError:pass
                    if key in ("out_time_us","out_time_ms") and duration>0:
                        try:x["pct"]=min(99.5,100*int(val)/1000000/duration)
                        except ValueError:pass
                    if key=="progress":
                        elapsed=time.monotonic()-start
                        eta=elapsed*(100-x["pct"])/max(x["pct"],.1)
                        self.events.put(("progress",i,x["pct"],fps,eta))
                code=self.process.wait()
                if code or self.stopflag:raise RuntimeError("Η μετατροπή διακόπηκε ή απέτυχε.")
                outduration,_,_,outaudio=probe(tmp)
                if duration>2 and outduration<duration*.90:raise RuntimeError("Ελλιπές τελικό βίντεο.")
                if a and not outaudio:raise RuntimeError("Λείπει ο ήχος από το τελικό αρχείο.")
                tmp.rename(out)
                sub=cfg["custom_subtitles"].get(str(source)) or self.sub(source)
                if sub and cfg["copy_subtitles"]:
                    size_text=cfg["subtitle_size"]
                    size_pct=int(re.search(r"(\d+)%",size_text).group(1))
                    pos=cfg["subtitle_position"]
                    try:delay=float(cfg["subtitle_delay"].replace(",","."))
                    except ValueError:raise ValueError("Η καθυστέρηση υποτίτλων πρέπει να είναι αριθμός.")
                    if sub.suffix.lower()==".srt" and (size_pct!=100 or pos!="Κάτω" or abs(delay)>.0001):
                        style_srt_as_ass(sub,out.with_suffix(".ass"),size_pct,pos,delay)
                    else:
                        if sub.suffix.lower()!=".srt" and (size_pct!=100 or pos!="Κάτω" or abs(delay)>.0001):
                            self.events.put(("warn","Οι αλλαγές εμφάνισης εφαρμόζονται μόνο σε SRT. Το ASS διατηρήθηκε αρχικό."))
                        shutil.copy2(sub,out.with_suffix(sub.suffix))
                x["pct"]=100;x["state"]="Έτοιμο"
                self.events.put(("progress",i,100,0,0))
            except Exception as e:
                x["state"]="Σφάλμα";x["error"]=str(e)
                self.events.put(("error",i,str(e)))
                try:
                    if tmp and tmp.exists():tmp.unlink()
                except OSError:pass
            self.events.put(("refresh",))
        self.events.put(("done",))
    def poll(self):
        try:
            while True:
                event=self.events.get_nowait()
                if event[0]=="preview_duration":
                    _,generation,duration=event
                    if generation==self.preview_generation and self.preview_enabled:
                        self.preview_duration=duration
                elif event[0]=="preview_frame":
                    _,generation,frame,position=event
                    if generation==self.preview_generation and self.preview_enabled:
                        from PIL import Image, ImageTk
                        im=Image.frombytes("RGB",(480,270),frame)
                        self.current_preview_frame=im
                        from PIL import ImageOps
                        bounds=(max(32,self.image.winfo_width()-4),max(32,self.image.winfo_height()-4))
                        fitted=ImageOps.contain(im,bounds,Image.Resampling.LANCZOS)
                        self.pic=ImageTk.PhotoImage(fitted)
                        self.image.configure(image=self.pic,text="")
                        self.preview_capture_button.configure(state="normal")
                        if not self.preview_seek_drag and self.preview_duration>0:
                            self.preview_position.set(min(100,100*position/self.preview_duration))
                        self.preview_clock.set(self.clock_string(position)+" / "+self.clock_string(self.preview_duration))
                        self.update_live_subtitles(position)
                        if not self.preview_pause.is_set():
                            self.preview_state.set("Προεπισκόπηση: παίζει χωρίς ήχο • 5 FPS")
                elif event[0]=="preview_error":
                    if event[1]==self.preview_generation:self.preview_state.set("Σφάλμα: "+event[2])
                elif event[0]=="preview_end":
                    if event[1]==self.preview_generation and self.preview_enabled:
                        self.preview_state.set("Προεπισκόπηση: τέλος αποσπάσματος")
                elif event[0]=="metadata":
                    _,i,duration_text,resolution,duration_seconds=event
                    if 0<=i<len(self.items):
                        self.items[i]["duration_text"]=duration_text
                        self.items[i]["duration_seconds"]=duration_seconds
                        self.items[i]["resolution"]=resolution
                        if self.tree.selection() and int(self.tree.selection()[0])==i:
                            self.preview_duration=duration_seconds
                        self.refresh()
                elif event[0]=="resolution":
                    _,i,source_label,destination_label=event
                    self.source_progress_label.set(f"Αρχικό βίντεο: {source_label} • Ταινία {i+1}/{len(self.items)}")
                    self.output_progress_label.set(f"Μετατροπή σε {destination_label} • Συνολική πρόοδος")
                elif event[0]=="warn":self.status.set(event[1])
                elif event[0]=="error":self.status.set(f"Σφάλμα ταινίας {event[1]+1}: {event[2]}")
                elif event[0]=="progress":
                    _,i,pct,fps,eta=event
                    self.pct.set(pct);self.status.set(f'Ταινία {i+1}/{len(self.items)}: {self.items[i]["path"].name} — {pct:.1f}%')
                    self.metrics.set(f"Ταχύτητα: {fps:.1f} FPS | Υπόλοιπο: περίπου {eta/60:.0f} λεπτά")
                elif event[0]=="done":
                    self.btn.configure(state="normal");self.btn._update_skin()
                    self.status.set(f'Ολοκληρώθηκαν {sum(x["state"]=="Έτοιμο" for x in self.items)}/{sum(x.get("enabled",True) for x in self.items)} επιλεγμένες ταινίες')
                if event[0] in ("progress","refresh","done"):self.refresh()
        except queue.Empty:pass
        self.after(100,self.poll)
if __name__=="__main__":
    if "--self-test" in sys.argv:sys.exit(self_test())
    app=MovieShrink()
    if os.name=="nt":
        try:app.state("zoomed")
        except tk.TclError:pass
    app.mainloop()
