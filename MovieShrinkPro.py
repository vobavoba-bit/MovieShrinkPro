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
        bar=tk.Frame(self,bg="#123b68");bar.pack(fill="x")
        tk.Label(bar,text="🎬 MovieShrink Pro",bg="#123b68",fg="white",font=("Segoe UI",23,"bold")).pack(anchor="w",padx=14,pady=7)
        tk.Label(bar,text="Δωρεάν μετατροπή • 1080p / 4K • Ουρά • Υπότιτλοι • Smart Quality Guard",bg="#123b68",fg="#d8ecff").pack(anchor="w",padx=15,pady=(0,10))
        toolbar=ttk.Frame(self,padding=8);toolbar.pack(fill="x")
        for title,action in (("Προσθήκη ταινιών",self.addfiles),("Φάκελος / USB",self.addfolder),("DVD VIDEO_TS",self.adddvd),("Αφαίρεση",self.remove)):
            ttk.Button(toolbar,text=title,command=action).pack(side="left",padx=4)
        split=ttk.Panedwindow(self,orient="horizontal");split.pack(fill="both",expand=True,padx=10)
        left=ttk.LabelFrame(split,text="Ουρά ταινιών",padding=6);split.add(left,weight=5)
        self.tree=ttk.Treeview(left,columns=("file","sub","pct","state"),show="headings")
        for c,t,w in (("file","Ταινία",245),("sub","SRT",50),("pct","%",55),("state","Κατάσταση",110)):
            self.tree.heading(c,text=t);self.tree.column(c,width=w)
        self.tree.pack(fill="both",expand=True)
        right=ttk.Frame(split,padding=6);split.add(right,weight=4)
        preview=ttk.LabelFrame(right,text="Προεπισκόπηση αρχικής εικόνας",padding=7);preview.pack(fill="x")
        self.image=tk.Label(preview,bg="#112139",fg="white",text="Προεπισκόπηση καρέ",height=10)
        self.image.pack(fill="x")
        ttk.Button(preview,text="Δες επιλεγμένη ταινία",command=self.preview).pack(anchor="e")
        settings=ttk.LabelFrame(right,text="Ρυθμίσεις ποιότητας και ήχου",padding=8);settings.pack(fill="x",pady=8)
        for label,var,options in (("Ανάλυση",self.size,["Πρωτότυπη","1080p","4K"]),
                                  ("Ποιότητα",self.quality,["Μέγιστη","Ισορροπημένη","Μικρότερο αρχείο"]),
                                  ("Έξοδος",self.format,["MP4","MKV"]),
                                  ("Ήχος",self.audio,["AAC Stereo","Dolby Digital AC3","Αρχικός ήχος"])):
            ttk.Label(settings,text=label).pack(anchor="w")
            ttk.Combobox(settings,textvariable=var,values=options,state="readonly").pack(fill="x",pady=(0,5))
        dest=ttk.LabelFrame(right,text="Φάκελος αποθήκευσης",padding=7);dest.pack(fill="x")
        ttk.Entry(dest,textvariable=self.output).pack(fill="x")
        ttk.Button(dest,text="Επιλογή φακέλου",command=self.destination).pack(anchor="e")
        bottom=ttk.Frame(self,padding=10);bottom.pack(fill="x")
        ttk.Label(bottom,textvariable=self.status).pack(anchor="w")
        ttk.Progressbar(bottom,variable=self.pct,maximum=100).pack(fill="x",pady=4)
        ttk.Label(bottom,textvariable=self.metrics).pack(anchor="w")
        ttk.Label(bottom,text="Συνολική πρόοδος").pack(anchor="w")
        ttk.Progressbar(bottom,variable=self.allpct,maximum=100).pack(fill="x",pady=4)
        buttons=ttk.Frame(bottom);buttons.pack(fill="x",pady=4)
        self.btn=ttk.Button(buttons,text="▶ Έναρξη",command=self.start);self.btn.pack(side="right",padx=5)
        ttk.Button(buttons,text="■ Διακοπή",command=self.stop).pack(side="right")
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i,x in enumerate(self.items):
            self.tree.insert("","end",iid=str(i),values=(x["path"].name,"Ναι" if self.sub(x["path"]) else "—",f'{x["pct"]:.0f}%',x["state"]))
        if self.items:self.allpct.set(sum(x["pct"] for x in self.items)/len(self.items))
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
