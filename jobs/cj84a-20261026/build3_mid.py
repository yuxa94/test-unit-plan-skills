# ---------------------------------------------------------------- v003 order: reserve kitchen -> UBR -> UBR doors -> doors -> windows
from place_kitchen import reserve_counter
from place_bathroom import measure_ubr, place_ubr
taken = {}
res = reserve_counter(model, kcfg)          # kitchen counter wall is reserved before doors/windows
if res:
    for wid, span in res["walls"]: taken.setdefault(wid, []).append(span)
    kcfg["reserved"] = {k: res[k] for k in ("orient", "n", "face", "span", "walls")}

# pre-pass without openings: clear loops do not depend on openings
G["openings"], G["cuts"] = [], []
run(136, 234)
clear_pre = {f["name"]: f["loops"] for f in G["finish"]}

# UBR library: body + panel blocks measured from the reference instances
ins_rows = {r[2]: r for r in G["rows"] if r[0] == "INSERT"}
def dump(p): return [l.rstrip("\n").split("\t") for l in open(JOB + "\\input\\" + p, encoding="utf-8")]
ubr_lib = {
    "공용": measure_ubr(ins_rows["UBR 공용욕실 1500x2200"], ins_rows["A$C84b07bde"], dump("ubr_common_extra.tsv")),
    "부부": measure_ubr(ins_rows["UBR 부부욕실 1600x2300"], ins_rows["A$C4e4a4905"], dump("ubr_master_extra.tsv")),
}
ubr_rules = [
    {"room": "욕실1", "ubr": "공용", "door_to": ["현관", "거실", "주방/식당"], "door_width": 800},
    {"room": "욕실2", "ubr": "부부", "door_to": ["드레스룸", "침실1"], "door_width": 800},
]
P["bathroom"] = {"system": {"value": "ubr", "status": UC},
                 "rooms": {"value": ubr_rules, "status": UC},
                 "rule": {"value": "UBR 실제 외곽선이 안목 안 + UBR 문이 door_to 실에 면함; 욕실 문은 UBR 문 위치를 따름", "status": UC}}
ubr, bath_doors, bath_issues = place_ubr(model, ubr_rules, ubr_lib, clear_pre)
for d in bath_doors: taken.setdefault(d["wall"], []).append(d["span"])

doors, door_issues = place_doors(model, [r for r in door_rules if r["room"] not in ("욕실1", "욕실2")], taken=taken)
doors = bath_doors + doors
for k, d in enumerate(doors): d["id"] = f"D{k + 1}"
wins, win_issues = place_windows(model, win_rules, WIDTHS, taken=taken)
wmap = {w["id"]: w for w in walls}
openings = []
for o in doors + wins:
    w = wmap[o["wall"]]
    a, b = o["span"]
    o["cut"] = [a, w["rect"][1] - 5, b, w["rect"][3] + 5] if w["orient"] == "H" else [w["rect"][0] - 5, a, w["rect"][2] + 5, b]
    c = (a + b) / 2
    o["center"] = (c, w["axis_coord"]) if w["orient"] == "H" else (w["axis_coord"], c)
    openings.append(o)
G["openings"], G["cuts"] = openings, [o["cut"] for o in openings]

run(136, 234)                        # wall outlines, insulation, finish loops, dimensions (with openings)
groups, ins_loops, finish = G["groups"], G["ins_loops"], G["finish"]
dims, clear_dims = G["dims"], G["clear_dims"]
clear_loops = {f["name"]: f["loops"] for f in finish}

# kitchen library (unchanged from v002)
lib = {}
for name in ("싱크", "쿡탑", "식탁-1300x800", "세탁기-850"):
    ins = ins_rows[name]
    ip, rot, xs = (float(ins[3]), float(ins[4])), round(float(ins[5])) % 360, round(float(ins[6]))
    lb = local_bbox_from_instance(ip, rot, xs, list(map(float, ins[8:12])))
    normal = None
    if name in ("싱크", "쿡탑"):
        nx, ny = inverse(rot, xs, (1, 0)); normal = (round(nx), round(ny))
    lib[name] = {"lbbox": lb, "rot": rot, "xs": xs, "normal": normal}
kit, kit_issues = place_kitchen(model, kcfg, lib, clear_loops, openings, [w["rect"] for w in walls])
fixtures = ubr + kit

# ---------------------------------------------------------------- model / profile
labels = [{"text": n[1], "at": [float(n[2]), float(n[3])]} for n in
          (l.rstrip("\n").split("\t") for l in open(JOB + r"\input\names_local.tsv", encoding="utf-8")) if n[0] == "실명"]
model2 = {"version": 1, "unit": {"type": "84A", "variant": "basic", "mode": "rule-v003"}, "spaces": spaces, "fixed": fixed,
          "walls": walls, "openings": openings, "fixtures": fixtures, "insulation_runs": G["ins_runs"], "finish": finish,
          "dimensions": dims + clear_dims, "annotations": labels, "ubr_lib": ubr_lib,
          "issues": {"doors": door_issues, "windows": win_issues, "bathroom": bath_issues, "kitchen": kit_issues}}
os.makedirs(JOB + r"\v002", exist_ok=True)
json.dump(P, open(JOB + r"\v002\profile.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(model2, open(JOB + r"\v002\model.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=list)
