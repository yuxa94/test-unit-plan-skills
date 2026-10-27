"""Render a dump-block TSV (+ optional names / zoning json) to SVG for visual checks."""
import sys, math, json

src, out = sys.argv[1], sys.argv[2]
names = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else None
zoning = sys.argv[4] if len(sys.argv) > 4 else None
style = {"CONC": ("#000", 22), "WAL": ("#000", 18), "WAL_DRY": ("#777", 14), "CEN_CON": ("#e00", 10), "CEN_WALL": ("#c0c", 10),
         "INS": ("#0aa", 10), "FIN": ("#bbb", 6), "MC": ("#36f", 5)}
els, xs, ys = [], [], []

def P(x, y):
    xs.append(x); ys.append(y); return f"{x:.0f},{-y:.0f}"

for line in open(src, encoding="utf-8"):
    f = line.rstrip("\n").split("\t")
    c, w = style.get(f[1], ("#ccc", 5)) if len(f) > 1 else ("#ccc", 5)
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
        els.append(f'<polyline points="{" ".join(P(cx + r*math.cos(a), cy + r*math.sin(a)) for a in t)}" stroke="#0a0" stroke-width="6" fill="none"/>')
    elif f[0] == "INSERT":
        x, y = float(f[3]), float(f[4])
        els.append(f'<circle cx="{x:.0f}" cy="{-y:.0f}" r="40" fill="#0a0"/><text x="{x:.0f}" y="{-y:.0f}" font-size="90" fill="#0a0">{f[2]}</text>')

if zoning:
    z = json.load(open(zoning, encoding="utf-8"))
    for s in z["spaces"]:
        pts = s["polygon"] + [s["polygon"][0]]
        els.insert(0, f'<polygon points="{" ".join(P(*p) for p in pts)}" fill="hsl({hash(s["name"])%360},70%,85%)" stroke="#f60" stroke-width="20"/>')
        cx = sum(p[0] for p in s["polygon"]) / len(s["polygon"]); cy = sum(p[1] for p in s["polygon"]) / len(s["polygon"])
        els.append(f'<text x="{cx:.0f}" y="{-cy:.0f}" font-size="200" fill="#c40" text-anchor="middle">{s["id"]} {s["name"]}</text>')
if names:
    for line in open(names, encoding="utf-8"):
        f = line.rstrip("\n").split("\t")
        els.append(f'<text x="{float(f[2]):.0f}" y="{-float(f[3]):.0f}" font-size="220" fill="#e60" font-weight="bold">{f[1]}</text>')

pad = 600
x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.0f} {-y1:.0f} {x1-x0:.0f} {y1-y0:.0f}" style="background:#fff;font-family:Malgun Gothic">' + "".join(els) + "</svg>"
open(out, "w", encoding="utf-8").write(f'<!doctype html><meta charset="utf-8"><body style="margin:0">{svg}</body>')
