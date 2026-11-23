"""Test actual SRT-to-ASS size, location and delay controls."""
from pathlib import Path
from tempfile import TemporaryDirectory
from MovieShrinkPro import style_srt_as_ass, read_srt_cues

with TemporaryDirectory() as d:
    srt=Path(d)/"movie.srt"
    ass=Path(d)/"movie.ass"
    srt.write_text("1\n00:00:01,000 --> 00:00:03,000\nΓειά σου!\n\n2\n00:00:04,100 --> 00:00:06,700\nΔεύτερη γραμμή\n",encoding="utf-8")
    cues=read_srt_cues(srt)
    assert len(cues)==2 and cues[0][0]==1.0 and cues[1][1]==6.7, cues
    count=style_srt_as_ass(srt,ass,120,"Πάνω",.5)
    text=ass.read_text(encoding="utf-8-sig")
    assert count==2, count
    assert "Style: Default,Arial,34" in text
    assert ",8,30,30,28,1" in text
    assert "0:00:01.50,0:00:03.50" in text
    assert "0:00:04.60,0:00:07.20" in text
    assert "Γειά σου!" in text
    count=style_srt_as_ass(srt,ass,80,"Κάτω",-3.0)
    text=ass.read_text(encoding="utf-8-sig")
    assert count==2
    assert "0:00:00.00,0:00:00.01" in text
print("SRT/ASS style and timing regression tests passed")
