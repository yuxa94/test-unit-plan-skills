"""Derive room polygons from wall centerlines + room-name points (orthogonal plans).

Use when the zoning input is an existing plan (reference drawing) rather than closed polylines.
Centerline segments are barriers; each name point is flood-filled on a compressed grid.
Short gaps (doors drawn without centerline, near-misses) are closed by extending segment
ends up to --snap mm until they hit a perpendicular segment.

usage: zoning_from_centerlines.py <dump.tsv> <names.tsv> <out.json> [--layers CEN_CON,CEN_WALL] [--snap 300]
  dump.tsv : rows from dump-block.lsp (LINE \t layer \t x1 \t y1 \t x2 \t y2)
  names.tsv: layer \t name \t x \t y
Output: {"spaces":[{"id","name","polygon","area_m2"}], "unassigned_names":[...], "leaks":[...]}
"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "unit-plan", "scripts"))
from rectunion import union_loops

args = sys.argv[1:]
dump, names_f, out = args[:3]
layers = {"CEN_CON", "CEN_WALL"}
snap = 300.0
if "--layers" in args: layers = set(args[args.index("--layers") + 1].split(","))
if "--snap" in args: snap = float(args[args.index("--snap") + 1])

body_layers = {"CONC", "WAL", "WAL_DRY"}
if "--body" in args: body_layers = set(args[args.index("--body") + 1].split(","))

H, V = [], []  # (y, x1, x2) / (x, y1, y2)
BH, BV = [], []  # wall body lines, used to trim centerline overshoot
for line in open(dump, encoding="utf-8"):
    f = line.rstrip("\n").split("\t")
    if f[0] != "LINE": continue
    x1, y1, x2, y2 = map(float, f[2:6])
    if f[1] in layers:
        if abs(y1 - y2) < 1: H.append([round(y1), min(x1, x2), max(x1, x2)])
        elif abs(x1 - x2) < 1: V.append([round(x1), min(y1, y2), max(y1, y2)])
    elif f[1] in body_layers:
        if abs(y1 - y2) < 1: BH.append((y1, min(x1, x2), max(x1, x2)))
        elif abs(x1 - x2) < 1: BV.append((x1, min(y1, y2), max(y1, y2)))

# Centerlines are often drawn past the wall (e.g. to -300). Trim both ends to the span of
# parallel wall-body lines within 300 mm; interior gaps (doors) are kept bridged.
def trim(segs, body):
    for s in segs:
        spans = [(lo, hi) for c, lo, hi in body if abs(c - s[0]) <= 300 and hi > s[1] and lo < s[2]]
        if spans:
            s[1] = max(s[1], min(lo for lo, _ in spans))
            s[2] = min(s[2], max(hi for _, hi in spans))
trim(H, BH); trim(V, BV)

# virtual boundaries (open plan splits, no wall): --split "x1,y1,x2,y2;..."
virtual = []
if "--split" in args:
    for s in args[args.index("--split") + 1].split(";"):
        x1, y1, x2, y2 = map(float, s.split(","))
        virtual.append([x1, y1, x2, y2])
        if abs(y1 - y2) < 1: H.append([round(y1), min(x1, x2), max(x1, x2)])
        else: V.append([round(x1), min(y1, y2), max(y1, y2)])

def extend(segs, others):
    for s in segs:
        c, a, b = s
        # nearest perpendicular segment beyond each end that spans this coordinate
        lo = [o[0] for o in others if o[1] - 1 <= c <= o[2] + 1 and a - snap <= o[0] < a]
        hi = [o[0] for o in others if o[1] - 1 <= c <= o[2] + 1 and b < o[0] <= b + snap]
        if lo: s[1] = max(lo)
        if hi: s[2] = min(hi)
def bridge(segs):
    # close collinear gaps up to `snap` (e.g. a virtual split meeting a trimmed wall line)
    for s in segs:
        for o in segs:
            if o is s or o[0] != s[0]: continue
            if 0 < o[1] - s[2] <= snap: s[2] = o[1]
            if 0 < s[1] - o[2] <= snap: s[1] = o[2]

for _ in range(2):
    bridge(H); bridge(V)
    extend(H, V); extend(V, H)

xs = sorted({v for s in V for v in (s[0],)} | {v for s in H for v in (s[1], s[2])})
ys = sorted({v for s in H for v in (s[0],)} | {v for s in V for v in (s[1], s[2])})
nx, ny = len(xs) - 1, len(ys) - 1
# wall between cell (i,j) and (i+1,j) if a V segment at xs[i+1] covers (ys[j], ys[j+1])
def vblock(i, j):
    x = xs[i + 1]; ym = (ys[j] + ys[j + 1]) / 2
    return any(s[0] == x and s[1] <= ym <= s[2] for s in V)
def hblock(i, j):
    y = ys[j + 1]; xm = (xs[i] + xs[i + 1]) / 2
    return any(s[0] == y and s[1] <= xm <= s[2] for s in H)

def cell_of(x, y):
    i = next((k for k in range(nx) if xs[k] <= x < xs[k + 1]), None)
    j = next((k for k in range(ny) if ys[k] <= y < ys[k + 1]), None)
    return (i, j) if i is not None and j is not None else None

names = [l.rstrip("\n").split("\t") for l in open(names_f, encoding="utf-8") if l.strip()]
owner, spaces, unassigned, leaks = {}, [], [], []
for k, (lay, name, x, y, *_) in enumerate(names):
    c = cell_of(float(x), float(y))
    if c is None or c in owner:
        unassigned.append({"name": name, "at": [float(x), float(y)], "reason": "outside grid" if c is None else f"same region as {owner[c]}"})
        continue
    sid = f"S{len(spaces) + 1}"
    stack, cells, leak = [c], set(), False
    while stack:
        i, j = stack.pop()
        if (i, j) in cells: continue
        cells.add((i, j))
        for di, dj, blocked in ((1, 0, lambda: vblock(i, j)), (-1, 0, lambda: vblock(i - 1, j)),
                                (0, 1, lambda: hblock(i, j)), (0, -1, lambda: hblock(i, j - 1))):
            ni, nj = i + di, j + dj
            if blocked(): continue
            if not (0 <= ni < nx and 0 <= nj < ny): leak = True; continue
            stack.append((ni, nj))
    for cc in cells: owner[cc] = sid
    rects = [[xs[i], ys[j], xs[i + 1], ys[j + 1]] for i, j in cells]
    loops = union_loops(rects)
    outer = max((l for l in loops if l["outer"]), key=lambda l: l["area"])
    if leak: leaks.append(name)
    spaces.append({"id": sid, "name": name, "polygon": outer["points"], "area_m2": round(outer["area"] / 1e6, 2),
                   "holes": [l["points"] for l in loops if not l["outer"]], "open_to_outside": leak})

# --absorb "NAME:x1,y1,x2,y2;..." : unnamed cells whose centre lies in the rectangle (e.g. the extent of a
# reference floor hatch) join space NAME. Disconnected parts become NAME-2, NAME-3 ... and are reported.
absorbed = []
if "--absorb" in args:
    for spec in args[args.index("--absorb") + 1].split(";"):
        nm, box = spec.split(":")
        bx1, by1, bx2, by2 = map(float, box.split(","))
        base = next((s for s in spaces if s["name"] == nm), None)
        if not base:
            unassigned.append({"name": nm, "reason": "absorb target not found"}); continue
        add = [(i, j) for i in range(nx) for j in range(ny) if (i, j) not in owner
               and bx1 <= (xs[i] + xs[i + 1]) / 2 <= bx2 and by1 <= (ys[j] + ys[j + 1]) / 2 <= by2]
        mine = [c for c, sid in owner.items() if sid == base["id"]]
        for c in add: owner[c] = base["id"]
        rects = [[xs[i], ys[j], xs[i + 1], ys[j + 1]] for i, j in mine + add]
        outers = sorted((l for l in union_loops(rects) if l["outer"]), key=lambda l: -l["area"])
        lbl = next(((float(n[2]), float(n[3])) for n in names if n[1] == nm), None)
        from rectunion import _inside
        outers.sort(key=lambda l: not (lbl and _inside(lbl[0], lbl[1], l["points"])))   # labelled part keeps the name
        base.update({"polygon": outers[0]["points"], "area_m2": round(outers[0]["area"] / 1e6, 2)})
        for k, extra in enumerate(outers[1:], start=2):
            sid = f"S{len(spaces) + 1}"
            spaces.append({"id": sid, "name": f"{nm}-{k}", "polygon": extra["points"], "area_m2": round(extra["area"] / 1e6, 2),
                           "holes": [], "open_to_outside": False, "absorbed_from": box})
        absorbed.append({"name": nm, "box": box, "cells": len(add), "parts": [round(l["area"] / 1e6, 2) for l in outers]})

unnamed = []
for i in range(nx):
    for j in range(ny):
        if (i, j) not in owner:
            a = (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
            if a > 0.5e6: unnamed.append([xs[i], ys[j], xs[i + 1], ys[j + 1]])
json.dump({"spaces": spaces, "virtual_splits": virtual, "unassigned_names": unassigned, "leaks": leaks, "absorbed": absorbed,
           "unnamed_cells": unnamed}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for s in spaces:
    print(f'{s["id"]:4} {s["name"]:8} {s["area_m2"]:7.2f}m2 pts={len(s["polygon"])}{" LEAK" if s["open_to_outside"] else ""}')
for u in unassigned: print("UNASSIGNED", u)
