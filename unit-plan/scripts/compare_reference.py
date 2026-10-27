"""Compare a rule-generated unit (run_reference_unit.py job) with its reference unit.

usage: python -I compare_reference.py <config.json> [job_ms.tsv]
Writes <job>/comparison.md and prints it. Matches doors by room pair, windows by room (+side),
fixtures by block name against the reference instances; checks door swing vs fixtures.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from upgeom import wall_sides
from run_reference_unit import load_tsv


def main(cfg_path, ms_path=None):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    J = cfg["job"]
    m = json.load(open(os.path.join(J, "model.json"), encoding="utf-8"))
    ref = json.load(open(os.path.join(J, "reference_openings.json"), encoding="utf-8"))
    names = {s["id"]: s["name"] for s in m["spaces"] + m["fixed"]}
    sides = wall_sides(m)
    wmap = {w["id"]: w for w in m["walls"]}

    def pair(wall, t):
        for t0, t1, lo, hi in sides[wall]:
            if t0 <= t <= t1: return names.get(lo, "외부"), names.get(hi, "외부")
        return None, None
    for o in ref:
        o["c"] = sum(o["span"]) / 2
        o["pair"] = set(pair(o["wall"], o["c"]))
    rows = [f'# {cfg.get("block")} — 규칙 배치 vs 원본', "", "## 문",
            "| 실 | 연결 | 규칙: 벽 / 폭 / 중심 | 원본: 벽 / 개구부폭 / 중심 | 판정 |", "|---|---|---|---|---|"]
    stats = {"door_same_wall": 0, "door_total": 0, "win_same_wall": 0, "win_same_width": 0, "win_total": 0}
    used = set()
    for d in [o for o in m["openings"] if o["kind"] == "door"]:
        stats["door_total"] += 1
        c = sum(d["span"]) / 2
        cand = [i for i, x in enumerate(ref) if x["kind"] == "door" and {d["room"], d["to"]} == x["pair"] and i not in used]
        if cand:
            i = min(cand, key=lambda i: (ref[i]["wall"] != d["wall"], abs(ref[i]["c"] - c))); used.add(i); s = ref[i]
            same = s["wall"] == d["wall"]; stats["door_same_wall"] += same
            v = f"같은 벽, 중심 차 {round(c - s['c'])}" if same else "다른 벽"
            rows.append(f'| {d["room"]} | {d["to"]} | {d["wall"]} / {d["width_mm"]} / {round(c)} | {s["wall"]} / {s["width_mm"]} ({s["block"]}) / {round(s["c"])} | {v} |')
        else:
            alt = [x for x in ref if x["kind"] == "door" and d["room"] in x["pair"]]
            rows.append(f'| {d["room"]} | {d["to"]} | {d["wall"]} / {d["width_mm"]} / {round(c)} | ' +
                        (", ".join(f'{"·".join(sorted(x["pair"]))} {x["wall"]}' for x in alt) or "없음") + " | 연결 상대 다름 |")
    rows += ["", "## 창", "| 실 | 규칙: 벽 / 방위 / 폭 / 중심 | 원본: 벽 / 폭 / 중심 | 판정 |", "|---|---|---|---|"]
    used = set()
    for w in [o for o in m["openings"] if o["kind"] == "window"]:
        stats["win_total"] += 1
        c = sum(w["span"]) / 2
        cand = [i for i, x in enumerate(ref) if x["kind"] == "window" and w["room"] in x["pair"] and i not in used]
        if not cand:
            rows.append(f'| {w["room"]} | {w["wall"]} / {w.get("side")} / {w["width_mm"]} / {round(c)} | 없음 | 원본엔 창 없음 |'); continue
        i = min(cand, key=lambda i: (ref[i]["wall"] != w["wall"], abs(ref[i]["c"] - c))); used.add(i); s = ref[i]
        if s["wall"] == w["wall"]:
            stats["win_same_wall"] += 1
            same_w = abs(s["width_mm"] - w["width_mm"]) <= 30; stats["win_same_width"] += same_w
            v = "같은 벽" + ("·같은 폭" if same_w else f'·폭 {w["width_mm"] - s["width_mm"]:+d}') + f", 중심 차 {round(c - s['c'])}"
        else:
            v = "다른 벽"
        rows.append(f'| {w["room"]} | {w["wall"]} / {w.get("side")} / {w["width_mm"]} / {round(c)} | {s["wall"]} / {s["width_mm"]} / {round(s["c"])} | {v} |')

    src = {}
    for r in load_tsv(cfg["dump"]):
        if r[0] == "INSERT" and r[8] and r[2] not in src: src[r[2]] = list(map(float, r[8:12]))
    def ctr(b): return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    rows += ["", "## 욕실·주방", "| 항목 | 규칙 외곽 | 원본 외곽 | 중심 차(x, y) |", "|---|---|---|---|"]
    for f in m["fixtures"]:
        fp = f.get("footprint") or f.get("rect"); s = src.get(f.get("block"))
        d = "—" if not s else "(%+d, %+d)" % tuple(round(a - b) for a, b in zip(ctr(fp), ctr(s)))
        rows.append(f'| {f["kind"]} {f.get("block") or ""} ({f["space"]}) | {[round(v) for v in fp]} | {[round(v) for v in s] if s else "원본 없음"} | {d} |')
    placed = {f.get("block") for f in m["fixtures"]}
    for b in ("싱크", "쿡탑", "세탁기-850", "식탁-1300x800"):
        if b in src and b not in placed: rows.append(f"| {b} | 미배치 | {[round(v) for v in src[b]]} | — |")

    rows += ["", "## 문 열림 간섭 검사"]
    hit = False
    for d in [o for o in m["openings"] if o["kind"] == "door" and o["type"] == "swing"]:
        w = wmap[d["wall"]]
        fc = w["axis_coord"] + (w["hi"] if d["swing_side"] == "hi" else w["lo"])
        n0, n1 = sorted((fc, fc + (d["width_mm"] if d["swing_side"] == "hi" else -d["width_mm"])))
        t0, t1 = d["span"]
        sr = [t0, n0, t1, n1] if w["orient"] == "H" else [n0, t0, n1, t1]
        for f in m["fixtures"]:
            if d.get("basis") == "ubr_door" and f["kind"] == "ubr" and f["space"] == d["room"]: continue
            fp = f.get("footprint") or f.get("rect")
            ox = min(sr[2], fp[2]) - max(sr[0], fp[0]); oy = min(sr[3], fp[3]) - max(sr[1], fp[1])
            if ox > 0 and oy > 0:
                hit = True; rows.append(f'- {d["room"]} 문 열림이 {f["kind"]} {f.get("block") or ""}와 {round(ox)}x{round(oy)} 겹침')
    if not hit: rows.append("- 없음")
    rows += ["", "## 요약",
             f'- 문: {stats["door_same_wall"]}/{stats["door_total"]} 같은 벽',
             f'- 창: {stats["win_same_wall"]}/{stats["win_total"]} 같은 벽, {stats["win_same_width"]}/{stats["win_total"]} 같은 폭',
             "", "## 규칙 실행 이슈"] + [f"- {k}: {i}" for k, v in m["issues"].items() for i in v]
    out = "\n".join(rows) + "\n"
    open(os.path.join(J, "comparison.md"), "w", encoding="utf-8").write(out)
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
