"""Derive profile proposals for a reference unit: windows (room/side/width), doors (room pair/width),
UBR body/panel pairs, kitchen blocks. Output: derived_profile.json + printed table."""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
SK = r"C:\Users\Planby Technologies\Desktop\2026\Autocad_mcp_test\unit-plan-skills"
for d in ("unit-plan", "unit-plan-windows"):
    sys.path.insert(0, SK + "\\" + d + r"\scripts")
import run_reference_unit as R
from upgeom import wall_sides
from place_windows import outward

JOB = r"C:\temp\cj84b"
rows = R.load_tsv(JOB + r"\input\84B_basic_L1.tsv")
lines = [(r[1], *map(float, r[2:6])) for r in rows if r[0] == "LINE"]
ins_rows = [r for r in rows if r[0] == "INSERT"]
inserts = [{"layer": r[1], "name": r[2], "bbox": list(map(float, r[8:12]))} for r in ins_rows if r[8]]
z = json.load(open(JOB + r"\zoning.json", encoding="utf-8"))
spaces = [{"id": s["id"], "name": s["name"], "polygon": s["polygon"]} for s in z["spaces"]]
walls = R.build_walls(lines, {"walls": {"party_axes": [["V", 0]]}})
model = {"spaces": spaces, "fixed": [], "walls": walls}
sides = wall_sides(model)
names = {s["id"]: s["name"] for s in spaces}
wmap = {w["id"]: w for w in walls}
ref = R.reference_openings(inserts, walls)
out = {"windows": [], "doors": []}
for o in ref:
    c = sum(o["span"]) / 2
    seg = next(((lo, hi) for t0, t1, lo, hi in sides[o["wall"]] if t0 <= c <= t1), (None, None))
    lo, hi = (names.get(seg[0]), names.get(seg[1]))
    if o["kind"] == "window":
        heated = [n for n in (lo, hi) if n and not n.startswith("발코니") and n != "하향식피난구"]
        room = heated[0] if heated else (lo or hi)
        side = "lo" if room == lo else "hi"
        out["windows"].append({"room": room, "side": outward(wmap[o["wall"]], side), "width": o["width_mm"], "block": o["block"], "wall": o["wall"]})
    else:
        out["doors"].append({"pair": [lo, hi], "width_bbox": o["width_mm"], "block": o["block"], "wall": o["wall"]})
ubr_bodies = [r for r in ins_rows if r[2].startswith("UBR")]
panels = [r for r in ins_rows if r[1] == "AA-XXXX-UBR"]
def ov(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
pairs = []
for b in ubr_bodies:
    bb = list(map(float, b[8:12]))
    p = max(panels, key=lambda p: ov(bb, list(map(float, p[8:12]))) if p[8] else 0) if panels else None
    room = next((s["name"] for s in spaces if R._inside((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, s["polygon"])), None)
    pairs.append({"room": room, "body": b[2], "panel": p[2] if p else None, "bbox": [round(v) for v in bb]})
out["ubr"] = pairs
out["kitchen_blocks"] = sorted({r[2] for r in ins_rows if r[2] in ("싱크", "쿡탑", "식탁-1300x800", "세탁기-850") or "식탁" in r[2] or "세탁" in r[2] or "싱크" in r[2] or "쿡탑" in r[2]})
out["walls_default"] = [f'{w["id"]} {w["orient"]}{w["axis_coord"]}' for w in walls if w["basis"] == "default_by_layer"]
json.dump(out, open(JOB + r"\derived_profile.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("## windows"); [print("  ", w) for w in out["windows"]]
print("## doors"); [print("  ", d) for d in out["doors"]]
print("## ubr"); [print("  ", u) for u in out["ubr"]]
print("## kitchen blocks", out["kitchen_blocks"])
print("## walls with default thickness", out["walls_default"])
