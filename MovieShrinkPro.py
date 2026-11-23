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
        self.ui();self.after(100,self.poll)
        for v in (self.quality,self.size,self.format,self.audio):v.trace_add("write",self.update_quality_hint)
        self.size.trace_add("write",self.update_progress_target)
        self.update_quality_hint();self.update_progress_target()
        self.protocol("WM_DELETE_WINDOW",self.close_app)
    def ui(self):
        """Compact cinematic Windows 10 interface; functional controls only."""
        bg="#d9e5f2"; navy="#073667"; top="#071a37"; bright="#0e5fa5"
        paper="#eef5fc"; ink="#142f4b"; accent="#f6bd3b"
        self.configure(bg=bg)
        style=ttk.Style(self);style.theme_use("clam")
        style.configure("TFrame",background=bg)
        style.configure("TLabel",background=paper,foreground=ink,font=("Segoe UI",10))
        style.configure("TButton",font=("Segoe UI",10,"bold"),padding=(10,7),
                        background="#e7f0fc",foreground=navy,bordercolor="#88abc9",relief="raised")
        style.map("TButton",background=[("active","#c3dff8"),("pressed","#9fcaf2")])
        style.configure("TEntry",padding=5)
        style.configure("TCombobox",font=("Segoe UI",10),padding=4,fieldbackground="white")
        style.configure("TRadiobutton",background=paper,foreground=ink,font=("Segoe UI",10),padding=(1,3))
        style.map("TRadiobutton",background=[("active","#dbeeff")])
        style.configure("TCheckbutton",background=paper,foreground=ink,font=("Segoe UI",10))
        style.configure("Treeview",background="#f8fbff",fieldbackground="#f8fbff",
                        foreground=ink,rowheight=30,font=("Segoe UI",9))
        style.map("Treeview",background=[("selected","#86c7f9")],
                  foreground=[("selected","#0a2646")])
        style.configure("Treeview.Heading",background="#c9dcf0",foreground=navy,
                        font=("Segoe UI",9,"bold"),padding=6)
        style.configure("Movie.TNotebook",background=paper,borderwidth=0)
        style.configure("Movie.TNotebook.Tab",background="#d0e3f6",foreground=navy,
                        padding=(12,6),font=("Segoe UI",9,"bold"))
        style.map("Movie.TNotebook.Tab",background=[("selected","#f8fbff")])
        style.configure("Green.Horizontal.TProgressbar",background="#15aa3b",troughcolor="#bfd2e7",thickness=15)
        style.configure("Blue.Horizontal.TProgressbar",background="#158edf",troughcolor="#bfd2e7",thickness=13)

        # Logo and blue-gold identity stay visible at common 1366×768 displays.
        header=tk.Frame(self,bg=top,height=95)
        header.pack(fill="x");header.pack_propagate(False)
        try:
            from PIL import Image, ImageTk
            base=P(getattr(sys,"_MEIPASS",P(__file__).resolve().parent))
            logo=Image.open(base/"assets"/"movieshrink_logo.jpg").convert("RGB")
            self.brand_image=ImageTk.PhotoImage(logo.resize((78,78),Image.Resampling.LANCZOS))
            tk.Label(header,image=self.brand_image,bg=top).pack(side="left",padx=(12,8),pady=6)
        except Exception:
            tk.Label(header,text="◉",bg=top,fg="#33b7ff",font=("Segoe UI",35,"bold")).pack(side="left",padx=12)
        brand=tk.Frame(header,bg=top);brand.pack(side="left",fill="both",expand=True,pady=10)
        brandline=tk.Frame(brand,bg=top);brandline.pack(anchor="w")
        tk.Label(brandline,text="MovieShrink",bg=top,fg="#f0f8ff",
                 font=("Segoe UI",24,"bold","italic")).pack(side="left")
        tk.Label(brandline,text=" Pro",bg=top,fg=accent,
                 font=("Segoe UI",24,"bold","italic")).pack(side="left")
        tk.Label(brand,text="DVD  /  USB  /  MP4     •     Full HD 1080p & 4K",
                 bg=top,fg="#a6d8ff",font=("Segoe UI",10,"bold")).pack(anchor="w")
        marks=tk.Frame(header,bg=top);marks.pack(side="right",padx=13)
        for mark in ("DVD","USB","MP4","1080p","4K"):
            tk.Label(marks,text=mark,bg="#15558f",fg=accent if mark in ("1080p","4K") else "white",
                     highlightbackground="#4285be",highlightthickness=1,
                     font=("Segoe UI",10,"bold"),padx=8,pady=7).pack(side="left",padx=3)

        toolbar=tk.Frame(self,bg="#c8dbef",height=53,highlightbackground="#9ebbd6",highlightthickness=1)
        toolbar.pack(fill="x");toolbar.pack_propagate(False)
        for title,func in (("◉  Προσθήκη DVD",self.adddvd),
                           ("▣  Προσθήκη φακέλου / USB",self.addfolder),
                           ("▤  Προσθήκη ταινιών",self.addfiles),
                           ("✖  Αφαίρεση",self.remove)):
            ttk.Button(toolbar,text=title,command=func).pack(side="left",padx=(7,0),pady=7)

        main=tk.Frame(self,bg=bg)
        main.pack(fill="both",expand=True,padx=7,pady=(7,3))
        main.grid_columnconfigure(0,weight=37,minsize=265)
        main.grid_columnconfigure(1,weight=35,minsize=280)
        main.grid_columnconfigure(2,weight=28,minsize=265)
        main.grid_rowconfigure(0,weight=1)
        def panel(col,title):
            outer=tk.Frame(main,bg=paper,highlightbackground="#7da5cc",highlightthickness=1)
            outer.grid(row=0,column=col,sticky="nsew",padx=3)
            tk.Label(outer,text=title,bg=navy,fg="white",anchor="w",
                     font=("Segoe UI",11,"bold"),padx=10,pady=7).pack(fill="x")
            return outer
        left=panel(0,"▤   Ουρά επεξεργασίας")
        middle=panel(1,"▣   Προεπισκόπηση")
        right=panel(2,"⚙   Ρυθμίσεις εξόδου")

        # Queue list with subtle alternating stripes and useful compact status.
        queueframe=tk.Frame(left,bg=paper);queueframe.pack(fill="both",expand=True,padx=5,pady=(6,3))
        self.tree=ttk.Treeview(queueframe,columns=("file","sub","pct","state"),
                               show="headings",selectmode="extended",height=9)
        for key,label,width in (("file","Ταινία",175),("sub","SRT",38),
                                ("pct","%",44),("state","Κατάσταση",96)):
            self.tree.heading(key,text=label)
            self.tree.column(key,width=width,minwidth=30,stretch=(key=="file"))
        scroll=ttk.Scrollbar(queueframe,orient="vertical",command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right",fill="y")
        self.tree.pack(side="left",fill="both",expand=True)
        self.tree.tag_configure("even",background="#fbfdff")
        self.tree.tag_configure("odd",background="#e9f3ff")
        self.tree.bind("<<TreeviewSelect>>",self._selected)
        self.queue_summary=tk.StringVar(value="0 ταινίες στην ουρά")
        tk.Label(left,textvariable=self.queue_summary,bg="#d6e7f7",fg=navy,
                 font=("Segoe UI",9,"bold"),anchor="w",padx=8,pady=5).pack(fill="x",side="bottom")

        # Deliberate non-autoplay low-CPU source video player.
        frame=tk.Frame(middle,bg="#091727",height=212)
        frame.pack(fill="x",padx=7,pady=(7,4));frame.pack_propagate(False)
        self.image=tk.Label(frame,text="▶\n\nΗ προεπισκόπηση είναι κλειστή",
                            bg="#091727",fg="#b4d9f6",font=("Segoe UI",11))
        self.image.pack(fill="both",expand=True,padx=3,pady=3)
        strip=tk.Frame(middle,bg=paper);strip.pack(fill="x",padx=7,pady=(1,4))
        self.preview_button=ttk.Button(strip,text="▶ Προεπισκόπηση",command=self.toggle_preview)
        self.preview_button.pack(side="left")
        self.preview_pause_button=ttk.Button(strip,text="⏸ Παύση",command=self.pause_preview,state="disabled")
        self.preview_pause_button.pack(side="left",padx=(5,0))
        self.preview_state=tk.StringVar(value="Κλειστή • χωρίς χρήση CPU")
        tk.Label(middle,textvariable=self.preview_state,bg=paper,fg="#42749d",
                 font=("Segoe UI",9),anchor="w",padx=8).pack(fill="x")
        self.current_detail=tk.StringVar(value="Επίλεξε μια ταινία")
        tk.Label(middle,textvariable=self.current_detail,bg=paper,fg=ink,anchor="w",
                 font=("Segoe UI",9,"bold"),wraplength=320,justify="left",padx=8,pady=3).pack(fill="x")
        subtitles=tk.Frame(middle,bg="#d2e6fb",highlightbackground="#94b9dc",highlightthickness=1)
        subtitles.pack(fill="x",padx=7,pady=(5,6))
        tk.Label(subtitles,text="Aa  Εξωτερικοί υπότιτλοι SRT / ASS",
                 bg="#d2e6fb",fg=navy,font=("Segoe UI",10,"bold"),
                 anchor="w",padx=8,pady=5).pack(fill="x")
        self.subtitle_info=tk.StringVar(value="Αναζήτηση δίπλα στην ταινία")
        tk.Label(subtitles,textvariable=self.subtitle_info,bg="#d2e6fb",fg="#2c567d",
                 font=("Segoe UI",9),wraplength=335,justify="left",
                 anchor="w",padx=8,pady=4).pack(fill="x")
        self.copy_subtitles=tk.BooleanVar(value=True)
        ttk.Checkbutton(subtitles,text="Αντιγραφή εξωτερικών υποτίτλων",
                        variable=self.copy_subtitles).pack(anchor="w",padx=7,pady=(1,5))

        # Right panel is a genuine notebook to keep every control readable on 13-inch screens.
        tabs=ttk.Notebook(right,style="Movie.TNotebook")
        tabs.pack(fill="both",expand=True,padx=7,pady=(7,3))
        picture=tk.Frame(tabs,bg=paper)
        audio_tab=tk.Frame(tabs,bg=paper)
        tabs.add(picture,text="Εικόνα & μορφή")
        tabs.add(audio_tab,text="Ήχος & πληροφορίες")
        def group(label):
            tk.Label(picture,text=label,bg="#d5e8fa",fg=navy,
                     font=("Segoe UI",10,"bold"),anchor="w",padx=6,pady=3).pack(fill="x",pady=(5,2))
        group("▣  Προφίλ ποιότητας")
        for value,label in (("Μέγιστη","Μέγιστη ποιότητα • μεγάλο αρχείο"),
                            ("Ισορροπημένη","Ισορροπημένο • προτεινόμενο"),
                            ("Μικρότερο αρχείο","Μικρότερο αρχείο")):
            ttk.Radiobutton(picture,text=label,value=value,variable=self.quality).pack(anchor="w",padx=8)
        group("▣  Ανάλυση εξόδου")
        for value,label in (("Πρωτότυπη","Πρωτότυπη ανάλυση"),
                            ("1080p","1080p • Full HD"),
                            ("4K","4K • υψηλός χρόνος")):
            ttk.Radiobutton(picture,text=label,value=value,variable=self.size).pack(anchor="w",padx=8)
        group("▣  Μορφή εξόδου")
        for value,label in (("MP4","MP4 • συμβατό"),
                            ("MKV","MKV • περισσότερες δυνατότητες")):
            ttk.Radiobutton(picture,text=label,value=value,variable=self.format).pack(anchor="w",padx=8)
        ttk.Button(picture,text="✓ Προτεινόμενες ρυθμίσεις",
                   command=self.recommended_settings).pack(fill="x",padx=7,pady=(8,5))
        tk.Label(audio_tab,text="♪  Ρύθμιση ήχου",bg="#d5e8fa",fg=navy,
                 font=("Segoe UI",10,"bold"),anchor="w",padx=7,pady=5).pack(fill="x",pady=(5,6))
        for value,label in (("AAC Stereo","AAC Stereo • συμβατό με Mi Box S"),
                            ("Dolby Digital AC3","Dolby Digital AC3"),
                            ("Αρχικός ήχος","Διατήρηση αρχικού ήχου")):
            ttk.Radiobutton(audio_tab,text=label,value=value,variable=self.audio).pack(anchor="w",padx=10,pady=3)
        tk.Label(audio_tab,text="Οι εξωτερικοί υπότιτλοι διατηρούνται σε ξεχωριστό αρχείο.",
                 bg=paper,fg="#385e82",font=("Segoe UI",9),
                 wraplength=250,justify="left",padx=8,pady=12).pack(fill="x")
        ttk.Button(audio_tab,text="↺ Επαναφορά προτεινόμενων",
                   command=self.recommended_settings).pack(fill="x",padx=8,pady=8)
        # Compact, dynamic Quality Guard under tabs.
        guard=tk.Frame(right,bg="#fff0bf",highlightbackground="#deb74b",highlightthickness=1)
        guard.pack(fill="x",padx=7,pady=(2,5))
        tk.Label(guard,text="⚠  Smart Quality Guard",bg="#ffe39b",fg="#634800",
                 anchor="w",font=("Segoe UI",10,"bold"),padx=8,pady=4).pack(fill="x")
        self.quality_description=tk.StringVar()
        self.quality_warning=tk.StringVar()
        tk.Label(guard,textvariable=self.quality_description,bg="#fff0bf",fg="#77540d",
                 font=("Segoe UI",9),anchor="w",wraplength=270,justify="left",
                 padx=8,pady=2).pack(fill="x")
        tk.Label(guard,textvariable=self.quality_warning,bg="#fff0bf",fg="#77540d",
                 font=("Segoe UI",9),anchor="w",wraplength=270,justify="left",
                 padx=8,pady=3).pack(fill="x")
        dest=tk.Frame(right,bg="#d2e5f8",highlightbackground="#91b5d7",highlightthickness=1)
        dest.pack(fill="x",padx=7,pady=(1,6))
        tk.Label(dest,text="▣  Φάκελος αποθήκευσης",bg="#d2e5f8",fg=navy,
                 anchor="w",font=("Segoe UI",9,"bold"),padx=7,pady=4).pack(fill="x")
        destrow=tk.Frame(dest,bg="#d2e5f8")
        destrow.pack(fill="x",padx=6,pady=(0,6))
        ttk.Entry(destrow,textvariable=self.output).pack(side="left",fill="x",expand=True,padx=(0,4))
        ttk.Button(destrow,text="…",width=2,command=self.destination).pack(side="right")

        bottom=tk.Frame(self,bg=paper,highlightbackground="#7da5cc",highlightthickness=1)
        bottom.pack(fill="x",padx=10,pady=(2,9))
        tk.Label(bottom,text="▥   Πρόοδος μετατροπής",bg=navy,fg="white",anchor="w",
                 font=("Segoe UI",11,"bold"),padx=10,pady=6).pack(fill="x")
        body=tk.Frame(bottom,bg=paper);body.pack(fill="x",padx=10,pady=(6,1))
        bars=tk.Frame(body,bg=paper);bars.pack(side="left",fill="both",expand=True)
        tk.Label(bars,textvariable=self.source_progress_label,bg=paper,fg=navy,
                 anchor="w",font=("Segoe UI",10,"bold")).pack(fill="x")
        ttk.Progressbar(bars,variable=self.pct,maximum=100,
                        style="Green.Horizontal.TProgressbar").pack(fill="x",pady=(3,4))
        tk.Label(bars,textvariable=self.output_progress_label,bg=paper,fg=navy,
                 anchor="w",font=("Segoe UI",10,"bold")).pack(fill="x")
        ttk.Progressbar(bars,variable=self.allpct,maximum=100,
                        style="Blue.Horizontal.TProgressbar").pack(fill="x",pady=(3,3))
        commands=tk.Frame(body,bg=paper);commands.pack(side="right",padx=(14,0),pady=9)
        self.btn=tk.Button(commands,text="▶  ΕΝΑΡΞΗ",command=self.start,
                           bg="#0e9336",fg="white",activebackground="#21b64b",
                           activeforeground="white",disabledforeground="#d0dcd2",
                           font=("Segoe UI",12,"bold"),padx=17,pady=10,
                           relief="raised",bd=2,cursor="hand2")
        self.btn.pack(side="left",padx=(0,7))
        tk.Button(commands,text="■  ΔΙΑΚΟΠΗ",command=self.stop,
                  bg="#c32833",fg="white",activebackground="#9b1722",
                  activeforeground="white",font=("Segoe UI",12,"bold"),
                  padx=15,pady=10,relief="raised",bd=2,cursor="hand2").pack(side="left")
        tk.Label(bottom,textvariable=self.status,bg=paper,fg="#335d81",
                 anchor="w",font=("Segoe UI",9)).pack(fill="x",padx=10,pady=(2,0))
        tk.Label(bottom,textvariable=self.metrics,bg=paper,fg="#315d82",
                 anchor="w",font=("Segoe UI",9,"bold")).pack(fill="x",padx=10,pady=(1,6))
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
            self.tree.insert("","end",iid=str(i),tags=("odd" if i%2 else "even",),values=(x["path"].name,"Ναι" if self.sub(x["path"]) else "—",f'{x["pct"]:.0f}%',x["state"]))
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
