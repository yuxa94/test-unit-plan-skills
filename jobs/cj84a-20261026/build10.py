"""청주 월명 84A 기본형 v010 — 문: 홀 동률 시 거실 쪽 모서리.
조닝/벽/단열/마감/치수 계산은 build.py와 동일 코드를 재사용한다(같은 벽 ID)."""
import json, os, sys, math
sys.stdout.reconfigure(encoding="utf-8")
SK = r"C:\Users\Planby Technologies\Desktop\2026\Autocad_mcp_test\unit-plan-skills"
for d in ("unit-plan", "unit-plan-doors", "unit-plan-windows", "unit-plan-bathroom", "unit-plan-kitchen-furniture"):
    sys.path.insert(0, SK + "\\" + d + r"\scripts")
from place_doors import place_doors
from place_windows import place_windows
from place_bathroom import place_ubr
from place_kitchen import place_kitchen
from upgeom import local_bbox_from_instance, inverse, face

JOB = r"C:\temp\cj84a"
SRCPY = (open(JOB + r"\build.py", encoding="utf-8").read()
         .replace(r"\zoning.json", r"\zoning_v008.json")
         .replace('"발코니2": "balcony",', '"발코니2": "balcony", "발코니2-2": "balcony",')).splitlines()
G = {"__name__": "build_shared"}
def _at(tag): return next(i for i, l in enumerate(SRCPY) if l.startswith("# ----") and tag in l)
def run_sec(start, end):
    a = 0 if start is None else _at(start)
    exec(compile("\n".join(SRCPY[a:_at(end)]), "build.py", "exec"), G)

run_sec(None, "openings from source parts")                          # profile, source geometry, zoning spaces, walls
spaces, fixed, walls, inserts = G["spaces"], G["fixed"], G["walls"], G["inserts"]
model = {"spaces": spaces, "fixed": fixed, "walls": walls}

# ---------------------------------------------------------------- profile additions (user answers)
UC = "user_confirmed"
P = G["profile"]
door_rules = [
    {"room": "현관", "to": "__core__", "width": 1100, "swing": "out", "position": "center"},
    {"room": "침실1", "to": ["거실", "주방/식당", "현관"], "width": 900, "position": "corner"},
    {"room": "침실2", "to": ["거실", "현관", "주방/식당"], "width": 900, "position": "corner"},
    {"room": "침실3", "to": ["거실", "현관", "주방/식당"], "width": 900, "position": "corner"},
    {"room": "욕실1", "to": ["현관", "거실", "주방/식당"], "width": 800},
    {"room": "팬트리", "to": ["주방/식당", "거실", "현관"], "width": 800, "position": "center"},
    {"room": "욕실2", "to": ["드레스룸", "침실1"], "width": 800},
    {"room": "드레스룸", "to": ["침실1"], "type": "open"},
    {"room": "하향식피난구", "to": ["발코니1"], "width": 750, "type": "sliding", "position": "entry", "jamb": 150},
]
win_rules = [  # profile: plan-relative side (+y = N) and width per room (user_confirmed: 원본 84A 값)
    {"room": "거실", "type": "double", "side": "S", "width": 3600},
    {"room": "침실1", "type": "double", "side": "S", "width": 1500},
    {"room": "침실2", "type": "double", "side": "S", "width": 1800},
    {"room": "침실3", "type": "double", "side": "S", "width": 1800},
    {"room": "주방/식당", "type": "double", "side": "N", "width": 1500},
    {"room": "드레스룸", "type": "double", "side": "N", "width": 1000},
    {"room": "하향식피난구", "type": "outdoor_unit", "side": "S", "width": 1000, "facing": "exterior"}]
WIDTHS = [1000, 1500, 1800, 3600]
P["doors"] = {"rules": {"value": door_rules, "status": UC}, "source": {"value": "rule", "status": UC}, "corridor_max_mm": {"value": 1800, "status": UC}, "jamb_mm": {"value": 100, "status": UC}, "corridor_tie": {"value": "living", "status": UC}, "position": {"value": {"침실·드레스룸·욕실": "corner", "현관·팬트리": "center", "하향식피난구": "entry(미지정, v006 유지)"}, "status": UC}}
P["windows"] = {"rules": {"value": win_rules, "status": UC}, "widths_mm": {"value": WIDTHS, "status": UC},
                "margin_mm": {"value": 300, "status": UC}, "source": {"value": "rule", "status": UC}}
P["bathroom"] = {"system": {"value": "ubr", "status": UC},
                 "rooms": {"value": {"욕실1": "UBR 공용욕실 1500x2200", "욕실2": "UBR 부부욕실 1600x2300"}, "status": UC},
                 "rule": {"value": "안목 최대 사각형, 문 반대 모서리", "status": UC}}
kcfg = {"room": "주방/식당", "layout": "I", "depth": 650, "fridge_position": "outside", "fridge_width": 900, "arrangement": "cooktop_window", "living": ["거실"], "min_len": 1800, "sink": "싱크", "cooktop": "쿡탑",
        "gap": 600, "table": "식탁-1300x800", "washer": {"block": "세탁기-850", "room": "발코니2", "priority": "exterior_first", "water_points": [[11905, 8406], [11755, 8406], [11395, 8400]]}}
P["kitchen_furniture"] = {"config": {"value": kcfg, "status": UC}}

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
run_sec("wall outlines", "room names from sheet")
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

CORRIDOR_MAX = 1800
DOOR_JAMB = 100   # profile: corner face -> opening (user_confirmed)
doors, door_issues = place_doors(model, [r for r in door_rules if r["room"] not in ("욕실1", "욕실2")], taken=taken, corridor_max=CORRIDOR_MAX, jamb=DOOR_JAMB, corridor_tie="living")
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

run_sec("wall outlines", "room names from sheet")                        # wall outlines, insulation, finish loops, dimensions (with openings)
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
    if name == "세탁기-850":   # back side measured from the reference instance (nearest wall face)
        sys.path.insert(0, SK + r"\unit-plan\scripts")
        from run_reference_unit import wall_normal_of
        wn = wall_normal_of(list(map(float, ins[8:12])), walls)
        if wn: nx, ny = inverse(rot, xs, wn); normal = (round(nx), round(ny))
    lib[name] = {"lbbox": lb, "rot": rot, "xs": xs, "normal": normal}
kit, kit_issues = place_kitchen(model, kcfg, lib, clear_loops, openings, [w["rect"] for w in walls])
fixtures = ubr + kit

# ---------------------------------------------------------------- model / profile
labels = [{"text": n[1], "at": [float(n[2]), float(n[3])]} for n in
          (l.rstrip("\n").split("\t") for l in open(JOB + r"\input\names_local.tsv", encoding="utf-8")) if n[0] == "실명"]
from upgeom import centroid as _c
for s in spaces:
    if s["name"] == "발코니2-2": labels.append({"text": "발코니2-2", "at": [round(_c(s["polygon"])[0]) - 400, round(_c(s["polygon"])[1])]})
model2 = {"version": 1, "unit": {"type": "84A", "variant": "basic", "mode": "rule-v010"}, "spaces": spaces, "fixed": fixed,
          "walls": walls, "openings": openings, "fixtures": fixtures, "insulation_runs": G["ins_runs"], "finish": finish,
          "dimensions": dims + clear_dims, "annotations": labels, "ubr_lib": ubr_lib,
          "issues": {"doors": door_issues, "windows": win_issues, "bathroom": bath_issues, "kitchen": kit_issues}}
os.makedirs(JOB + r"\v010", exist_ok=True)
json.dump(P, open(JOB + r"\v010\profile.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(model2, open(JOB + r"\v010\model.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=list)
# ---------------------------------------------------------------- LISP
DWG = "C:/temp/cj84a/outputs/cj84A-basic-v010.dwg"
OPS = "C:/temp/cj84a/operations_v010"
os.makedirs(OPS, exist_ok=True); os.makedirs(JOB + r"\v010\ops", exist_ok=True)
q, pts, loops_body = G["q"] if "q" in G else None, None, None
def q(s): return '"' + s.replace("\\", "/").replace('"', '\\"') + '"'
def pts(p): return "'(" + " ".join(f"({x:.1f} {y:.1f})" for x, y in p) + ")"
def op(step, body, locals_="ms o hs"):
    code = (f'(upc:run {q(DWG)} {q(OPS)} {q(step)} (quote (lambda (doc / {locals_}) (setq ms (vla-get-modelspace doc)) '
            + "\n ".join(body) + ")))")
    open(JOB + rf"\v010\ops\{step}.lsp", "w", encoding="utf-8").write(code + "\n")
def loops_body(loops, layer, hatch=None):
    out = []
    for k, lp in enumerate(loops):
        if not lp["outer"]: continue
        out.append(f'(setq o (upc:set (upc:pline ms {pts(lp["points"])} t) {q(layer)}) hs nil)')
        for h in loops:
            if not h["outer"] and h.get("parent") == k:
                out.append(f'(setq hs (cons (list (upc:set (upc:pline ms {pts(h["points"])} t) {q(layer)})) hs))')
        if hatch:
            pat, sc, ang, hl = hatch
            out.append(f'(upc:set (upc:hatch ms {q(pat)} {sc} {ang} (list o) hs) {q(hl)})')
    return out
def line(p1, p2, lay): return f'(upc:set (vla-addline ms (upc:pt {p1[0]:.1f} {p1[1]:.1f}) (upc:pt {p2[0]:.1f} {p2[1]:.1f})) {q(lay)})'
def P2(w, t, n): return (t, n) if w["orient"] == "H" else (n, t)

LAYERS = G["LAYERS"] if "LAYERS" in G else ["CONC", "WAL", "WAL_DRY", "A_HAT", "CEN_CON", "CEN_WALL", "INS", "FIN", "바닥타일", "DIM", "실명",
          "DOOR", "WIN", "FUR", "FUR_가구", "FUR_가전", "AA-XXXX-UBR", "Defpoint"]
BLOCKS = sorted({f["block"] for f in fixtures if f.get("block")} | {f["panel"]["block"] for f in ubr})
open(JOB + r"\v010\ops\std-901.lsp", "w", encoding="utf-8").write(
    f'(upc:run {q(DWG)} {q(OPS)} "std-901" (quote (lambda (doc / r) (setq r (upc:import doc {q(G["SRC"])} (list {" ".join(q(l) for l in LAYERS)}) '
    f'(list "MCDIM-50" "HAUD-100") (list "HAUD01") (list {" ".join(q(b) for b in BLOCKS)}))) (upc:write-utf8 "C:/temp/cj84a/v010/std-101.report.txt" r))))\n')

body = loops_body(groups["RC"], "CONC") + loops_body(groups["MAS"], "WAL", ("ANSI31", 10, 0, "A_HAT")) + loops_body(groups["DRY"], "WAL_DRY")
for w in walls:
    a, b = w["span"]
    body.append(line(P2(w, a, w["axis_coord"]), P2(w, b, w["axis_coord"]), "CEN_CON" if w["material"] == "RC" else "CEN_WALL"))
op("wall-901", body)

# doors: authored (jambs, leaf, 90deg arc) / sliding panels
body = []
for d in doors:
    w = wmap[d["wall"]]; t0, t1 = d["span"]; flo, fhi = face(w, "lo"), face(w, "hi")
    body += [line(P2(w, t0, flo), P2(w, t0, fhi), "DOOR"), line(P2(w, t1, flo), P2(w, t1, fhi), "DOOR")]
    if d["type"] == "sliding":
        ax = w["axis_coord"]; half = (t1 - t0) / 2
        for k, (s0, s1) in enumerate(((t0, t0 + half + 50), (t1 - half - 50, t1))):
            n0 = ax - 45 + k * 50
            body.append(f'(upc:set (upc:pline ms {pts([P2(w, s0, n0), P2(w, s1, n0), P2(w, s1, n0 + 40), P2(w, s0, n0 + 40)])} t) "DOOR")')
        continue
    sgn = 1 if d["swing_side"] == "hi" else -1
    fs = face(w, d["swing_side"]); ht = d["hinge_t"]; ot = t1 if ht == t0 else t0
    H = P2(w, ht, fs); E = P2(w, ht, fs + sgn * d["width_mm"]); C = P2(w, ot, fs)
    body.append(line(H, E, "DOOR"))
    a1 = math.atan2(E[1] - H[1], E[0] - H[0]); a2 = math.atan2(C[1] - H[1], C[0] - H[0])
    if (a2 - a1) % (2 * math.pi) > math.pi: a1, a2 = a2, a1
    body.append(f'(upc:set (vla-addarc ms (upc:pt {H[0]:.1f} {H[1]:.1f}) {d["width_mm"]} {a1:.6f} {a2:.6f}) "DOOR")')
op("door-901", body)

# windows: authored frame + glass lines
body = []
for wn in wins:
    w = wmap[wn["wall"]]; t0, t1 = wn["span"]; flo, fhi = face(w, "lo"), face(w, "hi")
    body.append(f'(upc:set (upc:pline ms {pts([P2(w, t0, flo), P2(w, t1, flo), P2(w, t1, fhi), P2(w, t0, fhi)])} t) "WIN")')
    th = fhi - flo
    for f in ((0.35, 0.65) if wn["type"] == "double" else (0.5,)):
        body.append(line(P2(w, t0, flo + th * f), P2(w, t1, flo + th * f), "WIN"))
op("win-901", body)

body = []
for t, loops in ins_loops.items():
    body += loops_body(loops, "INS", ("DASH", 10, 0, "INS"))
op("ins-901", body)

def insert(f, lay):
    return (f'(setq o (vla-insertblock ms (upc:pt {f["insert"][0]:.1f} {f["insert"][1]:.1f}) {q(f["block"])} {f["xscale"]} 1 1 '
            f'{math.radians(f["rotation_deg"]):.6f})) (upc:set o {q(lay)})')
op("bath-901", [insert(f, "FUR") for f in ubr] + [insert(dict(f["panel"]), f["panel"]["layer"]) for f in ubr], "ms o")
body = []
for f in kit:
    if f.get("block"):
        body.append(insert(f, {"sink": "FUR", "cooktop": "FUR", "table": "FUR_가구", "washer": "FUR_가전"}[f["kind"]]))
    else:
        x1, y1, x2, y2 = f["rect"]
        body.append(f'(upc:set (upc:pline ms {pts([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])} t) "FUR")')
        if f["kind"] == "fridge":
            body.append(f'(setq o (vla-addtext ms "냉장고" (upc:pt {(x1+x2)/2-180:.1f} {(y1+y2)/2:.1f}) 80)) (upc:set o "FUR")')
op("kit-901", body, "ms o")

body = []
for f in finish:
    for lp in f["loops"]:
        body.append(f'(upc:set (upc:pline ms {pts(lp)} t) "FIN")')
for f in finish:
    if f["name"] in ("발코니1", "발코니2", "발코니2-2", "하향식피난구"):
        for lp in f["loops"]:
            body.append(f'(setq o (upc:pline ms {pts(lp)} t)) (upc:set o "바닥타일") '
                        f'(setq h (vla-addhatch ms acHatchPatternTypeUserDefined "_USER" :vlax-true)) (vla-put-patternspace h 300) (vla-put-patterndouble h :vlax-true) '
                        f'(vla-appendouterloop h (upc:objarray (list o))) (vla-evaluate h) (upc:set h "바닥타일")')
op("fin-901", body, "ms o h")

body = []
for d in dims:
    if d["side"] == "S":
        off = -1500 if d["chain"] == "mc_overall" else -900
        body.append(f'(setq o (vla-adddimrotated ms (upc:pt {d["a"]} 0) (upc:pt {d["b"]} 0) (upc:pt {(d["a"]+d["b"])/2} {off}) 0)) (vla-put-stylename o "MCDIM-50") (upc:set o "DIM")')
    else:
        off = 16300 if d["chain"] == "mc_overall" else 15700
        body.append(f'(setq o (vla-adddimrotated ms (upc:pt 14630 {d["a"]}) (upc:pt 14630 {d["b"]}) (upc:pt {off} {(d["a"]+d["b"])/2}) (/ pi 2))) (vla-put-stylename o "MCDIM-50") (upc:set o "DIM")')
for d in clear_dims:
    ang = "0" if d["dir"] == "h" else "(/ pi 2)"
    loc = f'{(d["a"][0]+d["b"][0])/2} {d["a"][1]}' if d["dir"] == "h" else f'{d["a"][0]} {(d["a"][1]+d["b"][1])/2}'
    body.append(f'(setq o (vla-adddimrotated ms (upc:pt {d["a"][0]} {d["a"][1]}) (upc:pt {d["b"][0]} {d["b"][1]}) (upc:pt {loc}) {ang})) (vla-put-stylename o "HAUD-100") (upc:set o "DIM")')
op("dim-901", body, "ms o")
op("ann-901", [f'(setq o (vla-addtext ms {q(l["text"])} (upc:pt {l["at"][0]} {l["at"][1]}) 120)) (vla-put-stylename o "HAUD01") (upc:set o "실명")' for l in labels], "ms o")

print(json.dumps({"doors": [(d["room"], d["to"], d["wall"], d["width_mm"], d["type"]) for d in doors],
                  "windows": [(w["room"], w["facing"], w["wall"], w["width_mm"]) for w in wins],
                  "fixtures": [(f["kind"], f["space"], f.get("block"), [round(v) for v in (f.get("footprint") or f.get("rect"))]) for f in fixtures],
                  "issues": model2["issues"], "lib": {k: {kk: (vv if kk != "lbbox" else [round(x) for x in vv]) for kk, vv in v.items() if kk != "ref_insert"} for k, v in lib.items()}},
                 ensure_ascii=False, indent=0))
