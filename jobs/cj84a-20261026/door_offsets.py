"""Measure where the reference doors sit inside their shared wall segment (distance to both corners)."""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Planby Technologies\Desktop\2026\Autocad_mcp_test\unit-plan-skills\unit-plan\scripts")
from upgeom import wall_sides
JOB = r"C:\temp\cj84a"
m1 = json.load(open(JOB + r"\model.json", encoding="utf-8"))      # v001: reference openings (source parts)
m6 = json.load(open(JOB + r"\v006\model.json", encoding="utf-8"))  # v006: rule doors (for the same room pairs)
names = {s["id"]: s["name"] for s in m1["spaces"] + m1["fixed"]}
sides = wall_sides(m1)
src = {}
for o in m1["openings"]:
    if o["kind"] != "door" or not o.get("wall"): continue
    c = sum(o["span"]) / 2
    for t0, t1, lo, hi in sides[o["wall"]]:
        if t0 <= c <= t1:
            src[frozenset((names.get(lo, "외부"), names.get(hi, "외부")))] = (o, t0, t1, lo, hi)
# entry point for "near end" comparison
entry = next(s for s in m1["spaces"] if s["name"] == "현관")
ex = sum(p[0] for p in entry["polygon"]) / len(entry["polygon"]); ey = sum(p[1] for p in entry["polygon"]) / len(entry["polygon"])
print("| 실 | 원본 블록 | 구간 길이 | 개구부(원본 bbox폭) | 가까운 모서리까지 | 먼 모서리까지 | 가까운 모서리 = 현관 쪽? | 경첩(원본 삽입점) 쪽 |")
print("|---|---|---|---|---|---|---|---|")
ins = {r[2] + "@" + r[3]: (float(r[3]), float(r[4])) for r in
       (l.rstrip("\n").split("\t") for l in open(JOB + r"\input\84A_basic_L1.tsv", encoding="utf-8")) if r[0] == "INSERT"}
for d in m6["openings"]:
    if d["kind"] != "door": continue
    key = frozenset((d["room"], d["to"]))
    if key not in src: continue
    o, t0, t1, lo, hi = src[key]
    w = next(x for x in m1["walls"] if x["id"] == o["wall"])
    a, b = o["span"]
    da, db = a - t0, t1 - b
    near_t0 = da <= db
    p0 = (t0, w["axis_coord"]) if w["orient"] == "H" else (w["axis_coord"], t0)
    p1 = (t1, w["axis_coord"]) if w["orient"] == "H" else (w["axis_coord"], t1)
    entry_t0 = (p0[0] - ex) ** 2 + (p0[1] - ey) ** 2 <= (p1[0] - ex) ** 2 + (p1[1] - ey) ** 2
    print(f'| {d["room"]} | {o["block"]} | {round(t1 - t0)} | {round(b - a)} | {round(min(da, db))} | {round(max(da, db))} | '
          f'{"예" if near_t0 == entry_t0 else "아니오"} | — |')
