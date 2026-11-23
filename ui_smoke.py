"""Regression checks for the compact Windows GUI without invoking FFmpeg."""
import tkinter as tk
from MovieShrinkPro import MovieShrink

app = MovieShrink()
app.withdraw()
app.update_idletasks()
assert app.preview_enabled is False
assert app.preview_slider.winfo_class() == "TScale"
assert app.clock_string(3661) == "01:01:01"
assert app.preview_position.get() == 0
assert app.preview_box.winfo_exists()
app.preview_seek=7.0
app.preview_duration=100.0
app.preview_clock.set("00:07 / 01:40")
assert app.preview_clock.get() == "00:07 / 01:40"
assert len(app._styled_button_images)>=16
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
assert app.btn.winfo_class() == "Button"
assert app.stop_btn.winfo_class() == "Button"
assert app.btn.cget("image") != ""
assert app.stop_btn.cget("image") != ""
assert app.btn.winfo_manager() == "pack"
assert app.stop_btn.winfo_manager() == "pack"
assert app.btn.master == app.stop_btn.master
assert len(app._styled_button_images) >= 4
assert not any("ΕΝΑΡΞΗ" in v or "ΔΙΑΚΟΠΗ" in v for v in button_labels)

assert any("Προεπισκόπηση" in v for v in button_labels)
assert any("Προτεινόμενες" in v for v in button_labels)
app.destroy()
print("MovieShrinkPro compact UI smoke checks passed")
