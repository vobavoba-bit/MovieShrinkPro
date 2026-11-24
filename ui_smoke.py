"""Regression checks for the compact Windows GUI without invoking FFmpeg."""
import tkinter as tk
from MovieShrinkPro import MovieShrink

app = MovieShrink()
app.withdraw()
app.update_idletasks()
assert app.preview_enabled is False
assert app.preview_slider.winfo_class() == "TScale"
assert app.preview_off_button.instate(["disabled"])
assert app.preview_capture_button.instate(["disabled"])
assert not app.preview_button.instate(["disabled"])
assert app.external_subtitles == {}
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
assert app.btn.winfo_reqwidth() >= 210 and app.btn.winfo_reqheight() >= 48
assert app.stop_btn.winfo_reqwidth() >= 210 and app.stop_btn.winfo_reqheight() >= 48
assert len(app.btn._action_images) == 3
assert len(app.stop_btn._action_images) == 3
assert len(app.settings_tabs.tabs()) == 3
assert app.quality_warning.get() == "", "No permanent Quality Guard description"
assert app.smart_guard_enabled.get() is True
assert app.guard_switch.winfo_exists()
app.smart_guard_enabled.set(False)
app.size.set("4K")
app.update_idletasks()
assert app.quality_warning.get()==""
app.smart_guard_enabled.set(True)
app.update_idletasks()
assert "4K" in app.quality_warning.get()
app.recommended_settings()

app.size.set("4K")
app.update_idletasks()
assert "4K" in app.quality_warning.get()
app.recommended_settings()
app.update_idletasks()
assert app.quality_warning.get() == ""

assert app.btn.master == app.action_panel
assert str(app.btn.pack_info()["side"]) == "top"
assert str(app.stop_btn.pack_info()["side"]) == "top"
app.deiconify()
app.geometry("1000x690+5+5")
app.update()
assert app.btn.winfo_rooty() < app.stop_btn.winfo_rooty(), "START must be above STOP"
assert app.stop_btn.winfo_rooty() + app.stop_btn.winfo_height() < app.winfo_rooty() + app.winfo_height(), "STOP must be visible"
assert app.btn.winfo_rootx() == app.stop_btn.winfo_rootx(), "START and STOP must align vertically"
app.withdraw()
assert len(app._styled_button_images) >= 4
assert not any("ΕΝΑΡΞΗ" in v or "ΔΙΑΚΟΠΗ" in v for v in button_labels)

assert any("Παίξε" in v for v in button_labels)
assert any("Κλείσιμο" in v for v in button_labels)
assert any("Προτεινόμενες" in v for v in button_labels)
app.destroy()
print("MovieShrinkPro compact UI smoke checks passed")
