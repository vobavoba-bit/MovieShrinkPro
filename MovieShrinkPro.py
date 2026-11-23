"""MovieShrink Pro: free Windows 10 video batch converter (unencrypted sources only)."""
import os, sys, pathlib, subprocess, json, shutil, threading, queue, tempfile, time, base64
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
class MovieShrink(tk.Tk):
    def __init__(self):
        super().__init__();self.title("MovieShrink Pro — DVD / USB / MP4");self.geometry("1150x730");self.minsize(970,640)
        self.items=[];self.events=queue.Queue();self.worker=None;self.process=None;self.stopflag=False
        self.quality=tk.StringVar(value="Ισορροπημένη");self.size=tk.StringVar(value="1080p")
        self.audio=tk.StringVar(value="AAC Stereo");self.format=tk.StringVar(value="MP4")
        self.output=tk.StringVar(value=str(P.home()/"Videos"/"MovieShrinkPro"))
        self.pct=tk.DoubleVar();self.allpct=tk.DoubleVar();self.status=tk.StringVar(value="Έτοιμο")
        self.metrics=tk.StringVar(value="Ταχύτητα: — FPS | Χρόνος: —")
        self.source_progress_label=tk.StringVar(value="Αρχική ταινία: —")
        self.output_progress_label=tk.StringVar(value="Μετατροπή σε 1080p • Συνολική πρόοδος")
        self.preview_stop=threading.Event();self.preview_pause=threading.Event()
        self.preview_generation=0;self.preview_proc=None
        self.preview_enabled=False;self.preview_thread=None
        self.ui()
        if hasattr(self,"brand_image"):self.iconphoto(True,self.brand_image)
        self.after(100,self.poll)
        for v in (self.quality,self.size,self.format,self.audio):v.trace_add("write",self.update_quality_hint)
        self.size.trace_add("write",self.update_progress_target)
        self.update_quality_hint();self.update_progress_target()
        self.protocol("WM_DELETE_WINDOW",self.close_app)
    def glossy_button(self,parent,label,command,colors,width=152,height=52):
        """Real rounded anti-aliased button images; Windows Tk draws exact pixels."""
        from PIL import Image, ImageDraw, ImageFont, ImageTk
        import tkinter.font as tkfont
        import math
        normal_top,normal_bottom,outline=colors
        def rgb(h):return tuple(int(h[i:i+2],16) for i in (1,3,5))
        def mix(a,b,t):return tuple(round(a[i]*(1-t)+b[i]*t) for i in range(3))
        def artwork(hover=False):
            top=rgb(normal_top);bottom=rgb(normal_bottom)
            if hover:
                top=mix(top,(255,255,255),.18)
                bottom=mix(bottom,(255,255,255),.10)
            im=Image.new("RGBA",(width*2,height*2),(0,0,0,0))
            draw=ImageDraw.Draw(im)
            w,h=im.size
            mask=Image.new("L",(w,h),0)
            md=ImageDraw.Draw(mask)
            md.rounded_rectangle((2,2,w-3,h-3),radius=20,fill=255)
            gradient=Image.new("RGBA",(w,h))
            gd=ImageDraw.Draw(gradient)
            for y in range(h):
                t=y/max(1,h-1)
                col=mix(top,bottom,t)
                gd.line((0,y,w,y),fill=col+(255,))
            im.paste(gradient,(0,0),mask)
            draw=ImageDraw.Draw(im)
            draw.rounded_rectangle((2,2,w-3,h-3),radius=20,outline=rgb(outline)+(255,),width=4)
            draw.arc((9,6,w-10,h-12),181,358,fill=(255,255,255,145),width=3)
            try:
                font_path=os.path.join(os.environ.get("WINDIR","C:\\Windows"),"Fonts","segoeuib.ttf")
                font=ImageFont.truetype(font_path,26)
            except OSError:
                try:font=ImageFont.truetype("DejaVuSans-Bold.ttf",24)
                except OSError:font=ImageFont.load_default()
            bbox=draw.textbbox((0,0),label,font=font)
            x=(w-(bbox[2]-bbox[0])+48)/2
            y=(h-(bbox[3]-bbox[1]))/2-bbox[1]
            if label=="ΕΝΑΡΞΗ":
                draw.polygon([(28,30),(28,76),(65,53)],fill=(255,255,255,245))
            elif label=="ΔΙΑΚΟΠΗ":
                draw.rounded_rectangle((27,35,61,69),radius=3,fill=(255,255,255,245))
            draw.text((x,y+2),label,font=font,fill=(0,0,0,80))
            draw.text((x,y),label,font=font,fill=(255,255,255,255))
            return ImageTk.PhotoImage(im.resize((width,height),Image.Resampling.LANCZOS))
        pic=artwork();hover_pic=artwork(True)
        if not hasattr(self,"_styled_button_images"):self._styled_button_images=[]
        self._styled_button_images.extend((pic,hover_pic))
        btn=tk.Button(parent,image=pic,command=command,bd=0,relief="flat",
                      highlightthickness=0,overrelief="flat",bg="#eef5fc",
                      activebackground="#eef5fc",cursor="hand2",
                      disabledforeground="#d4e4e1")
        btn.bind("<Enter>",lambda e:btn.configure(image=hover_pic) if str(btn.cget("state"))=="normal" else None)
        btn.bind("<Leave>",lambda e:btn.configure(image=pic))
        return btn
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
            try:
                f=ImageFont.truetype(os.path.join(os.environ.get("WINDIR","C:\\Windows"),"Fonts","segoeuib.ttf"),24)
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
        style.configure("Treeview",font=("Segoe UI",9),rowheight=29,
                        background="#f9fcff",fieldbackground="#f9fcff",foreground=ink)
        style.configure("Treeview.Heading",font=("Segoe UI",9,"bold"),background="#c0d8f3",
                        foreground=navy,padding=6)
        style.map("Treeview",background=[("selected","#9bcffa")],foreground=[("selected","#103052")])
        style.configure("TRadiobutton",font=("Segoe UI",9),background=paper,foreground=ink,padding=(0,1))
        style.map("TRadiobutton",background=[("active","#d5eafd")])
        style.configure("TCheckbutton",font=("Segoe UI",9),background=paper,foreground=ink)
        style.configure("TCombobox",font=("Segoe UI",9))
        style.configure("Green.Horizontal.TProgressbar",background="#1ccb43",troughcolor="#b7cee3",thickness=14)
        style.configure("Blue.Horizontal.TProgressbar",background="#149cee",troughcolor="#b7cee3",thickness=13)
        def load_font(size,bold=False):
            fn="segoeuib.ttf" if bold else "segoeui.ttf"
            path=os.path.join(os.environ.get("WINDIR","C:\\Windows"),"Fonts",fn)
            try:return ImageFont.truetype(path,size)
            except OSError:return ImageFont.load_default()
        # Original icon and deep-blue luminous branded header are real image pixels.
        head_bg=Image.new("RGB",(1400,123))
        hd=ImageDraw.Draw(head_bg)
        for y in range(123):
            t=y/122
            hd.line((0,y,1400,y),fill=(5+int(5*t),22+int(40*t),51+int(76*t)))
        for x in range(1400):
            y=103+int(11*__import__("math").sin(x/120))
            hd.line((x,max(0,y-2),x,min(122,y+1)),fill=(23,166,252),width=2)
        hd.line((0,120,1399,120),fill="#45bdff",width=3)
        self.header_img=ImageTk.PhotoImage(head_bg)
        head=tk.Frame(self,bg=dark,height=112)
        head.pack(side="top",fill="x");head.pack_propagate(False)
        tk.Label(head,image=self.header_img,bd=0).place(x=0,y=0,relwidth=1,relheight=1)
        logo=None
        try:
            base=P(getattr(sys,"_MEIPASS",P(__file__).resolve().parent))
            logo=Image.open(base/"assets"/"movieshrink_logo.jpg").convert("RGB")
            self.brand_image=ImageTk.PhotoImage(logo.resize((94,94),Image.Resampling.LANCZOS))
            tk.Label(head,image=self.brand_image,bd=0,bg=dark).place(x=15,y=7)
        except Exception:pass
        tk.Label(head,text="MovieShrink",font=("Segoe UI",27,"bold","italic"),
                 bg="#081f48",fg="#f4f9ff").place(x=120,y=22)
        tk.Label(head,text="Pro",font=("Segoe UI",27,"bold","italic"),
                 bg="#081f48",fg="#f9c83d").place(x=326,y=22)
        tk.Label(head,text="Μετατροπή DVD / MP4 σε 1080p & 4K",
                 font=("Segoe UI",10,"bold"),bg="#081f48",fg="#c9e6ff").place(x=121,y=75)
        marks=tk.Frame(head,bg="#091f44");marks.place(relx=1,x=-8,y=32,anchor="ne")
        for name in ("DVD","USB","MP4","1080p","4K"):
            col="#f9cd47" if name in ("1080p","4K") else "#e3f3ff"
            tk.Label(marks,text=name,font=("Segoe UI",10,"bold"),bg="#12477f",
                     fg=col,highlightbackground="#5da1da",highlightthickness=1,
                     padx=7,pady=6).pack(side="left",padx=2)
        bar=tk.Frame(self,bg="#c7daee",height=54,highlightbackground="#79a5c9",highlightthickness=1)
        bar.pack(side="top",fill="x");bar.pack_propagate(False)
        for cap,act,icon_id,bw in (("Προσθήκη DVD",self.adddvd,"disc",188),
                                    ("Προσθήκη φακέλου",self.addfolder,"folder",214),
                                    ("Προσθήκη USB / MP4",self.addfiles,"usb",220),
                                    ("Αφαίρεση",self.remove,"remove",162)):
            self.metallic_toolbar_button(bar,cap,act,icon_id,width=bw).pack(
                side="left",padx=(8,0),pady=4)
        # Bottom is packed BEFORE the growing center: always remains visible.
        bottom=tk.Frame(self,bg=white,highlightbackground="#5987b9",highlightthickness=2)
        bottom.pack(side="bottom",fill="x",padx=8,pady=(3,6))
        tk.Label(bottom,text="▥   ΠΡΟΟΔΟΣ ΜΕΤΑΤΡΟΠΗΣ",bg="#0c477d",fg="white",
                 font=("Segoe UI",11,"bold"),anchor="w",padx=9,pady=4).pack(fill="x")
        inner=tk.Frame(bottom,bg=white);inner.pack(fill="x",padx=10,pady=(4,0))
        controls=tk.Frame(inner,bg=white);controls.pack(side="right",padx=(12,0),pady=7)
        self.btn=self.glossy_button(controls,"ΕΝΑΡΞΗ",self.start,
                                    ("#62eb77","#08772e","#075322"),width=152,height=50)
        self.btn.pack(side="left",padx=(0,7))
        self.stop_btn=self.glossy_button(controls,"ΔΙΑΚΟΠΗ",self.stop,
                                         ("#ff8888","#b00920","#790719"),width=152,height=50)
        self.stop_btn.pack(side="left")
        bframe=tk.Frame(inner,bg=white);bframe.pack(side="left",fill="both",expand=True)
        for var,style_name,percentage in ((self.source_progress_label,"Green.Horizontal.TProgressbar",self.pct),
                                           (self.output_progress_label,"Blue.Horizontal.TProgressbar",self.allpct)):
            tk.Label(bframe,textvariable=var,bg=white,fg=navy,
                     font=("Segoe UI",10,"bold"),anchor="w").pack(fill="x",pady=(0,1))
            ttk.Progressbar(bframe,variable=percentage,maximum=100,
                            style=style_name).pack(fill="x",pady=(0,4))
        tk.Label(bottom,textvariable=self.status,bg=white,fg="#23547e",
                 font=("Segoe UI",9),anchor="w").pack(fill="x",padx=10)
        tk.Label(bottom,textvariable=self.metrics,bg=white,fg="#23547e",
                 font=("Segoe UI",9,"bold"),anchor="w").pack(fill="x",padx=10,pady=(0,3))
        # Three true interactive panels, preserving functionality.
        main=tk.Frame(self,bg="#bfcfe0")
        main.pack(side="top",fill="both",expand=True,padx=6,pady=(6,3))
        for col,wt,minsize in ((0,36,280),(1,34,275),(2,30,270)):
            main.grid_columnconfigure(col,weight=wt,minsize=minsize)
        main.grid_rowconfigure(0,weight=1)
        def panel(index,title):
            out=tk.Frame(main,bg=paper,highlightbackground="#5d94c0",highlightthickness=2)
            out.grid(row=0,column=index,sticky="nsew",padx=3)
            tk.Label(out,text=title,bg="#0b467f",fg="white",font=("Segoe UI",10,"bold"),
                     anchor="w",padx=8,pady=5).pack(fill="x")
            return out
        left=panel(0,"▣   Ουρά επεξεργασίας")
        center=panel(1,"▣   Ζωντανή προεπισκόπηση")
        right=panel(2,"⚙   Ρυθμίσεις εξόδου")
        # Queue includes duration and source dimensions, populated asynchronously.
        lst=tk.Frame(left,bg=paper);lst.pack(fill="both",expand=True,padx=4,pady=(4,0))
        cols=("file","duration","resolution","pct","state")
        self.tree=ttk.Treeview(lst,columns=cols,show="headings",selectmode="extended",height=8)
        for key,label,w in (("file","Όνομα αρχείου",155),("duration","Διάρκεια",65),
                            ("resolution","Πηγή",75),("pct","%",42),("state","Κατάσταση",92)):
            self.tree.heading(key,text=label)
            self.tree.column(key,width=w,minwidth=30,stretch=(key=="file"))
        yscroll=ttk.Scrollbar(lst,orient="vertical",command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side="right",fill="y")
        self.tree.pack(side="left",fill="both",expand=True)
        self.tree.tag_configure("even",background="#f7fbff")
        self.tree.tag_configure("odd",background="#dfeeff")
        self.tree.bind("<<TreeviewSelect>>",self._selected)
        self.queue_summary=tk.StringVar(value="0 ταινίες στην ουρά")
        tk.Label(left,textvariable=self.queue_summary,bg="#cfe1f3",fg=navy,
                 font=("Segoe UI",9,"bold"),anchor="w",padx=7,pady=4).pack(side="bottom",fill="x")
        # Center preview + explicit enable/pause/off; subtitle copy is a real setting.
        preview_box=tk.Frame(center,bg="#071525",height=190)
        preview_box.pack(fill="x",padx=5,pady=(5,3));preview_box.pack_propagate(False)
        self.image=tk.Label(preview_box,text="▶\nΠροεπισκόπηση απενεργοποιημένη",
                            bg="#071525",fg="#bcd9f2",font=("Segoe UI",10))
        self.image.pack(fill="both",expand=True,padx=3,pady=3)
        pc=tk.Frame(center,bg=paper);pc.pack(fill="x",padx=5,pady=(1,2))
        self.preview_button=ttk.Button(pc,text="▶ Προεπισκόπηση",command=self.toggle_preview)
        self.preview_button.pack(side="left",padx=(0,4))
        self.preview_pause_button=ttk.Button(pc,text="⏸ Παύση",command=self.pause_preview,state="disabled")
        self.preview_pause_button.pack(side="left")
        self.preview_state=tk.StringVar(value="Κλειστή • εξοικονόμηση CPU")
        tk.Label(center,textvariable=self.preview_state,bg=paper,fg="#406b94",
                 font=("Segoe UI",9),anchor="w",padx=7).pack(fill="x")
        self.current_detail=tk.StringVar(value="Επίλεξε ταινία από την ουρά")
        tk.Label(center,textvariable=self.current_detail,bg=paper,fg=navy,
                 font=("Segoe UI",9,"bold"),anchor="w",wraplength=295,
                 justify="left",padx=7,pady=3).pack(fill="x")
        subs=tk.Frame(center,bg="#d3e7fa",highlightbackground="#8eb9dd",highlightthickness=1)
        subs.pack(fill="x",padx=5,pady=(3,4))
        tk.Label(subs,text="Aa   Εξωτερικοί υπότιτλοι SRT / ASS",bg="#b6d4f1",fg=navy,
                 font=("Segoe UI",10,"bold"),anchor="w",padx=7,pady=4).pack(fill="x")
        self.subtitle_info=tk.StringVar(value="Αυτόματη ανίχνευση SRT / ASS")
        tk.Label(subs,textvariable=self.subtitle_info,bg="#d3e7fa",fg="#1e507e",
                 font=("Segoe UI",9),anchor="w",wraplength=300,padx=7,pady=3).pack(fill="x")
        self.copy_subtitles=tk.BooleanVar(value=True)
        ttk.Checkbutton(subs,text="Αντιγραφή εξωτερικών υποτίτλων",
                        variable=self.copy_subtitles).pack(anchor="w",padx=6,pady=(1,4))
        # Right settings in a single vertical pane, not hidden in tab pages.
        wrap=tk.Frame(right,bg=paper);wrap.pack(fill="both",expand=True,padx=(4,2),pady=3)
        sc=tk.Scrollbar(wrap,orient="vertical");sc.pack(side="right",fill="y")
        canvas=tk.Canvas(wrap,bg=paper,highlightthickness=0,yscrollcommand=sc.set)
        canvas.pack(side="left",fill="both",expand=True)
        sc.configure(command=canvas.yview)
        form=tk.Frame(canvas,bg=paper)
        fid=canvas.create_window((0,0),window=form,anchor="nw")
        form.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda e:canvas.itemconfigure(fid,width=e.width))
        canvas.bind("<MouseWheel>",lambda e:canvas.yview_scroll(-int(e.delta/120),"units"))
        def section(title):
            tk.Label(form,text=title,bg="#c8e0f6",fg=navy,
                     font=("Segoe UI",10,"bold"),anchor="w",padx=7,pady=3).pack(fill="x",pady=(4,2))
        def choose(var,entries):
            for value,label in entries:
                ttk.Radiobutton(form,text=label,variable=var,value=value).pack(anchor="w",padx=9,pady=1)
        section("▣  Προφίλ ποιότητας")
        choose(self.quality,(("Μέγιστη","Μέγιστη ποιότητα"),("Ισορροπημένη","Ισορροπημένο (προτεινόμενο)"),
                             ("Μικρότερο αρχείο","Μικρότερο αρχείο")))
        section("▣  Ανάλυση εξόδου")
        choose(self.size,(("Πρωτότυπη","Πρωτότυπη"),("1080p","1080p (1920 × 1080)"),
                          ("4K","4K (3840 × 2160)")))
        section("▣  Μορφή εξόδου")
        choose(self.format,(("MP4","MP4 (προτεινόμενο)"),("MKV","MKV")))
        section("♪  Ήχος")
        ttk.Combobox(form,textvariable=self.audio,state="readonly",
                     values=("AAC Stereo","Dolby Digital AC3","Αρχικός ήχος")).pack(fill="x",padx=8,pady=(2,4))
        section("Aa  Υπότιτλοι")
        tk.Label(form,text="Οι SRT / ASS αντιγράφονται ξεχωριστά.",
                 bg=paper,fg="#3d6588",font=("Segoe UI",9),anchor="w").pack(fill="x",padx=8)
        tk.Label(form,text="Μέγεθος / θέση / καθυστέρηση: δεν έχουν υλοποιηθεί ακόμη.",
                 bg=paper,fg="#6b7b87",font=("Segoe UI",8),wraplength=245,
                 justify="left").pack(fill="x",padx=8,pady=(2,4))
        guard=tk.Frame(form,bg="#fff1c1",highlightbackground="#d4ae44",highlightthickness=1)
        guard.pack(fill="x",padx=6,pady=(4,5))
        tk.Label(guard,text="⚠  Smart Quality Guard",bg="#ffdd79",fg="#66450a",
                 font=("Segoe UI",10,"bold"),anchor="w",padx=8,pady=4).pack(fill="x")
        self.quality_description=tk.StringVar()
        self.quality_warning=tk.StringVar()
        tk.Label(guard,textvariable=self.quality_description,bg="#fff1c1",fg="#78540b",
                 font=("Segoe UI",9),wraplength=250,justify="left",padx=7,pady=2).pack(fill="x")
        tk.Label(guard,textvariable=self.quality_warning,bg="#fff1c1",fg="#78540b",
                 font=("Segoe UI",9),wraplength=250,justify="left",padx=7,pady=2).pack(fill="x")
        ttk.Button(form,text="⚙  Προτεινόμενες ρυθμίσεις",
                   command=self.recommended_settings).pack(fill="x",padx=7,pady=(1,3))
        ttk.Button(form,text="↺  Επαναφορά",command=self.recommended_settings).pack(fill="x",padx=7,pady=(0,4))
        section("▣  Φάκελος αποθήκευσης")
        destrow=tk.Frame(form,bg=paper);destrow.pack(fill="x",padx=6,pady=(0,8))
        ttk.Entry(destrow,textvariable=self.output).pack(side="left",fill="x",expand=True,padx=(0,4))
        ttk.Button(destrow,text="…",width=2,command=self.destination).pack(side="right")
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
        if not hasattr(self,"quality_description"):return
        quality_text={"Μέγιστη":"Πιο καθαρή εικόνα • μεγαλύτερο αρχείο.",
                      "Ισορροπημένη":"Προτεινόμενο προφίλ • καλή ισορροπία εικόνας και μεγέθους.",
                      "Μικρότερο αρχείο":"Μικρότερο μέγεθος • πιθανή απώλεια λεπτομέρειας."}
        self.quality_description.set(quality_text.get(self.quality.get(),""))
        warnings=[]
        if self.size.get()=="4K":
            warnings.append("Το 4K απαιτεί πολύ χρόνο και δεν αυξάνει την πραγματική λεπτομέρεια.")
        elif self.size.get()=="1080p":
            warnings.append("Αν η πηγή είναι 720p, η αναβάθμιση σε 1080p δεν προσθέτει λεπτομέρεια.")
        if self.audio.get()=="Dolby Digital AC3":
            warnings.append("Το AC3 δεν δημιουργεί αυθεντικό 5.1 από stereo.")
        if self.format.get()=="MP4" and self.audio.get()=="Αρχικός ήχος":
            warnings.append("Ο αρχικός ήχος ενδέχεται να μην είναι συμβατός με MP4.")
        self.quality_warning.set(" ".join(warnings) if warnings else "Οι ρυθμίσεις είναι κατάλληλες για τυπική αναπαραγωγή.")
    def _selected(self,event=None):
        if not self.items:return
        selected=self.tree.selection()
        if not selected:return
        i=int(selected[0])
        if i>=len(self.items):return
        path=self.items[i]["path"]
        self.current_detail.set(path.name)
        sub=self.sub(path)
        self.subtitle_info.set("Υπότιτλοι: "+sub.name if sub else "Δεν βρέθηκαν εξωτερικοί SRT / ASS")
        if self.preview_enabled:self.preview()
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i,x in enumerate(self.items):
            self.tree.insert("","end",iid=str(i),tags=("odd" if i%2 else "even",),values=(x["path"].name,x.get("duration_text","—"),x.get("resolution","—"),f'{x["pct"]:.0f}%',x["state"]))
        if self.items:self.allpct.set(sum(x["pct"] for x in self.items)/len(self.items))
        if hasattr(self,"queue_summary"):self.queue_summary.set(f"{len(self.items)} ταινίες  ·  {sum(x['state']=='Έτοιμο' for x in self.items)} ολοκληρωμένες")
    def sub(self,p):
        return next((p.with_suffix(ext) for ext in (".srt",".ass",".ssa") if p.with_suffix(ext).is_file()),None)
    def add(self,paths):
        seen={str(x["path"]) for x in self.items}
        for name in paths:
            p=P(name)
            if p.is_file() and p.suffix.lower() in EXT and str(p) not in seen:
                self.items.append(dict(path=p,state="Αναμονή",pct=0));seen.add(str(p))
                index=len(self.items)-1
                def metadata(i=index,filename=p):
                    try:
                        duration,w,h,_=probe(filename)
                        hh=int(duration)//3600;mm=int(duration)%3600//60;ss=int(duration)%60
                        self.events.put(("metadata",i,f"{hh:02d}:{mm:02d}:{ss:02d}",f"{w}×{h}"))
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
    def toggle_preview(self):
        if self.preview_enabled:
            self.disable_preview()
        else:
            if not self.items:
                messagebox.showinfo("Προεπισκόπηση","Πρόσθεσε πρώτα μια ταινία.")
                return
            self.preview_enabled=True
            self.preview_button.configure(text="■ Απενεργοποίηση")
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
        self.preview_button.configure(text="▶ Ενεργοποίηση")
        self.preview_pause_button.configure(state="disabled",text="⏸ Παύση")
        self.preview_state.set("Προεπισκόπηση: κλειστή")
        self.image.configure(image="",text="▶\n\nΠροεπισκόπηση απενεργοποιημένη")
        self.pic=None
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
        def worker():
            proc=None
            try:
                ff=binary("ffmpeg.exe")
                if not ff:raise RuntimeError("Δεν βρέθηκε FFmpeg.")
                # 320x180, 5 fps limits CPU load on older Intel HD 4000 systems.
                cmd=[ff,"-hide_banner","-loglevel","error","-ss","5","-i",str(path),
                     "-an","-vf","fps=5,scale=320:180:force_original_aspect_ratio=decrease,"
                     "pad=320:180:(ow-iw)/2:(oh-ih)/2",
                     "-pix_fmt","rgb24","-f","rawvideo","pipe:1"]
                proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                                      creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                self.preview_proc=proc
                frame_bytes=320*180*3
                while not stop.is_set() and generation==self.preview_generation:
                    if self.preview_pause.is_set():
                        time.sleep(.08)
                        continue
                    frame=proc.stdout.read(frame_bytes)
                    if len(frame)!=frame_bytes:break
                    if self.events.qsize()<8:
                        self.events.put(("preview_frame",generation,frame))
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
        if not self.items:messagebox.showwarning("Προσοχή","Πρόσθεσε ταινίες.");return
        if not binary("ffmpeg.exe") or not binary("ffprobe.exe"):messagebox.showerror("Σφάλμα","Λείπουν τα ενσωματωμένα εργαλεία μετατροπής.");return
        try:
            P(self.output.get()).mkdir(parents=True,exist_ok=True)
            if self.size.get()=="4K" and any(probe(x["path"])[2]<1080 for x in self.items):
                if not messagebox.askyesno("Smart Quality Guard","Το 4K upscaling δεν προσθέτει πραγματική λεπτομέρεια. Συνέχεια;"):return
            if self.audio.get()=="Dolby Digital AC3" and any((probe(x["path"])[3] or {}).get("channels",0)<6 for x in self.items):
                if not messagebox.askyesno("Smart Quality Guard","Μερικές ταινίες δεν έχουν ήχο 5.1. Δεν μπορούμε να δημιουργήσουμε πραγματικό surround. Συνέχεια;"):return
        except Exception as e:messagebox.showerror("Σφάλμα",str(e));return
        self.stopflag=False;self.btn.configure(state="disabled")
        self.worker=threading.Thread(target=self.convert,daemon=True);self.worker.start()
    def stop(self):
        self.stopflag=True
        if self.process and self.process.poll() is None:self.process.terminate()
    def convert(self):
        for i,x in enumerate(self.items):
            if self.stopflag:break
            if x["state"]=="Έτοιμο":continue
            tmp=None
            try:
                source=x["path"];duration,w,h,a=probe(source);x["state"]="Επεξεργασία"
                src_label=f"{w}×{h}" + (f" ({h}p)" if h in (480,576,720,1080,1440,2160) else "")
                dest_label=self.size.get()
                if dest_label=="Πρωτότυπη":dest_label=f"{h}p (χωρίς αλλαγή ανάλυσης)"
                self.events.put(("resolution",i,src_label,dest_label))
                suffix=".mp4" if self.format.get()=="MP4" else ".mkv"
                out=P(self.output.get())/(source.stem+(" (4K)" if self.size.get()=="4K" else " (1080p)" if self.size.get()=="1080p" else "")+suffix)
                if out.resolve()==source.resolve():raise RuntimeError("Η έξοδος συμπίπτει με την πηγή.")
                if out.exists():out=out.with_name(out.stem+"_"+str(int(time.time()))+suffix)
                tmp=out.with_name(out.stem+".partial"+suffix)
                cmd=[binary("ffmpeg.exe"),"-y","-hide_banner","-i",str(source),"-map","0:v:0","-map","0:a:0?","-c:v","libx264","-preset","veryfast","-crf",str({"Μέγιστη":18,"Ισορροπημένη":21,"Μικρότερο αρχείο":25}[self.quality.get()]),"-pix_fmt","yuv420p"]
                size=self.size.get()
                if size!="Πρωτότυπη":
                    width,height=(1920,1080) if size=="1080p" else (3840,2160)
                    cmd+=["-vf",f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"]
                audio=self.audio.get()
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
                sub=self.sub(source)
                if sub and self.copy_subtitles.get():shutil.copy2(sub,out.with_suffix(sub.suffix))
                x["pct"]=100;x["state"]="Έτοιμο"
            except Exception as e:
                x["state"]="Σφάλμα";x["error"]=str(e)
                try:
                    if tmp and tmp.exists():tmp.unlink()
                except OSError:pass
            self.events.put(("refresh",))
        self.events.put(("done",))
    def poll(self):
        try:
            while True:
                event=self.events.get_nowait()
                if event[0]=="preview_frame":
                    _,generation,frame=event
                    if generation==self.preview_generation and self.preview_enabled:
                        from PIL import Image, ImageTk
                        im=Image.frombytes("RGB",(320,180),frame)
                        self.pic=ImageTk.PhotoImage(im)
                        self.image.configure(image=self.pic,text="")
                        if not self.preview_pause.is_set():
                            self.preview_state.set("Προεπισκόπηση: παίζει χωρίς ήχο • 5 FPS")
                elif event[0]=="preview_error":
                    if event[1]==self.preview_generation:self.preview_state.set("Σφάλμα: "+event[2])
                elif event[0]=="preview_end":
                    if event[1]==self.preview_generation and self.preview_enabled:
                        self.preview_state.set("Προεπισκόπηση: τέλος αποσπάσματος")
                elif event[0]=="metadata":
                    _,i,duration_text,resolution=event
                    if 0<=i<len(self.items):
                        self.items[i]["duration_text"]=duration_text
                        self.items[i]["resolution"]=resolution
                        self.refresh()
                elif event[0]=="resolution":
                    _,i,source_label,destination_label=event
                    self.source_progress_label.set(f"Αρχικό βίντεο: {source_label} • Ταινία {i+1}/{len(self.items)}")
                    self.output_progress_label.set(f"Μετατροπή σε {destination_label} • Συνολική πρόοδος")
                elif event[0]=="warn":self.status.set(event[1])
                elif event[0]=="progress":
                    _,i,pct,fps,eta=event
                    self.pct.set(pct);self.status.set(f'Ταινία {i+1}/{len(self.items)}: {self.items[i]["path"].name} — {pct:.1f}%')
                    self.metrics.set(f"Ταχύτητα: {fps:.1f} FPS | Υπόλοιπο: περίπου {eta/60:.0f} λεπτά")
                elif event[0]=="done":
                    self.btn.configure(state="normal")
                    self.status.set(f'Ολοκληρώθηκαν {sum(x["state"]=="Έτοιμο" for x in self.items)}/{len(self.items)} ταινίες')
                if event[0] in ("progress","refresh","done"):self.refresh()
        except queue.Empty:pass
        self.after(100,self.poll)
if __name__=="__main__":
    if "--self-test" in sys.argv:sys.exit(self_test())
    MovieShrink().mainloop()
