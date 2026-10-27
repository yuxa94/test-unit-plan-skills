"""청주 월명 84A 기본형 — unit-plan 전체 시험 실행용 빌드 스크립트.
profile.json + model.json + ops/<step>.lsp 생성. 실행은 MCP execute_lisp로 단계별로."""
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
SK =r"C:\Users\Planby Technologies\Desktop\2026\Autocad_mcp_test\unit-plan-skills"
sys.path.insert(0, SK + r"\unit-plan\scripts")
from rectunion import union_loops

JOB = r"C:\temp\cj84a"
DWG = "C:/temp/cj84a/outputs/cj84A-basic-v001.dwg"
OPS = "C:/temp/cj84a/operations"
SRC = "C:/temp/cj84a/input/cj_plan.dwg"
BLOCK = "U-84A(기본)"
os.makedirs(JOB + r"\ops", exist_ok=True)

# ---------------------------------------------------------------- profile (user answers 2026-10-26)
UC = "user_confirmed"
profile = {
    "project": {"name": {"value": "청주 월명", "status": UC}, "unit_type": {"value": "84A", "status": UC},
                "variant": {"value": "basic", "status": UC}, "drawing_scale": {"value": "1/50", "status": "project_confirmed"},
                "units": {"value": "mm", "status": "project_confirmed"}},
    "standards": {"layer_scheme": {"value": "custom(청주 원본)", "status": "proposed", "note": "원본 재현 시험이라 원본 레이어 이름 사용"},
                  "template_dwg": {"value": "input/cj_plan.dwg", "status": "project_confirmed"},
                  "text_style": {"value": "HAUD01", "status": "observed"}},
    "zoning": {"source": {"value": "U-84A(기본) 벽 중심선(CEN_CON/CEN_WALL) + 시트 실명", "status": UC},
               "boundary_meaning": {"value": "wall_centerline", "status": UC},
               "virtual_splits": {"value": "현관/거실, 거실/주방, 침실1/드레스룸", "status": UC}},
    "walls": {"assemblies": {"value": "원본 실측(외벽·코어측 RC250, 세대내 RC200, 경량100, 조적190)", "status": UC},
              "assignment": {"value": "explicit (중심선별 실측 오프셋)", "status": UC},
              "show_concrete_hatch": {"value": False, "status": "observed", "note": "원본: RC 무해치, 조적(WAL)만 ANSI31"}},
    "insulation": {"method": {"value": "internal", "status": "project_confirmed"},
                   "by_exposure": {"value": {"exterior_direct": 155, "exterior_indirect": 110, "party_wall": 0, "core": 110}, "status": UC,
                                   "note": "core=110은 간접외기로 본 가정(proposed)"},
                   "material": {"value": "압출법보온판 특호", "status": "project_confirmed"},
                   "dewproofing": {"value": {"thickness_mm": 10, "width_mm": None}, "status": "unresolved", "note": "폭 미확인 → 미작도"},
                   "symbol": {"value": "hatch_dash", "status": UC}},
    "doors": {"source": {"value": "원본 재현", "status": UC}},
    "windows": {"source": {"value": "원본 재현", "status": UC}},
    "bathroom": {"system": {"value": "ubr", "status": "observed"}, "source": {"value": "원본 재현", "status": UC}},
    "kitchen_furniture": {"source": {"value": "원본 재현", "status": UC}},
    "finish": {"floor_pattern": {"value": {"balcony": "_USER 300 grid"}, "status": "observed"}},
    "dimensions": {"dimstyle_mc": {"value": "MCDIM-50", "status": "observed"}, "dimstyle_clear": {"value": "HAUD-100", "status": "observed"}},
    "annotation": {"room_name_height": {"value": 120, "status": "observed"}, "sheet": {"value": None, "status": "unresolved"}},
}

# ---------------------------------------------------------------- source geometry
rows = [l.rstrip("\n").split("\t") for l in open(JOB + r"\input\84A_basic_L1.tsv", encoding="utf-8")]
lines = [(r[1], *map(float, r[2:6])) for r in rows if r[0] == "LINE"]
inserts = [{"layer": r[1], "name": r[2], "bbox": list(map(float, r[8:12]))} for r in rows if r[0] == "INSERT"]
zoning = json.load(open(JOB + r"\zoning.json", encoding="utf-8"))

KIND = {"발코니1": "balcony", "발코니2": "balcony", "하향식피난구": "service", "욕실1": "wet", "욕실2": "wet",
        "ELEV. 홀": "core", "PS": "shaft"}
spaces, fixed = [], []
for s in zoning["spaces"]:
    k = KIND.get(s["name"], "room")
    item = {"id": s["id"], "name": s["name"], "polygon": s["polygon"], "kind": k,
            "heated": k in ("room", "wet"), "area_m2": s["area_m2"], "boundary_meaning": "wall_centerline"}
    (fixed if k in ("core", "shaft") else spaces).append(item)

# ---------------------------------------------------------------- walls (explicit, measured offsets)
BODY = {"CONC", "WAL", "WAL_DRY"}
OFF = {  # (orient, coord): (lo, hi, material)   material: RC | MAS | DRY
    ("V", 0): (-125, 125, "RC"), ("H", 7150): (-125, 125, "RC"), ("H", 10335): (-200, 0, "RC"),
    ("H", 7010): (-125, 125, "RC"), ("V", 5570): (-125, 125, "RC"), ("H", 9000): (-125, 125, "RC"),
    ("V", 6340): (-112, 112, "RC"), ("V", 14630): (55, 305, "RC"), ("H", 0): (0, 200, "RC"),
    ("H", 9745): (-200, 0, "RC"), ("H", 8140): (-10, 190, "RC"), ("H", 1680): (-190, 10, "RC"),
    ("H", 4035): (-120, 80, "RC"), ("V", 12780): (-60, 60, "RC"),
    ("V", 12640): (-35, 65, "DRY"), ("V", 1780): (-35, 65, "DRY"), ("H", 5555): (-65, 35, "DRY"),
    ("H", 8145): (-15, 185, "MAS"), ("H", 8585): (-15, 175, "MAS"), ("V", 10080): (-15, 175, "MAS"),
    ("H", 1500): (-175, 15, "MAS"), ("H", 1675): (-175, 15, "MAS"),
    # PS walls beside 욕실2, measured 2026-10-26 (v003): drywall 75, faces 7070/7145 and 11320/11395
    ("H", 7090): (-20, 55, "DRY"), ("V", 11390): (-70, 5, "DRY"),
}
cen = []
for lay, x1, y1, x2, y2 in lines:
    if lay not in ("CEN_CON", "CEN_WALL"): continue
    if abs(y1 - y2) < 1: cen.append(["H", round(y1), min(x1, x2), max(x1, x2), lay])
    else: cen.append(["V", round(x1), min(y1, y2), max(y1, y2), lay])
body = [(("H" if abs(b[2] - b[4]) < 1 else "V"), b) for b in lines if b[0] in BODY]
for c in cen:  # trim overshoot to wall-body span (same rule as zoning)
    spans = []
    for o, (lay, x1, y1, x2, y2) in body:
        if o != c[0]: continue
        cc, lo, hi = (y1, min(x1, x2), max(x1, x2)) if o == "H" else (x1, min(y1, y2), max(y1, y2))
        if abs(cc - c[1]) <= 320 and hi > c[2] and lo < c[3]: spans.append((lo, hi))
    if spans: c[2], c[3] = max(c[2], min(s[0] for s in spans)), min(c[3], max(s[1] for s in spans))

walls = []
for i, (o, c, a, b, lay) in enumerate(cen):
    lo, hi, mat = OFF.get((o, c), (-100, 100, "RC") if lay == "CEN_CON" else (-50, 50, "DRY"))
    walls.append({"id": f"W{i+1}", "orient": o, "axis_coord": c, "span": [a, b], "lo": lo, "hi": hi, "material": mat,
                  "basis": "measured" if (o, c) in OFF else "default_by_layer"})
# extend each end to a perpendicular wall within 300 mm, through to its far face (clean joins)
for w in walls:
    for end in (0, 1):
        p = w["span"][end]
        best = None
        for q in walls:
            if q["orient"] == w["orient"]: continue
            if not (q["span"][0] - 1 <= w["axis_coord"] <= q["span"][1] + 1): continue
            d = q["axis_coord"] - p
            if abs(d) <= 300 and (best is None or abs(d) < abs(best[0])): best = (d, q)
        if best:
            q = best[1]
            w["span"][end] = q["axis_coord"] + (q["hi"] if end == 1 else q["lo"])
            w["span"][end] = max(w["span"][end], p) if end == 1 else min(w["span"][end], p)

def wall_rect(w):
    a, b = w["span"]; c = w["axis_coord"]
    return [a, c + w["lo"], b, c + w["hi"]] if w["orient"] == "H" else [c + w["lo"], a, c + w["hi"], b]
for w in walls: w["rect"] = wall_rect(w)

# ---------------------------------------------------------------- openings from source parts (bbox → nearest wall)
OPEN_LAYERS = {"DOOR": "door", "SINA-F-FRAME": "door", "WIN": "window"}
openings = []
for ins in inserts:
    kind = OPEN_LAYERS.get(ins["layer"]) or ("window" if ins["name"].startswith("실외기창") else None)
    if not kind: continue
    x1, y1, x2, y2 = ins["bbox"]
    best = None
    for w in walls:
        c = w["axis_coord"]
        if w["orient"] == "H":
            dist = 0 if y1 <= c <= y2 else min(abs(c - y1), abs(c - y2)); ov = min(x2, w["span"][1]) - max(x1, w["span"][0])
        else:
            dist = 0 if x1 <= c <= x2 else min(abs(c - x1), abs(c - x2)); ov = min(y2, w["span"][1]) - max(y1, w["span"][0])
        if dist <= 300 and ov >= 300 and (best is None or (dist, -ov) < best[0]): best = ((dist, -ov), w)
    if not best:
        openings.append({"id": f"O{len(openings)+1}", "kind": kind, "block": ins["name"], "wall": None, "bbox": ins["bbox"]}); continue
    w = best[1]
    span = [x1, x2] if w["orient"] == "H" else [y1, y2]
    cut = [span[0], w["rect"][1] - 5, span[1], w["rect"][3] + 5] if w["orient"] == "H" else [w["rect"][0] - 5, span[0], w["rect"][2] + 5, span[1]]
    openings.append({"id": f"O{len(openings)+1}", "kind": kind, "block": ins["name"], "wall": w["id"],
                     "span": span, "width_mm": round(span[1] - span[0]), "cut": cut, "bbox": ins["bbox"]})
cuts = [o["cut"] for o in openings if o.get("cut")]

# ---------------------------------------------------------------- wall outlines (priority RC > MAS > DRY)
groups = {}
higher = []
for mat in ("RC", "MAS", "DRY"):
    rects = [w["rect"] for w in walls if w["material"] == mat]
    groups[mat] = union_loops(rects, cuts + higher)
    higher += rects

# ---------------------------------------------------------------- insulation
def space_at(x, y):
    from rectunion import _inside
    for s in spaces + fixed:
        if _inside(x, y, s["polygon"]): return s
    return None
T = profile["insulation"]["by_exposure"]["value"]
ins_rects, ins_runs = {}, []
for w in walls:
    if w["material"] == "DRY": continue
    a, b = w["span"]; c = w["axis_coord"]
    for side, face in (("lo", c + w["lo"]), ("hi", c + w["hi"])):
        sgn = -1 if side == "lo" else 1
        other_face = c + (w["hi"] if side == "lo" else w["lo"])
        # sample along the wall: heated side = this side, exposure from the opposite side
        n = max(2, int((b - a) // 400))
        for k in range(n):
            t0 = a + (b - a) * k / n; t1 = a + (b - a) * (k + 1) / n; tm = (t0 + t1) / 2
            here = space_at(*( (tm, face + sgn * 60) if w["orient"] == "H" else (face + sgn * 60, tm) ))
            there = space_at(*( (tm, other_face - sgn * 60) if w["orient"] == "H" else (other_face - sgn * 60, tm) ))
            if not here or not here["heated"]: continue
            if there is None:
                exp = "party_wall" if (w["orient"], c) == ("V", 0) else "exterior_direct"
            elif there["heated"]: continue
            elif there["kind"] in ("core", "shaft"): exp = "core"
            else: exp = "exterior_indirect"
            t = T[exp]
            if not t: continue
            r = [t0, face, t1, face + sgn * t] if w["orient"] == "H" else [face, t0, face + sgn * t, t1]
            ins_rects.setdefault(t, []).append(r)
            ins_runs.append({"wall": w["id"], "side": side, "exposure": exp, "thickness_mm": t, "from_to": [round(t0), round(t1)]})
wall_rects = [w["rect"] for w in walls]
# openings must also cut the insulation band, which sits beyond the wall face
ins_cuts = []
for o in openings:
    if not o.get("cut"): continue
    x1, y1, x2, y2 = o["cut"]
    w = next(w for w in walls if w["id"] == o["wall"])
    ins_cuts.append([x1, y1 - 200, x2, y2 + 200] if w["orient"] == "H" else [x1 - 200, y1, x2 + 200, y2])
ins_loops = {t: union_loops(r, ins_cuts + wall_rects) for t, r in ins_rects.items()}
ins_all = [r for rs in ins_rects.values() for r in rs]

# ---------------------------------------------------------------- finish loops (room polygon − walls − insulation)
def poly_rects(poly):
    xs = sorted({p[0] for p in poly}); ys = sorted({p[1] for p in poly})
    from rectunion import _inside
    out = []
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            if _inside((xs[i] + xs[i+1]) / 2, (ys[j] + ys[j+1]) / 2, poly): out.append([xs[i], ys[j], xs[i+1], ys[j+1]])
    return out
finish = []
for s in spaces:
    loops = [l for l in union_loops(poly_rects(s["polygon"]), wall_rects + ins_all) if l["outer"] and l["area"] > 0.3e6]
    s["clear_area_m2"] = round(sum(l["area"] for l in loops) / 1e6, 2)
    finish.append({"space": s["id"], "name": s["name"], "loops": [l["points"] for l in loops]})

# ---------------------------------------------------------------- dimensions (MC = wall centerlines)
xs_s = [0, 3195, 6065, 10785, 12780, 14630]
ys_e = [0, 1500, 5555, 8145, 10335]
dims = [{"chain": "mc_overall", "side": "S", "a": 0, "b": 14630},
        *[{"chain": "mc_segment", "side": "S", "a": a, "b": b} for a, b in zip(xs_s, xs_s[1:])],
        {"chain": "mc_overall", "side": "E", "a": 0, "b": 10335},
        *[{"chain": "mc_segment", "side": "E", "a": a, "b": b} for a, b in zip(ys_e, ys_e[1:])]]
def chord(loop, x, y, horizontal):
    """Clear width through (x, y): nearest loop edges left/right (or below/above) of the point."""
    n = len(loop); hits = []
    for k in range(n):
        (ax, ay), (bx, by) = loop[k - 1], loop[k]
        if horizontal and ax == bx and min(ay, by) < y < max(ay, by): hits.append(ax)
        if not horizontal and ay == by and min(ax, bx) < x < max(ax, bx): hits.append(ay)
    c = x if horizontal else y
    lo = max((h for h in hits if h < c), default=None); hi = min((h for h in hits if h > c), default=None)
    return (lo, hi) if lo is not None and hi is not None else None

label_at = {}
for l in open(JOB + r"\input\names_local.tsv", encoding="utf-8"):
    f_ = l.rstrip("\n").split("\t")
    if f_[0] == "실명": label_at[f_[1]] = (float(f_[2]) + 150, float(f_[3]) - 300)   # just below the label
clear_dims = []
for f in finish:
    if f["name"] not in ("침실1", "침실2", "침실3", "거실", "주방/식당", "드레스룸") or f["name"] not in label_at: continue
    x, y = label_at[f["name"]]
    for lp in f["loops"]:
        hc = chord(lp, x, y, True); vc = chord(lp, x, y, False)
        if hc and vc:
            clear_dims.append({"space": f["name"], "dir": "h", "a": [hc[0], y], "b": [hc[1], y]})
            clear_dims.append({"space": f["name"], "dir": "v", "a": [x + 600, vc[0]], "b": [x + 600, vc[1]]})
            break

# ---------------------------------------------------------------- room names from sheet
names = [l.rstrip("\n").split("\t") for l in open(JOB + r"\input\names_local.tsv", encoding="utf-8")]
labels = [{"text": n[1], "at": [float(n[2]), float(n[3])]} for n in names if n[0] == "실명"]

model = {"version": 1, "unit": {"type": "84A", "variant": "basic", "source": BLOCK},
         "spaces": spaces, "fixed": fixed, "walls": walls, "openings": openings,
         "insulation_runs": ins_runs, "finish": finish, "dimensions": dims + clear_dims, "annotations": labels}
json.dump(profile, open(JOB + r"\profile.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(model, open(JOB + r"\model.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- LISP ops
def q(s): return '"' + s.replace("\\", "/").replace('"', '\\"') + '"'
def pts(p): return "'(" + " ".join(f"({x:.1f} {y:.1f})" for x, y in p) + ")"
def op(step, body, locals_="ms o hs"):
    code = (f'(upc:run {q(DWG)} {q(OPS)} {q(step)} (quote (lambda (doc / {locals_}) (setq ms (vla-get-modelspace doc)) '
            + "\n ".join(body) + ")))")
    open(JOB + rf"\ops\{step}.lsp", "w", encoding="utf-8").write(code + "\n")

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

LAYERS = ["CONC", "WAL", "WAL_DRY", "A_HAT", "CEN_CON", "CEN_WALL", "INS", "FIN", "바닥타일", "DIM", "실명",
          "DOOR", "SINA-F-FRAME", "WIN", "FUR", "FUR_가구", "FUR_가전", "F-FUR-설치", "수전", "AA-XXXX-UBR", "ETC", "A-ELE8", "Defpoint"]
open(JOB + r"\ops\std-001.lsp", "w", encoding="utf-8").write(
    f'(upc:run {q(DWG)} {q(OPS)} "std-001" (quote (lambda (doc / r) (setq r (upc:import doc {q(SRC)} (list {" ".join(q(l) for l in LAYERS)}) '
    f'(list "MCDIM-50" "HAUD-100") (list "HAUD01") nil)) (upc:write-utf8 "C:/temp/cj84a/std-001.report.txt" r))))\n')

body = loops_body(groups["RC"], "CONC") + loops_body(groups["MAS"], "WAL", ("ANSI31", 10, 0, "A_HAT")) + loops_body(groups["DRY"], "WAL_DRY")
for w in walls:
    a, b = w["span"]; c = w["axis_coord"]
    p1, p2 = ((a, c), (b, c)) if w["orient"] == "H" else ((c, a), (c, b))
    lay = "CEN_CON" if w["material"] == "RC" else "CEN_WALL"
    body.append(f'(upc:set (vla-addline ms (upc:pt {p1[0]} {p1[1]}) (upc:pt {p2[0]} {p2[1]})) {q(lay)})')
op("wall-001", body)

def copy_op(step, layer_pat, name_pat):
    open(JOB + rf"\ops\{step}.lsp", "w", encoding="utf-8").write(
        f'(upc:run {q(DWG)} {q(OPS)} {q(step)} (quote (lambda (doc / r) (setq r (upd:copy-parts doc {q(SRC)} {q(BLOCK)} {q(layer_pat)} {q(name_pat)})) '
        f'(upc:write-utf8 "C:/temp/cj84a/{step}.report.txt" r))))\n')
copy_op("door-001", "DOOR,SINA-F-FRAME", "*")
copy_op("win-001", "WIN,0", "WIN_*,실외기창*")
copy_op("bath-001", "FUR,AA-XXXX-UBR,수전", "UBR*,A$C4e4a4905,A$C84b07bde,수전,FD")
copy_op("kit-001", "FUR,F-FUR-설치,FUR_가구,FUR_가전,0,ETC,A-ELE8", "싱크,쿡탑,식탁*,세탁기*,A$Ca96da67e,*발코니배수구,A$C24669fbc,A$C8273e713")

body = []
for t, loops in ins_loops.items():
    body += loops_body(loops, "INS", ("DASH", 10, 0, "INS"))
op("ins-001", body)
# revision: INS layer holds only this skill's output, so replace it wholesale
op("ins-002", ['(setq old nil) (vlax-for e ms (if (= (vla-get-layer e) "INS") (setq old (cons e old)))) (foreach e old (vla-delete e))'] + body, "ms o hs old")

body = []
for f in finish:
    for lp in f["loops"]:
        body.append(f'(upc:set (upc:pline ms {pts(lp)} t) "FIN")')
TILE = {"발코니1", "발코니2", "하향식피난구"}
for f in finish:
    if f["name"] in TILE:
        for lp in f["loops"]:
            body.append(f'(setq o (upc:pline ms {pts(lp)} t)) (upc:set o "바닥타일") '
                        f'(setq h (vla-addhatch ms acHatchPatternTypeUserDefined "_USER" :vlax-true)) (vla-put-patternspace h 300) (vla-put-patterndouble h :vlax-true) '
                        f'(vla-appendouterloop h (upc:objarray (list o))) (vla-evaluate h) (upc:set h "바닥타일")')
op("fin-001", body, "ms o h")

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
op("dim-001", body, "ms o")
op("dim-002", ['(setq old nil) (vlax-for e ms (if (= (vla-get-layer e) "DIM") (setq old (cons e old)))) (foreach e old (vla-delete e))'] + body, "ms o old")

body = []
for l in labels:
    body.append(f'(setq o (vla-addtext ms {q(l["text"])} (upc:pt {l["at"][0]} {l["at"][1]}) 120)) (vla-put-stylename o "HAUD01") (upc:set o "실명")')
op("ann-001", body, "ms o")

print(json.dumps({
    "spaces": len(spaces), "fixed": len(fixed), "walls": len(walls),
    "walls_default_basis": [w["id"] for w in walls if w["basis"] != "measured"],
    "openings": [(o["block"], o["wall"], o.get("width_mm")) for o in openings],
    "wall_loops": {k: len(v) for k, v in groups.items()},
    "ins": {str(t): len(v) for t, v in ins_loops.items()},
    "exposures": sorted({r["exposure"] for r in ins_runs}),
    "clear_area": {s["name"]: s["clear_area_m2"] for s in spaces},
}, ensure_ascii=False, indent=0))
