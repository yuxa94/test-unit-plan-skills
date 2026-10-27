"""Compare v002 (rule placement) with the reference 84A (v001 = source parts)."""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Planby Technologies\Desktop\2026\Autocad_mcp_test\unit-plan-skills\unit-plan\scripts")
from upgeom import wall_sides

JOB = r"C:\temp\cj84a"
m1 = json.load(open(JOB + r"\model.json", encoding="utf-8"))
VER = sys.argv[1] if len(sys.argv) > 1 else "v002"
m2 = json.load(open(JOB + "\\" + VER + r"\model.json", encoding="utf-8"))
names = {s["id"]: s["name"] for s in m1["spaces"] + m1["fixed"]}
sides = wall_sides(m1)
wmap = {w["id"]: w for w in m1["walls"]}

def pair_at(wall, t):
    for t0, t1, lo, hi in sides[wall]:
        if t0 <= t <= t1: return names.get(lo, "외부"), names.get(hi, "외부")
    return None, None

src_doors, src_wins = [], []
for o in m1["openings"]:
    if not o.get("wall"): continue
    c = sum(o["span"]) / 2
    lo, hi = pair_at(o["wall"], c)
    (src_doors if o["kind"] == "door" else src_wins).append({**o, "pair": {lo, hi}, "c": c})

rows = ["## 문", "| 실 | 연결 | 규칙: 벽 / 폭 / 중심 | 원본: 벽 / 개구부폭 / 중심 | 판정 |", "|---|---|---|---|---|"]
for d in [o for o in m2["openings"] if o["kind"] == "door"]:
    c = sum(d["span"]) / 2
    s = next((x for x in src_doors if {d["room"], d["to"]} == x["pair"]), None)
    if s:
        same = s["wall"] == d["wall"]
        verdict = ("같은 벽, 중심 차 %d" % round(c - s["c"])) if same else "다른 벽"
        rows.append(f'| {d["room"]} | {d["to"]} | {d["wall"]} / {d["width_mm"]} / {round(c)} | {s["wall"]} / {s["width_mm"]} ({s["block"]}) / {round(s["c"])} | {verdict} |')
    else:
        alt = [x for x in src_doors if d["room"] in x["pair"]]
        rows.append(f'| {d["room"]} | {d["to"]} | {d["wall"]} / {d["width_mm"]} / {round(c)} | ' +
                    (", ".join(f'{"·".join(sorted(x["pair"]))} {x["wall"]}' for x in alt) or "없음") + ' | 연결 상대 다름 |')

rows += ["", "## 창", "| 실 | 규칙: 벽 / 폭 / 중심 | 원본: 벽 / 폭 / 중심 | 판정 |", "|---|---|---|---|"]
for w in [o for o in m2["openings"] if o["kind"] == "window"]:
    c = sum(w["span"]) / 2
    s = [x for x in src_wins if w["room"] in x["pair"]]
    if not s:
        rows.append(f'| {w["room"]} | {w["wall"]} / {w["width_mm"]} / {round(c)} | 없음 | 원본엔 창 없음 |'); continue
    best = min(s, key=lambda x: (x["wall"] != w["wall"], abs(x["c"] - c)))
    if best["wall"] == w["wall"]:
        v = "같은 벽" + ("·같은 폭" if best["width_mm"] == w["width_mm"] else f'·폭 {w["width_mm"] - best["width_mm"]:+d}') + f', 중심 차 {round(c - best["c"])}'
    else:
        v = "다른 벽"
    rows.append(f'| {w["room"]} | {w["wall"]} / {w["width_mm"]} / {round(c)} | ' + ", ".join(f'{x["wall"]} / {x["width_mm"]} / {round(x["c"])}' for x in s) + f' | {v} |')

# fixtures vs source part bboxes
src_parts = {}
for r in (l.rstrip("\n").split("\t") for l in open(JOB + r"\input\84A_basic_L1.tsv", encoding="utf-8")):
    if r[0] == "INSERT" and r[2] not in src_parts: src_parts[r[2]] = list(map(float, r[8:12]))
rows += ["", "## 욕실·주방", "| 항목 | 규칙 외곽 | 원본 외곽 | 중심 차(x, y) |", "|---|---|---|---|"]
def ctr(b): return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
seen = set()
for f in m2["fixtures"]:
    fp = f.get("footprint") or f.get("rect")
    s = src_parts.get(f.get("block"))
    seen.add(f.get("block"))
    d = "—" if not s else "(%+d, %+d)" % tuple(round(a - b) for a, b in zip(ctr(fp), ctr(s)))
    rows.append(f'| {f["kind"]} {f.get("block") or ""} ({f["space"]}) | {[round(v) for v in fp]} | {[round(v) for v in s] if s else "원본 없음"} | {d} |')
for b in ("UBR 부부욕실 1600x2300", "세탁기-850"):
    if b not in seen: rows.append(f'| {b} | 미배치 | {[round(v) for v in src_parts[b]]} | — |')

# door swing square vs fixtures (clearance check the skill requires)
rows += ["", "## UBR 실제 삽입 외곽(CAD 재읽기) vs 원본", "| 블록 | 결과 bbox | 원본 bbox | 차(xmin, ymin, xmax, ymax) |", "|---|---|---|---|"]
import os
ms = JOB + "\\" + VER + r"\job_ms.tsv"
if os.path.exists(ms):
    got, got_ins = {}, {}
    for r in (l.rstrip("\n").split("\t") for l in open(ms, encoding="utf-8")):
        if r[0] == "INSERT" and len(r) >= 12 and r[8]: got[r[2]] = list(map(float, r[8:12]))
        elif r[0] == "INSERT": got_ins[r[2]] = (float(r[3]), float(r[4]))
    src_ins = {r[2]: (float(r[3]), float(r[4])) for r in (l.rstrip("\n").split("\t") for l in open(JOB + r"\input\84A_basic_L1.tsv", encoding="utf-8")) if r[0] == "INSERT"}
    for b in ("UBR 공용욕실 1500x2200", "A$C84b07bde", "UBR 부부욕실 1600x2300", "A$C4e4a4905"):
        if b in got_ins:   # bbox unavailable through ObjectDBX (block holds dimensions): compare insertion points
            rows.append(f'| {b} | 삽입점 {tuple(round(v) for v in got_ins[b])} | 삽입점 {tuple(round(v) for v in src_ins[b])} | 삽입점 차 {tuple(round(a - c) for a, c in zip(got_ins[b], src_ins[b]))} |')
        elif b in got and b in src_parts:
            rows.append(f'| {b} | {[round(v) for v in got[b]]} | {[round(v) for v in src_parts[b]]} | {tuple(round(a - c) for a, c in zip(got[b], src_parts[b]))} |')
        elif b in src_parts:
            rows.append(f'| {b} | 없음 | {[round(v) for v in src_parts[b]]} | — |')
rows += ["", "## 문 열림 간섭 검사"]
def swing_rect(d):
    w = next(x for x in m2["walls"] if x["id"] == d["wall"])
    f = w["axis_coord"] + (w["hi"] if d["swing_side"] == "hi" else w["lo"])
    n0, n1 = sorted((f, f + (d["width_mm"] if d["swing_side"] == "hi" else -d["width_mm"])))
    t0, t1 = d["span"]
    return [t0, n0, t1, n1] if w["orient"] == "H" else [n0, t0, n1, t1]
hit = False
for d in [o for o in m2["openings"] if o["kind"] == "door" and o["type"] == "swing"]:
    sr = swing_rect(d)
    for f in m2["fixtures"]:
        if d.get("basis") == "ubr_door" and f["kind"] == "ubr" and f["space"] == d["room"]: continue
        fp = f.get("footprint") or f.get("rect")
        ox = min(sr[2], fp[2]) - max(sr[0], fp[0]); oy = min(sr[3], fp[3]) - max(sr[1], fp[1])
        if ox > 0 and oy > 0:
            hit = True
            rows.append(f'- {d["room"]} 문({d["width_mm"]}) 열림 범위가 {f["kind"]} {f.get("block") or ""}와 {round(ox)}x{round(oy)} 겹침')
if not hit: rows.append("- 없음")

rows += ["", "## 규칙 실행 이슈"] + [f"- {k}: {i}" for k, v in m2["issues"].items() for i in v]
open(JOB + "\\" + VER + r"\comparison.md", "w", encoding="utf-8").write("\n".join(rows) + "\n")
print("\n".join(rows))
