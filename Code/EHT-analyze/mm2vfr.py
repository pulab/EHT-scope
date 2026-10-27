#!/usr/bin/env python3
"""
mm2vfr.py - Build correctly timed videos from Micro-Manager acquisitions,
using each frame's recorded time: TimeReceivedByCore (when Micro-Manager
received the frame from the camera), or ElapsedTime-ms if that is missing.

One video is written per acquisition:
  * <name>.mp4  (default) variable frame rate. Each frame is shown at its
                recorded time, so dropped frames appear as a brief hold on
                the previous frame instead of a jump.
  * <name>.avi  (with --avi) constant frame rate (2x the camera rate). Every
                recorded frame is shown, placed on the tick nearest its
                recorded time. For players or journals that require .avi.

Each frame is overlaid with a scale bar, the recorded time of the frame and,
for EHT-scope folder names (<name>_<well>_<bpm>), the well and pacing rate.

Works with Micro-Manager 1.4 and 2.0 data saved either as
  * "Separate image files": a folder of single TIFFs + metadata.txt, or
  * "Image stack file":     MMStack_*.ome.tif (+ optional metadata.txt).

Requirements (one time):
    pip install numpy tifffile pillow av

Usage:
    python mm2vfr.py "path/to/acquisition_folder"
    python mm2vfr.py "path/to/folder_of_acquisitions" -o videos
    python mm2vfr.py "path/to/acquisition_folder" --speed 0.5
    python mm2vfr.py "path/to/acquisition_folder" --avi

The input can be one acquisition folder (or its Pos0 subfolder) or a folder
containing several acquisitions; every acquisition found is converted.

Options:
    -o / --output-dir  Output folder (default: next to each acquisition folder)
    --speed         Playback speed relative to real time (default 1.0;
                    0.5 = half speed, 2 = double speed)
    --range LO HI   Fixed intensity range mapped to black/white. Default:
                    8-bit images are left unchanged; other bit depths use the
                    0.1st-99.9th percentile over sampled frames (the same for
                    every frame, so there is no flicker)
    --crf           x264 quality, lower = better/larger (default 20)
    --px-per-mm     Camera calibration for the scale bar (default 67, as in
                    EHT_config.m pixel_size)
    --bar-mm        Scale bar length in mm (default 1)
    --no-overlay    Do not draw scale bar, timer or label
    --avi           Write a constant frame rate .avi instead of the .mp4
    --time-key      Metadata key holding the frame time (default auto:
                    TimeReceivedByCore, else ElapsedTime-ms)
    --channel / --slice   Which channel / z index to use (default 0 / 0)
    --report-only   Print frame-timing / dropped-frame report, write no video
"""

import argparse
import glob
import json
import os
import re
import sys
from fractions import Fraction
from datetime import datetime
from functools import lru_cache

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont

try:
    import av
except ImportError:
    av = None


# --------------------------------------------------------------------------
# Metadata
# --------------------------------------------------------------------------

@lru_cache(maxsize=8)
def load_metadata_txt(path):
    """Load Micro-Manager metadata.txt, tolerating a file cut off mid-write
    (happens when an acquisition is stopped or crashes)."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Truncated: keep everything up to the last complete top-level entry.
    ends = [m.start() for m in re.finditer(r"\}\s*,", text)]
    for pos in reversed(ends[-200:]):
        try:
            md = json.loads(text[: pos + 1] + "\n}")
            print("WARNING: metadata.txt was incomplete; using the frames "
                  "recorded before it was cut off.")
            return md
        except json.JSONDecodeError:
            continue
    raise ValueError(f"Could not parse {path}")


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _index(entry, names, default=0):
    for n in names:
        if n in entry and _num(entry[n]) is not None:
            return int(float(entry[n]))
    return default


CLOCK_KEY = "TimeReceivedByCore"


def _clock_ms(v):
    """'2025-10-23 12:48:15.271382' -> ms on a fixed (arbitrary) origin."""
    if not isinstance(v, str):
        return None
    m = re.match(r"\s*(\d{4}-\d\d-\d\d)[ T](\d\d:\d\d:\d\d(?:\.\d+)?)", v)
    if not m:
        return None
    clock = m.group(2)[:15]                  # strptime takes at most 6 decimals
    fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in clock else "%Y-%m-%d %H:%M:%S"
    try:
        dt = datetime.strptime(f"{m.group(1)} {clock}", fmt)
    except ValueError:
        return None
    return (dt - datetime(1970, 1, 1)).total_seconds() * 1000.0


def _time_ms(entry, key):
    return _clock_ms(entry.get(key)) if key == CLOCK_KEY else _num(entry.get(key))


def time_keys(time_key):
    return [CLOCK_KEY, "ElapsedTime-ms"] if time_key == "auto" else [time_key]


def choose_time(entries, time_key):
    """Set t_ms on each entry and return (entries that have it, key used).
    'auto' uses TimeReceivedByCore (when Micro-Manager received the frame from
    the camera) if every frame has it, otherwise ElapsedTime-ms. One key is used
    for the whole acquisition so the two clocks are never mixed."""
    keys = time_keys(time_key)
    key = next((k for k in keys
                if entries and all(e["times"].get(k) is not None for e in entries)),
               keys[-1])
    out = [e for e in entries if e["times"].get(key) is not None]
    for e in out:
        e["t_ms"] = e["times"][key]
    return out, key


def frame_entries_from_metadata(md, time_key):
    """Return a list of dicts: {times, frame, channel, slice, position, file};
    times holds each candidate timestamp (ms), see choose_time()."""
    out = []
    for key, entry in md.items():
        if not isinstance(entry, dict) or key == "Summary":
            continue
        times = {k: _time_ms(entry, k) for k in time_keys(time_key)}
        if all(t is None for t in times.values()):
            continue
        frame = _index(entry, ["Frame", "FrameIndex", "TimeIndex"], None)
        if frame is None:                       # MM 1.4 key: FrameKey-t-c-z
            m = re.match(r"FrameKey-(\d+)-(\d+)-(\d+)", key)
            frame = int(m.group(1)) if m else len(out)
        fname = entry.get("FileName")
        if fname:
            fname = fname.replace("\\", "/").split("/")[-1]
        out.append(dict(
            times=times,
            frame=frame,
            channel=_index(entry, ["ChannelIndex"]),
            slice=_index(entry, ["SliceIndex", "ZIndex"]),
            position=_index(entry, ["PositionIndex"]),
            file=fname,
        ))
    return out


# --------------------------------------------------------------------------
# Frame sources
# --------------------------------------------------------------------------

def find_metadata_txt(folder):
    hits = sorted(glob.glob(os.path.join(folder, "*metadata*.txt")))
    return hits[0] if hits else None


def find_stack_files(folder):
    files = sorted(glob.glob(os.path.join(folder, "*.ome.tif")) +
                   glob.glob(os.path.join(folder, "*.ome.tiff")))
    if not files:
        files = sorted(f for f in glob.glob(os.path.join(folder, "*MMStack*.tif*")))
    # MMStack_Pos0.ome.tif, MMStack_Pos0_1.ome.tif, ... in acquisition order
    def k(p):
        m = re.search(r"_(\d+)\.ome\.tiff?$", os.path.basename(p))
        return (re.sub(r"_\d+(\.ome\.tiff?)$", r"\1", os.path.basename(p)),
                int(m.group(1)) if m else 0)
    return sorted(files, key=k)


def find_acquisitions(root):
    """Folders under root (or root itself) holding a Micro-Manager acquisition.
    Template folders written by EHT_motion_tracker.m are skipped."""
    found = []
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d.lower() != "templates")
        if find_metadata_txt(dirpath) or find_stack_files(dirpath):
            found.append(dirpath)
    return found


def acquisition_name(folder):
    """Pos0 takes the name of the acquisition folder; Pos1, Pos2, ... get the
    position appended so they do not overwrite each other."""
    base = os.path.basename(os.path.normpath(folder))
    m = re.fullmatch(r"Pos(\d+)", base)
    if m:
        acq = os.path.basename(os.path.dirname(os.path.normpath(folder)))
        return acq if m.group(1) == "0" else f"{acq}_{base}"
    return base


def stack_pages(stack_files, time_key):
    """Yield (path, page index, per-page metadata dict or None) for every page."""
    for path in stack_files:
        with tifffile.TiffFile(path) as tf:
            for page in tf.pages:
                tag = page.tags.get(51123)          # MicroManagerMetadata
                md = None
                if tag is not None:
                    v = tag.value
                    if isinstance(v, (bytes, str)):
                        try:
                            v = json.loads(v)
                        except Exception:
                            v = None
                    md = v if isinstance(v, dict) else None
                yield path, page.index, md


def planned_frames(folder):
    """Frame count requested by the acquisition, from the metadata Summary."""
    md_path = find_metadata_txt(folder)
    if not md_path:
        return None
    summary = load_metadata_txt(md_path).get("Summary", {})
    n = _num(summary.get("Frames"))
    return int(n) if n else None


def collect_frames(folder, args):
    """Return (frames, source, n_saved): frames is a list of (t_ms, loader) where
    loader() -> 2D ndarray; n_saved is the number of images saved on disk."""
    md_path = find_metadata_txt(folder)
    md_entries = []
    if md_path:
        md_entries = frame_entries_from_metadata(load_metadata_txt(md_path), args.time_key)

    def keep(e):
        return e["channel"] == args.channel and e["slice"] == args.slice

    # 1) Separate image files
    stacks = find_stack_files(folder)
    stack_names = {os.path.basename(f) for f in stacks}
    sep = [e for e in md_entries if e["file"] and keep(e)
           and e["file"] not in stack_names
           and os.path.exists(os.path.join(folder, e["file"]))]
    if sep:
        sep, key = choose_time(sep, args.time_key)
        n_tif = len(glob.glob(os.path.join(folder, "*.tif")))
        single = (len({e["channel"] for e in md_entries}) == 1
                  and len({e["slice"] for e in md_entries}) == 1)
        if single and n_tif > len(sep):
            print(f"WARNING: {n_tif - len(sep)} of {n_tif} TIFFs have no entry in "
                  f"{os.path.basename(md_path)} and are not used.")
        sep.sort(key=lambda e: (e["frame"], e["t_ms"]))
        return ([(e["t_ms"], (lambda p=os.path.join(folder, e["file"]): tifffile.imread(p)))
                 for e in sep], f"separate TIFFs + {os.path.basename(md_path)}, times: {key}",
                max(n_tif, len(sep)) if single else len(sep))

    # 2) Stack files
    if not stacks:
        raise SystemExit(f"No Micro-Manager TIFFs found in {folder}")

    pages = list(stack_pages(stacks, args.time_key))
    per_page = []
    for path, idx, md in pages:
        ents = frame_entries_from_metadata({"x": md}, args.time_key) if md else []
        if not ents:
            per_page = None
            break
        if keep(ents[0]):
            per_page.append((ents[0], path, idx))
    if per_page:
        ents, key = choose_time([e for e, _, _ in per_page], args.time_key)
        per_page = [x for x in per_page if "t_ms" in x[0]]
        per_page.sort(key=lambda x: (x[0]["frame"], x[0]["t_ms"]))
        frames = [(e["t_ms"], (lambda p=p, i=i: tifffile.imread(p, key=i)))
                  for e, p, i in per_page]
        return (frames, f"{len(stacks)} stack file(s), per-frame embedded metadata, "
                f"times: {key}", len(pages))

    # Stack without usable per-page tags: pair pages with metadata.txt in order
    if not md_entries:
        raise SystemExit("Stack has no per-frame metadata and no metadata.txt was found.")
    ents, key = choose_time([e for e in md_entries if keep(e)], args.time_key)
    ents.sort(key=lambda e: (e["frame"], e["t_ms"]))
    n_ch = len({e["channel"] for e in md_entries}) or 1
    n_z = len({e["slice"] for e in md_entries}) or 1
    if n_ch * n_z != 1:
        raise SystemExit("Multi-channel/z stack without embedded per-page metadata "
                         "is not supported; please re-save with metadata.")
    n = min(len(ents), len(pages))
    if len(ents) != len(pages):
        print(f"WARNING: {len(pages)} images but {len(ents)} metadata entries; "
              f"using the first {n}.")
    frames = [(ents[i]["t_ms"], (lambda p=pages[i][0], k=pages[i][1]: tifffile.imread(p, key=k)))
              for i in range(n)]
    return (frames, f"{len(stacks)} stack file(s) + {os.path.basename(md_path)}, times: {key}",
            len(pages))


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def gap_threshold(d):
    """Intervals longer than this (ms) follow one or more dropped frames.
    Repeated timestamps (d <= 0) are ignored."""
    d = d[d > 0]
    return 1.75 * float(np.median(d)) if len(d) else np.inf


def nominal_interval(times_ms):
    """Camera frame interval (ms): the mean of the intervals without dropped
    frames. Saved times are rounded to the 15.6 ms Windows clock, so at 30 fps
    single intervals are saved as 31 or 47 ms; their mean is the true 33.3 ms."""
    d = np.diff(np.asarray(times_ms, float))
    d = d[(d > 0) & (d <= gap_threshold(d))]
    return float(np.mean(d)) if len(d) else 1000.0 / 30


def timing_report(times_ms, planned=None, n_saved=None):
    """planned: number of frames the acquisition asked for (metadata Summary);
    n_saved: number of images on disk. Used for the dropped-frame count."""
    t = np.asarray(times_ms, float)
    d = np.diff(t)
    if len(d) == 0:
        return "Only one frame."
    nominal = nominal_interval(t)
    gaps = d > gap_threshold(d)
    dur = (t[-1] - t[0]) / 1000.0
    lines = [
        f"Frames:               {len(t)}",
        f"Duration:             {dur:.3f} s",
        f"Frame interval:       {nominal:.2f} ms  ({1000/nominal:.2f} fps)",
        f"Interval min / max:   {d.min():.2f} / {d.max():.2f} ms",
        f"Gaps after drops:     {int(gaps.sum())}",
    ]
    n_saved = max(n_saved or 0, len(t))
    if planned and planned >= n_saved:
        dropped = planned - n_saved
        lines.append(f"Dropped frames:       {dropped} of {planned} planned "
                     f"({100*dropped/planned:.1f}%)")
    else:
        est_dropped = int(np.sum(np.round(d[gaps] / nominal) - 1))
        lines.append(f"Est. dropped frames:  {est_dropped}  "
                     f"({100*est_dropped/(len(t)+est_dropped):.1f}% of expected)")
    if gaps.any():
        idx = np.where(gaps)[0]
        show = ", ".join(f"{(t[i+1]-t[0])/1000:.3f}s (+{d[i]:.0f} ms)" for i in idx[:10])
        lines.append(f"First gaps at:        {show}" + (" ..." if len(idx) > 10 else ""))
    if np.any(d <= 0):
        lines.append(f"WARNING: {int(np.sum(d <= 0))} non-increasing timestamps "
                     "(these frames will be nudged 1 ms later).")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Image conversion and overlay
# --------------------------------------------------------------------------

def to_gray8(img, lo, hi):
    img = np.asarray(img)
    if img.ndim == 3 and img.shape[-1] in (3, 4):        # RGB(A) -> luminance
        img = img[..., :3].astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    elif img.ndim > 2:
        img = np.squeeze(img)
        if img.ndim > 2:
            raise SystemExit(f"Expected one 2D image per frame, got shape {img.shape}")
    if lo is None:
        return img.astype(np.uint8)
    x = (img.astype(np.float32) - lo) * (255.0 / max(hi - lo, 1e-6))
    return np.clip(x + 0.5, 0, 255).astype(np.uint8)


def auto_range(frames, n_sample=50):
    idx = np.linspace(0, len(frames) - 1, min(n_sample, len(frames))).astype(int)
    vals = np.concatenate([np.asarray(frames[i][1]()).ravel()[::7] for i in idx])
    lo, hi = np.percentile(vals, [0.1, 99.9])
    if hi <= lo:
        hi = lo + 1
    return float(lo), float(hi)


def eht_label(name):
    """'Acquire-EHT_C1_60' -> 'Well C1 | paced 60 bpm'; other names unchanged."""
    m = re.match(r"^(?:.+_)?([A-Za-z]+\d+)_(\d+)$", name)
    if not m:
        return name
    well, bpm = m.group(1).upper(), int(m.group(2))
    return f"Well {well} | " + ("unpaced" if bpm == 0 else f"paced {bpm} bpm")


def load_font(size):
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)          # Pillow >= 10.1
    except TypeError:
        raise SystemExit("No TrueType font found; install Arial or DejaVu fonts, "
                         "or upgrade Pillow (pip install -U pillow).")


class Overlay:
    """Scale bar (top right), recorded time (top left), label (bottom left)."""

    def __init__(self, w, label, px_per_mm, bar_mm):
        self.font = load_font(max(14, w // 20))
        self.label = label
        self.bar_px = round(bar_mm * px_per_mm)
        self.bar_txt = f"{bar_mm:g} mm"

    def _boxed_text(self, d, xy, text, pad, anchor):
        x0, y0, x1, y1 = d.textbbox(xy, text, font=self.font, anchor=anchor)
        d.rectangle([x0 - pad, y0 - pad, x1 + pad, y1 + pad], fill=0)
        d.text(xy, text, fill=255, font=self.font, anchor=anchor)

    def draw(self, g, t_s):
        h, w = g.shape
        im = Image.fromarray(g)
        d = ImageDraw.Draw(im)
        m = max(12, w // 30)
        pad = max(4, w // 80)

        self._boxed_text(d, (m, m), f"t = {t_s:5.2f} s", pad, "lt")
        if self.label:
            self._boxed_text(d, (m, h - m), self.label, pad, "lb")

        bar_h = max(5, h // 120)
        x1, y0 = w - m, m
        x0 = x1 - self.bar_px
        txt_xy = ((x0 + x1) / 2, y0 + bar_h + pad)
        tx0, _, tx1, ty1 = d.textbbox(txt_xy, self.bar_txt, font=self.font, anchor="mt")
        d.rectangle([min(x0, tx0) - pad, y0 - pad, max(x1, tx1) + pad, ty1 + pad], fill=0)
        d.rectangle([x0, y0, x1 - 1, y0 + bar_h - 1], fill=255)
        d.text(txt_xy, self.bar_txt, fill=255, font=self.font, anchor="mt")
        return np.asarray(im)


# --------------------------------------------------------------------------
# Encoding
# --------------------------------------------------------------------------

def rendered_frames(frames, lo, hi, overlay):
    """Yield (t_ms, 8-bit frame with even width/height)."""
    t0 = frames[0][0]
    for t, load in frames:
        g = to_gray8(load(), lo, hi)
        g = g[: g.shape[0] - g.shape[0] % 2, : g.shape[1] - g.shape[1] % 2]
        if overlay:
            g = overlay.draw(g, (t - t0) / 1000.0)
        yield t, g


def open_stream(container, rate, w, h, crf, time_base=None, bframes=True):
    stream = container.add_stream("libx264", rate=rate)
    stream.width, stream.height = w, h
    stream.pix_fmt = "yuv420p"
    if time_base is not None:
        stream.time_base = time_base
        stream.codec_context.time_base = time_base
    stream.options = {"crf": str(crf), "preset": "medium"}
    if not bframes:
        stream.options["bf"] = "0"
    return stream


def to_video_frame(g):
    return av.VideoFrame.from_ndarray(g, format="gray").reformat(format="yuv420p")


def encode_vfr_mp4(frames, out_path, speed, lo, hi, crf, overlay):
    """Variable frame rate: each frame's pts is its recorded time in ms."""
    tb = Fraction(1, 1000)
    t0 = frames[0][0]
    nominal_fps = max(1, round(1000.0 / nominal_interval([f[0] for f in frames]) * speed))

    container = av.open(out_path, mode="w", options={"movflags": "+faststart"})
    stream = None
    last_pts = -1
    for i, (t, g) in enumerate(rendered_frames(frames, lo, hi, overlay)):
        if stream is None:
            stream = open_stream(container, nominal_fps, g.shape[1], g.shape[0], crf, tb)
        vf = to_video_frame(g)
        pts = int(round((t - t0) / speed))
        if pts <= last_pts:
            pts = last_pts + 1
        vf.pts, vf.time_base = pts, tb
        last_pts = pts
        for pkt in stream.encode(vf):
            container.mux(pkt)
        if (i + 1) % 500 == 0:
            print(f"  encoded {i+1}/{len(frames)}", file=sys.stderr)
    for pkt in stream.encode():
        container.mux(pkt)
    container.close()


def encode_cfr_avi(frames, out_path, speed, lo, hi, crf, overlay):
    """Constant frame rate at 2x the camera rate. Each recorded frame goes on
    the tick nearest its recorded time (pushed one tick later if that tick is
    taken) and is held until the next one, so no frame is dropped.
    Returns the largest shift between a frame's tick and its recorded time (ms)."""
    times = np.array([f[0] for f in frames], float)
    fps = max(1, round(2 * 1000.0 / nominal_interval(times) * speed))
    tick_ms = 1000.0 / fps
    ticks = np.round((times - times[0]) / speed / tick_ms).astype(int)
    for i in range(1, len(ticks)):
        ticks[i] = max(ticks[i], ticks[i - 1] + 1)
    max_shift = float(np.max(np.abs(ticks * tick_ms - (times - times[0]) / speed)))

    container = av.open(out_path, mode="w")
    stream = None
    out_tick = 0
    prev = None
    for i, (_, g) in enumerate(rendered_frames(frames, lo, hi, overlay)):
        if stream is None:
            stream = open_stream(container, fps, g.shape[1], g.shape[0], crf, bframes=False)
            stream.codec_context.codec_tag = "H264"
        while prev is not None and out_tick < ticks[i]:
            for pkt in stream.encode(to_video_frame(prev)):
                container.mux(pkt)
            out_tick += 1
        prev = g
    for pkt in stream.encode(to_video_frame(prev)):
        container.mux(pkt)
    for pkt in stream.encode():
        container.mux(pkt)
    container.close()
    return max_shift


# --------------------------------------------------------------------------

def convert(folder, out_dir, args):
    name = acquisition_name(folder)
    print(f"\n{name}")
    frames, source, n_saved = collect_frames(folder, args)
    frames.sort(key=lambda f: f[0])
    print(f"Source: {source}")
    print(timing_report([f[0] for f in frames], planned_frames(folder), n_saved))
    if args.report_only:
        return

    if args.range:
        lo, hi = args.range
    elif np.asarray(frames[0][1]()).dtype == np.uint8:
        lo = hi = None
    else:
        lo, hi = auto_range(frames)
        print(f"Intensity range: {lo:g} - {hi:g}")

    overlay = None
    if not args.no_overlay:
        w = np.asarray(frames[0][1]()).shape[1]
        overlay = Overlay(w - w % 2, eht_label(name), args.px_per_mm, args.bar_mm)

    out_dir = out_dir or os.path.dirname(os.path.normpath(
        os.path.dirname(folder) if re.fullmatch(r"Pos\d+", os.path.basename(folder)) else folder))
    os.makedirs(out_dir, exist_ok=True)
    if not args.avi:
        mp4 = os.path.join(out_dir, name + ".mp4")
        print(f"Writing {mp4} ...")
        encode_vfr_mp4(frames, mp4, args.speed, lo, hi, args.crf, overlay)
    else:
        avi = os.path.join(out_dir, name + ".avi")
        print(f"Writing {avi} ...")
        shift = encode_cfr_avi(frames, avi, args.speed, lo, hi, args.crf, overlay)
        print(f"  largest timing shift in .avi: {shift:.1f} ms")
        if shift > nominal_interval([f[0] for f in frames]) / args.speed:
            print("WARNING: many frames share the same timestamp, so the .avi drifts "
                  "from the recorded times. The timestamps may be when frames were "
                  "saved rather than captured; use the .mp4 and check the data.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", help="acquisition folder, its Pos0 folder, or a "
                    "folder containing several acquisitions")
    ap.add_argument("-o", "--output-dir", help="output folder (default: next to "
                    "each acquisition folder)")
    ap.add_argument("--speed", type=float, default=1.0,
                    help="playback speed relative to real time (default 1)")
    ap.add_argument("--range", type=float, nargs=2, metavar=("LO", "HI"),
                    help="fixed intensity range mapped to black/white")
    ap.add_argument("--crf", type=int, default=20,
                    help="x264 quality, lower = better/larger (default 20)")
    ap.add_argument("--px-per-mm", type=float, default=67.0,
                    help="camera calibration for the scale bar (default 67)")
    ap.add_argument("--bar-mm", type=float, default=1.0,
                    help="scale bar length in mm (default 1)")
    ap.add_argument("--no-overlay", action="store_true",
                    help="no scale bar, timer or label")
    ap.add_argument("--avi", action="store_true",
                    help="write an .avi (60 fps for a 30 fps camera) instead of the .mp4")
    ap.add_argument("--time-key", default="auto",
                    help="metadata key with the frame time. Default 'auto': "
                    "TimeReceivedByCore if every frame has it, else ElapsedTime-ms")
    ap.add_argument("--channel", type=int, default=0, help="channel index (default 0)")
    ap.add_argument("--slice", type=int, default=0, help="z index (default 0)")
    ap.add_argument("--report-only", action="store_true",
                    help="print the frame timing report, write no video")
    args = ap.parse_args()
    if args.speed <= 0:
        ap.error("--speed must be greater than 0")

    if av is None and not args.report_only:
        raise SystemExit("PyAV is required: pip install av")

    folders = find_acquisitions(os.path.abspath(args.folder))
    if not folders:
        raise SystemExit(f"No Micro-Manager acquisitions found in {args.folder}")
    out_dir = os.path.abspath(args.output_dir) if args.output_dir else None
    failed = []
    for folder in folders:
        try:
            convert(folder, out_dir, args)
        except (SystemExit, ValueError, OSError) as e:
            print(f"ERROR: {e}")
            failed.append(folder)
    if failed:
        raise SystemExit(f"\n{len(failed)} of {len(folders)} acquisition(s) failed: "
                         + ", ".join(failed))
    print("\nDone.")


if __name__ == "__main__":
    main()
