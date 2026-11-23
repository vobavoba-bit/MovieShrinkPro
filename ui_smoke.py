"""Regression checks for the compact Windows GUI without invoking FFmpeg."""
import tkinter as tk
from MovieShrinkPro import MovieShrink

app = MovieShrink()
app.withdraw()
app.update_idletasks()
assert app.preview_enabled is False
assert app.copy_subtitles.get() is True
assert app.size.get() == "1080p"
assert app.source_progress_label.get().startswith("Αρχική")
assert "1080p" in app.output_progress_label.get()
app.size.set("4K")
app.update_idletasks()
assert "4K" in app.output_progress_label.get()
app.quality.set("Μέγιστη")
app.recommended_settings()
assert app.size.get() == "1080p" and app.quality.get() == "Ισορροπημένη"
all_widgets = []
def walk(root):
    for child in root.winfo_children():
        all_widgets.append(child)
        walk(child)
walk(app)
button_labels = [str(x.cget("text")) for x in all_widgets
                 if isinstance(x, (tk.Button,)) or x.winfo_class() == "TButton"]
starts = [v for v in button_labels if "ΕΝΑΡΞΗ" in v or "Έναρξη" in v]
stops = [v for v in button_labels if "ΔΙΑΚΟΠΗ" in v]
assert len(starts) == 1, starts
assert len(stops) == 1, stops
assert any("Προεπισκόπηση" in v for v in button_labels)
assert any("Προτεινόμενες" in v for v in button_labels)
app.destroy()
print("MovieShrinkPro compact UI smoke checks passed")
