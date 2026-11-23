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
        super().__init__();self.title("MovieShrink Pro — DVD / USB / MP4");self.geometry("1080x720")
        self.items=[];self.events=queue.Queue();self.worker=None;self.process=None;self.stopflag=False
        self.quality=tk.StringVar(value="Ισορροπημένη");self.size=tk.StringVar(value="1080p")
        self.audio=tk.StringVar(value="AAC Stereo");self.format=tk.StringVar(value="MP4")
        self.output=tk.StringVar(value=str(P.home()/"Videos"/"MovieShrinkPro"))
        self.pct=tk.DoubleVar();self.allpct=tk.DoubleVar();self.status=tk.StringVar(value="Έτοιμο")
        self.metrics=tk.StringVar(value="Ταχύτητα: — FPS | Χρόνος: —")
        self.ui();self.after(100,self.poll)
    def ui(self):
        """DVD Shrink-inspired three-column interface, sized for a 13-inch display."""
        bg="#e6edf5"; dark="#071f3c"; navy="#113d6b"; blue="#2069a3"
        pale="#f8fbff"; edge="#b4c9df"; text="#15304a"; gold="#f9c63f"
        self.configure(bg=bg)
        style=ttk.Style(self);style.theme_use("clam")
        style.configure("TFrame",background=bg)
        style.configure("TLabel",background=bg,foreground=text,font=("Segoe UI",9))
        style.configure("TButton",font=("Segoe UI",9,"bold"),padding=(8,6),background="#edf5fd",foreground=navy,bordercolor="#a5bed6")
        style.map("TButton",background=[("active","#d8eaff")])
        style.configure("TCombobox",font=("Segoe UI",9),padding=3)
        style.configure("Treeview",font=("Segoe UI",8),rowheight=26,background="white",fieldbackground="white",foreground=text)
        style.map("Treeview",background=[("selected","#c4e0ff")],foreground=[("selected","#143452")])
        style.configure("Treeview.Heading",background="#d8e7f6",foreground=navy,font=("Segoe UI",8,"bold"),padding=6)
        style.configure("Green.Horizontal.TProgressbar",background="#18ad44",troughcolor="#dce6f1",thickness=12)
        style.configure("Blue.Horizontal.TProgressbar",background="#168be2",troughcolor="#dce6f1",thickness=10)

        header=tk.Frame(self,bg=dark,height=113)
        header.pack(fill="x");header.pack_propagate(False)
        try:
            from PIL import Image,ImageTk
            base=P(getattr(sys,"_MEIPASS",P(__file__).resolve().parent))
            logo=Image.open(base/"assets"/"movieshrink_logo.jpg")
            self.brand_image=ImageTk.PhotoImage(logo.resize((93,93),Image.Resampling.LANCZOS))
            tk.Label(header,image=self.brand_image,bg=dark).pack(side="left",padx=(10,8),pady=9)
        except Exception:
            tk.Label(header,text="◉",font=("Segoe UI",42),fg="#4dc6ff",bg=dark).pack(side="left",padx=14)
        brand=tk.Frame(header,bg=dark);brand.pack(side="left",fill="both",expand=True,pady=15)
        title_line=tk.Frame(brand,bg=dark);title_line.pack(anchor="w")
        tk.Label(title_line,text="MovieShrink",font=("Segoe UI",25,"bold","italic"),
                 fg="#edf7ff",bg=dark).pack(side="left")
        tk.Label(title_line,text=" Pro",font=("Segoe UI",25,"bold","italic"),
                 fg=gold,bg=dark).pack(side="left")
        tk.Label(brand,text="DVD / USB / MP4    •    Μετατροπή σε Full HD 1080p & 4K",
                 font=("Segoe UI",9,"bold"),fg="#9ad2ff",bg=dark).pack(anchor="w")
        flags=tk.Frame(header,bg=dark);flags.pack(side="right",padx=9)
        for name in ("DVD","USB","MP4","1080p","4K"):
            tk.Label(flags,text=name,bg="#17518a",fg=gold if name in ("1080p","4K") else "#ffffff",
                     font=("Segoe UI",9,"bold"),padx=8,pady=6,
                     highlightbackground="#448aca",highlightthickness=1).pack(side="left",padx=2)

        toolbar=tk.Frame(self,bg="#d3e3f3",height=50)
        toolbar.pack(fill="x");toolbar.pack_propagate(False)
        for caption,action in (("◉  Προσθήκη DVD",self.adddvd),
                               ("▣  Προσθήκη φακέλου",self.addfolder),
                               ("▤  Προσθήκη αρχείων",self.addfiles),
                               ("✖  Αφαίρεση",self.remove)):
            ttk.Button(toolbar,text=caption,command=action).pack(side="left",padx=(7,0),pady=7)
        tk.Button(toolbar,text="▶  ΕΝΑΡΞΗ",command=self.start,bg="#168a3b",fg="white",
                  activebackground="#27a64e",activeforeground="white",
                  font=("Segoe UI",10,"bold"),relief="raised",bd=2,padx=17).pack(side="right",padx=10,pady=5)

        content=tk.Frame(self,bg=bg);content.pack(fill="both",expand=True,padx=7,pady=(8,4))
        content.grid_columnconfigure(0,weight=4,minsize=280)
        content.grid_columnconfigure(1,weight=4,minsize=280)
        content.grid_columnconfigure(2,weight=3,minsize=255)
        content.grid_rowconfigure(0,weight=1)

        def card(parent,column,title,weight=1):
            outer=tk.Frame(parent,bg=pale,highlightbackground=edge,highlightthickness=1)
            outer.grid(row=0,column=column,sticky="nsew",padx=4)
            tk.Label(outer,text=title,bg=navy,fg="white",
                     font=("Segoe UI",10,"bold"),anchor="w",padx=8,pady=6).pack(fill="x")
            return outer

        left=card(content,0,"▤  Ουρά επεξεργασίας")
        table=tk.Frame(left,bg="white");table.pack(fill="both",expand=True,padx=5,pady=6)
        self.tree=ttk.Treeview(table,columns=("file","sub","pct","state"),show="headings",selectmode="extended")
        for key,label,width in (("file","Ταινία",160),("sub","SRT",35),
                                ("pct","%",35),("state","Κατάσταση",79)):
            self.tree.heading(key,text=label);self.tree.column(key,width=width,stretch=(key=="file"),minwidth=30)
        sb=ttk.Scrollbar(table,orient="vertical",command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right",fill="y")
        self.tree.pack(side="left",fill="both",expand=True)
        self.tree.bind("<<TreeviewSelect>>",self._selected)
        self.queue_summary=tk.StringVar(value="0 ταινίες σε αναμονή")
        tk.Label(left,textvariable=self.queue_summary,bg=pale,fg="#46637f",anchor="w",
                 font=("Segoe UI",9),padx=7,pady=6).pack(fill="x")

        center=card(content,1,"▣  Προεπισκόπηση ταινίας")
        view=tk.Frame(center,bg="#071524");view.pack(fill="both",expand=True,padx=6,pady=(8,5))
        self.image=tk.Label(view,bg="#071524",fg="#c9deef",text="▶\n\nΠροεπισκόπηση επιλεγμένης ταινίας",
                            font=("Segoe UI",11),justify="center")
        self.image.pack(fill="both",expand=True,padx=3,pady=3)
        tk.Label(center,text="Προεπισκόπηση της αρχικής εικόνας • Όχι τελικό καρέ",
                 bg=pale,fg="#657d93",font=("Segoe UI",8),anchor="w").pack(fill="x",padx=8)
        control=tk.Frame(center,bg=pale);control.pack(fill="x",padx=6,pady=7)
        ttk.Button(control,text="▶ Προεπισκόπηση",command=self.preview).pack(side="left")
        self.current_detail=tk.StringVar(value="Επίλεξε μία ταινία")
        tk.Label(center,textvariable=self.current_detail,wraplength=305,anchor="w",
                 bg=pale,fg="#244c70",font=("Segoe UI",8),justify="left",
                 padx=7,pady=7).pack(fill="x")
        subs=tk.Frame(center,bg="#dcecff",highlightbackground="#bad4ee",highlightthickness=1)
        subs.pack(fill="x",padx=6,pady=(5,8))
        tk.Label(subs,text="Aa  Εξωτερικοί υπότιτλοι",font=("Segoe UI",10,"bold"),
                 bg="#dcecff",fg=navy,anchor="w",padx=7,pady=5).pack(fill="x")
        self.subtitle_info=tk.StringVar(value="SRT / ASS δίπλα στην ταινία · Επιλέξιμοι στον player")
        tk.Label(subs,textvariable=self.subtitle_info,bg="#dcecff",fg="#2d557e",
                 font=("Segoe UI",8),anchor="w",wraplength=320,padx=7,pady=4).pack(fill="x")

        right=card(content,2,"⚙  Ρυθμίσεις εξόδου")
        options=tk.Frame(right,bg=pale);options.pack(fill="x",padx=8,pady=5)
        def group(title,var,values):
            tk.Label(options,text=title,bg=pale,fg=navy,font=("Segoe UI",9,"bold"),
                     anchor="w",pady=5).pack(fill="x")
            ttk.Combobox(options,textvariable=var,values=values,state="readonly").pack(fill="x")
        group("Προφίλ ποιότητας",self.quality,["Μέγιστη","Ισορροπημένη","Μικρότερο αρχείο"])
        group("Ανάλυση εξόδου",self.size,["Πρωτότυπη","1080p","4K"])
        group("Μορφή εξόδου",self.format,["MP4","MKV"])
        group("Ήχος • Stereo / Dolby 5.1",self.audio,["AAC Stereo","Dolby Digital AC3","Αρχικός ήχος"])
        self.quality_warning=tk.StringVar(value="⚠ Το upscaling δεν δημιουργεί πραγματική λεπτομέρεια.")
        tk.Label(options,textvariable=self.quality_warning,bg="#fff0c5",
                 fg="#775000",font=("Segoe UI",8),wraplength=240,justify="left",
                 padx=6,pady=7).pack(fill="x",pady=(10,4))
        tk.Label(options,text="Smart Quality Guard",bg=pale,fg="#1e699f",
                 font=("Segoe UI",9,"bold"),anchor="w").pack(fill="x",pady=(3,0))
        tk.Label(options,text="Προειδοποιήσεις πριν από απώλεια ποιότητας ή αλλαγή ήχου.",
                 bg=pale,fg="#57738b",font=("Segoe UI",8),wraplength=240,justify="left").pack(fill="x",pady=(3,8))

        dest=tk.Frame(right,bg="#e5f0fb",highlightbackground=edge,highlightthickness=1)
        dest.pack(fill="x",padx=8,pady=(0,5))
        tk.Label(dest,text="▣  Προορισμός αρχείου",font=("Segoe UI",9,"bold"),
                 bg="#e5f0fb",fg=navy,anchor="w",padx=6,pady=5).pack(fill="x")
        d=tk.Frame(dest,bg="#e5f0fb");d.pack(fill="x",padx=5,pady=(0,6))
        ttk.Entry(d,textvariable=self.output).pack(side="left",fill="x",expand=True,padx=(0,4))
        ttk.Button(d,text="…",command=self.destination,width=2).pack(side="right")

        bottom=tk.Frame(self,bg="#f7fbff",highlightbackground=edge,highlightthickness=1)
        bottom.pack(fill="x",padx=11,pady=(2,10))
        tk.Label(bottom,text="▥  Πρόοδος μετατροπής",font=("Segoe UI",10,"bold"),
                 bg="#20669e",fg="white",anchor="w",padx=9,pady=5).pack(fill="x")
        control=tk.Frame(bottom,bg="#f7fbff");control.pack(fill="x",padx=9,pady=(8,6))
        track=tk.Frame(control,bg="#f7fbff");track.pack(side="left",fill="both",expand=True)
        tk.Label(track,textvariable=self.status,bg="#f7fbff",fg=navy,
                 font=("Segoe UI",9,"bold"),anchor="w").pack(fill="x")
        ttk.Progressbar(track,variable=self.pct,maximum=100,style="Green.Horizontal.TProgressbar").pack(fill="x",pady=(4,2))
        tk.Label(track,text="Συνολική πρόοδος",font=("Segoe UI",9),
                 bg="#f7fbff",fg=navy,anchor="w").pack(fill="x",pady=(5,0))
        ttk.Progressbar(track,variable=self.allpct,maximum=100,style="Blue.Horizontal.TProgressbar").pack(fill="x",pady=(4,2))
        actions=tk.Frame(control,bg="#f7fbff");actions.pack(side="right",padx=(12,0))
        self.btn=ttk.Button(actions,text="▶  Έναρξη",command=self.start);self.btn.pack(side="left",padx=(0,5),pady=3)
        tk.Button(actions,text="■  Διακοπή",command=self.stop,bg="#bd3540",fg="white",
                  activebackground="#a22a33",font=("Segoe UI",9,"bold"),padx=12,pady=5).pack(side="left",pady=3)
        tk.Label(bottom,textvariable=self.metrics,bg="#f7fbff",fg="#345878",
                 font=("Segoe UI",9),anchor="w").pack(fill="x",padx=9,pady=(0,5))
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
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i,x in enumerate(self.items):
            self.tree.insert("","end",iid=str(i),values=(x["path"].name,"Ναι" if self.sub(x["path"]) else "—",f'{x["pct"]:.0f}%',x["state"]))
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
    def preview(self):
        if not self.items:return
        index=int(self.tree.selection()[0]) if self.tree.selection() else 0
        def worker():
            try:
                with tempfile.TemporaryDirectory() as d:
                    p=P(d)/"frame.png"
                    result=run([binary("ffmpeg.exe"),"-v","error","-y","-ss","10","-i",str(self.items[index]["path"]),"-frames:v","1","-vf","scale=360:-2",str(p)],capture_output=True,timeout=90)
                    if result.returncode:raise RuntimeError("Δεν διαβάζεται η προεπισκόπηση.")
                    self.events.put(("image",base64.b64encode(p.read_bytes()).decode("ascii")))
            except Exception as e:self.events.put(("warn",str(e)))
        threading.Thread(target=worker,daemon=True).start()
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
                if sub:shutil.copy2(sub,out.with_suffix(sub.suffix))
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
                if event[0]=="image":
                    self.pic=tk.PhotoImage(data=event[1]);self.image.configure(image=self.pic,text="")
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
