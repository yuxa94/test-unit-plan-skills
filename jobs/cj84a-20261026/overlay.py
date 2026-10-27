"""Overlay: source unit (grey) vs job DWG model space (colour by layer). usage: overlay.py src.tsv job.tsv out.html"""
import sys, math
src, job, out = sys.argv[1:4]
COL = {"CONC": "#d00", "WAL": "#a50", "WAL_DRY": "#c6c", "A_HAT": "#fa0", "CEN_CON": "#f99", "CEN_WALL": "#e9e",
       "INS": "#09c", "FIN": "#0a0", "바닥타일": "#9c9", "DIM": "#00f", "실명": "#f60", "DOOR": "#080", "SINA-F-FRAME": "#080",
       "WIN": "#06f", "FUR": "#a0a", "AA-XXXX-UBR": "#a0a", "수전": "#a0a"}
els, xs, ys = [], [], []

def P(x, y):
    xs.append(x); ys.append(y); return f"{x:.0f},{-y:.0f}"

def draw(path, grey):
    for line in open(path, encoding="utf-8"):
        f = line.rstrip("\n").split("\t")
        if len(f) < 3: continue
        c = "#bbb" if grey else COL.get(f[1], "#555")
        w = 8 if grey else 14
        if f[0] == "LINE":
            els.append(f'<polyline points="{P(float(f[2]), float(f[3]))} {P(float(f[4]), float(f[5]))}" stroke="{c}" stroke-width="{w}" fill="none"/>')
        elif f[0] == "PLINE":
            pts = [tuple(map(float, p.split(","))) for p in f[3].split(";") if p]
            if f[2] == "closed": pts.append(pts[0])
            els.append(f'<polyline points="{" ".join(P(*p) for p in pts)}" stroke="{c}" stroke-width="{w}" fill="none"/>')
        elif f[0] == "ARC":
            cx, cy, r, a0, a1 = map(float, f[2:7])
            if a1 < a0: a1 += 360
            t = [math.radians(a0 + (a1 - a0) * k / 16) for k in range(17)]
            els.append(f'<polyline points="{" ".join(P(cx + r*math.cos(a), cy + r*math.sin(a)) for a in t)}" stroke="{c}" stroke-width="{w}" fill="none"/>')
        elif f[0] == "INSERT" and len(f) >= 12 and f[8]:
            x1, y1, x2, y2 = map(float, f[8:12])
            els.append(f'<rect x="{x1:.0f}" y="{-y2:.0f}" width="{x2-x1:.0f}" height="{y2-y1:.0f}" stroke="{c}" stroke-width="{w}" fill="none" stroke-dasharray="{"" if grey else "40,30"}"/>')
            if not grey: P(x1, y1); P(x2, y2)
        elif f[0] == "TEXT" and not grey:
            els.append(f'<text x="{float(f[3]):.0f}" y="{-float(f[4]):.0f}" font-size="{float(f[5])*1.6:.0f}" fill="{c}">{f[2]}</text>')
        elif f[0] == "HATCH" and len(f) >= 9 and f[5] and not grey:
            x1, y1, x2, y2 = map(float, f[5:9])
            els.append(f'<rect x="{x1:.0f}" y="{-y2:.0f}" width="{x2-x1:.0f}" height="{y2-y1:.0f}" fill="{c}" fill-opacity="0.18" stroke="none"/>')

draw(src, True)
draw(job, False)
pad = 500
x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
if len(sys.argv) > 4:  # crop window "x0,y0,x1,y1"
    x0, y0, x1, y1 = map(float, sys.argv[4].split(","))
svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.0f} {-y1:.0f} {x1-x0:.0f} {y1-y0:.0f}" style="background:#fff;font-family:Malgun Gothic">' + "".join(els) + "</svg>"
open(out, "w", encoding="utf-8").write(f'<!doctype html><meta charset="utf-8"><body style="margin:0">{svg}</body>')
