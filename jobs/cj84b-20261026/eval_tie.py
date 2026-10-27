"""Evaluate corridor_tie options for door placement on 84A (v009) and 84B (v004) models vs the reference."""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
SK = r"C:\Users\Planby Technologies\Desktop\2026\Autocad_mcp_test\unit-plan-skills"
for d in ("unit-plan", "unit-plan-doors", "unit-plan-kitchen-furniture"):
    sys.path.insert(0, SK + "\\" + d + r"\scripts")
from place_doors import place_doors
from upgeom import wall_sides

def setup(model_path, ref, door_rules, corridor_max=1800, jamb=100):
    m = json.load(open(model_path, encoding="utf-8"))
    base = {"spaces": m["spaces"], "fixed": m["fixed"], "walls": m["walls"]}
    # same reservations as the pipeline: kitchen counter wall, UBR doors, then (rule) doors
    taken = {}
    for o in m["openings"]:
        if o.get("basis") == "ubr_door": taken.setdefault(o["wall"], []).append(o["span"])
    kit = [f for f in m["fixtures"] if f["kind"] == "counter"]
    return m, base, taken
UNITS = {
    "84A": (r"C:\temp\cj84a\v009\model.json", r"C:\temp\cj84a\model.json", "v001"),
    "84B": (r"C:\temp\cj84b\model.json", r"C:\temp\cj84b\reference_openings.json", "ref"),
}
cfg_b = json.load(open(r"C:\temp\cj84b\config_v004.json", encoding="utf-8"))
rules = [r for r in cfg_b["doors"]["rules"]]
for unit, (mp, refp, kind) in UNITS.items():
    m = json.load(open(mp, encoding="utf-8"))
    base = {"spaces": m["spaces"], "fixed": m["fixed"], "walls": m["walls"]}
    names = {s["id"]: s["name"] for s in m["spaces"] + m["fixed"]}
    sides = wall_sides(base)
    ref = json.load(open(refp, encoding="utf-8"))
    ref = ref["openings"] if isinstance(ref, dict) else ref
    refd = []
    for o in ref:
        if o.get("kind") != "door" or not o.get("wall"): continue
        c = sum(o["span"]) / 2
        seg = next(((lo, hi) for t0, t1, lo, hi in sides[o["wall"]] if t0 <= c <= t1), (None, None))
        refd.append(({names.get(seg[0]), names.get(seg[1])}, o["wall"], c))
    # taken = everything the pipeline reserved before rule doors: UBR doors + kitchen counter + windows don't matter
    taken0 = {}
    for o in m["openings"]:
        if o.get("basis") == "ubr_door": taken0.setdefault(o["wall"], []).append(list(o["span"]))
    for f in m["fixtures"]:
        pass
    print(f"## {unit}")
    for tie in ("entry", "far_entry", "living", "rc_wall"):
        taken = {k: [list(s) for s in v] for k, v in taken0.items()}
        # kitchen counter reservation (recomputed like the pipeline)
        from place_kitchen import reserve_counter
        res = reserve_counter(base, {"room": "주방/식당"})
        if res:
            for wid, span in res["walls"]: taken.setdefault(wid, []).append(span)
        rr = [r for r in rules if r["room"] not in ("욕실1", "욕실2")]
        doors, _ = place_doors(base, rr, taken=taken, corridor_max=1800, jamb=100, corridor_tie=tie)
        out = []
        for d in doors:
            c = sum(d["span"]) / 2
            s = next(((w, rc) for p, w, rc in refd if p == {d["room"], d["to"]}), None)
            diff = "—" if not s else (f"{round(c - s[1])}" if s[0] == d["wall"] else "다른벽")
            out.append(f'{d["room"]}:{diff}')
        print(f"  {tie:10}", "  ".join(out))
