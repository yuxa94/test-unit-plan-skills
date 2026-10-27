"""Run the unit-plan rule pipeline for one unit given a reference dump + zoning + profile (config JSON).

usage: python -I run_reference_unit.py <config.json>
Produces in config["job"]: model.json, profile.json, ops/<step>.lsp (std, wall, door, win, ins, bath, kit,
fin, dim, ann), reference_openings.json (for comparison) and prints a JSON summary.

config keys (see jobs/*/config.json for a full example):
  job, src_dwg, block, dump, names, zoning, out_dwg, ops_dir, op_suffix
  kinds            {name: room|wet|balcony|service|core|shaft}   (default room; PS->shaft, ELEV->core)
  walls            {"overrides": {"H:7090": [-20, 55, "DRY"], ...}, "party_axes": [["V", 0]]}
  insulation       {"exterior_direct": 155, "exterior_indirect": 110, "core": 110, "party_wall": 0}
  doors            {"rules": [...], "corridor_max": 1800, "jamb": 100}
  windows          {"rules": [...], "widths": [...]}
  bathroom         {"rules": [{"room", "body", "panel", "door_to", "door_width"}], "panel_dumps": {panel: tsv}}
  kitchen          place_kitchen cfg (+ "lib_blocks": [...])
  tiles            [space names with floor tile]
  extra_labels     [{"text", "space"}]   labels for spaces without a reference label
"""
import json, os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
SK = os.path.dirname(HERE)
ROOT = os.path.dirname(SK)
for d in ("unit-plan", "unit-plan-doors", "unit-plan-windows", "unit-plan-bathroom", "unit-plan-kitchen-furniture"):
    sys.path.insert(0, os.path.join(ROOT, d, "scripts"))
from rectunion import union_loops, _inside
from upgeom import local_bbox_from_instance, inverse, face, centroid
from place_doors import place_doors
from place_windows import place_windows
from place_bathroom import measure_ubr, place_ubr
from place_kitchen import place_kitchen, reserve_counter

BODY = {"CONC": "RC", "WAL": "MAS", "WAL_DRY": "DRY"}


def load_tsv(p):
    return [l.rstrip("\n").split("\t") for l in open(p, encoding="utf-8") if l.strip()]


# ---------------------------------------------------------------- walls: centerlines + measured offsets
def measure_offsets(o, c, a, b, body, cluster_gap=60, reach=350, prefer=None):
    """Outer faces of the wall body around centerline (o, c) over span [a, b] from parallel body lines.
    prefer: body layer to use exclusively when present (CONC for RC centerlines, so interior lining
    lines next to a concrete wall are not taken as the wall face)."""
    if prefer:
        pref = measure_offsets(o, c, a, b, [l for l in body if l[0] == prefer], cluster_gap, reach)
        if pref[0] is not None or pref[1] is not None:
            return pref
    sides = {+1: [], -1: []}
    on_axis = []
    for lay, x1, y1, x2, y2 in body:
        if o == "H" and abs(y1 - y2) < 1:
            cc, lo, hi = y1, min(x1, x2), max(x1, x2)
        elif o == "V" and abs(x1 - x2) < 1:
            cc, lo, hi = x1, min(y1, y2), max(y1, y2)
        else:
            continue
        if min(hi, b) - max(lo, a) < min(300, 0.3 * (b - a)): continue
        d = cc - c
        if abs(d) < 1: on_axis.append(lay); continue
        if abs(d) <= reach: sides[1 if d > 0 else -1].append((abs(d), lay))
    out, mats = {}, []
    clusters = {}
    for s, ds in sides.items():
        ds.sort()
        cl = []
        for d, l in ds:   # group lines into faces
            if cl and d - cl[-1][-1][0] <= cluster_gap: cl[-1].append((d, l))
            else: cl.append([(d, l)])
        clusters[s] = cl
        if not cl:
            out[s] = 0.0 if on_axis else None; continue
        out[s] = cl[0][-1][0]
        mats += [l for _, l in cl[0]]
    mats += on_axis
    mat = max(set(mats), key=mats.count) if mats else None
    # wall entirely on one side of its centerline: no lines on one side, two faces on the other
    for s in (1, -1):
        if out[-s] is None and not on_axis and len(clusters[s]) >= 2 and clusters[s][1][-1][0] - clusters[s][0][0][0] <= 350:
            near, far = clusters[s][0][0][0], clusters[s][1][-1][0]
            mats = [l for _, l in clusters[s][0] + clusters[s][1]]
            mat = max(set(mats), key=mats.count)
            # caller uses lo = -dlo, hi = dhi
            return (-near, far, BODY.get(mat)) if s == 1 else (far, -near, BODY.get(mat))
    return out[-1], out[1], BODY.get(mat)


def build_walls(lines, cfg):
    cen = []
    for lay, x1, y1, x2, y2 in lines:
        if lay not in ("CEN_CON", "CEN_WALL"): continue
        if abs(y1 - y2) < 1: cen.append(["H", round(y1), min(x1, x2), max(x1, x2), lay])
        else: cen.append(["V", round(x1), min(y1, y2), max(y1, y2), lay])
    body = [b for b in lines if b[0] in BODY]
    for c in cen:   # trim centerline overshoot to the wall-body span
        spans = []
        for lay, x1, y1, x2, y2 in body:
            o = "H" if abs(y1 - y2) < 1 else "V"
            if o != c[0]: continue
            cc, lo, hi = (y1, min(x1, x2), max(x1, x2)) if o == "H" else (x1, min(y1, y2), max(y1, y2))
            if abs(cc - c[1]) <= 320 and hi > c[2] and lo < c[3]: spans.append((lo, hi))
        if spans: c[2], c[3] = max(c[2], min(s[0] for s in spans)), min(c[3], max(s[1] for s in spans))
    overrides = {k: v for k, v in cfg.get("walls", {}).get("overrides", {}).items()}
    party = {tuple(p) for p in cfg.get("walls", {}).get("party_axes", [])}
    walls = []
    for i, (o, c, a, b, lay) in enumerate(cen):
        key = f"{o}:{c}"
        if key in overrides:
            lo, hi, mat = overrides[key]; basis = "override"
        else:
            dlo, dhi, mat = measure_offsets(o, c, a, b, body, prefer="CONC" if lay == "CEN_CON" else None)
            default = 100 if lay == "CEN_CON" else 50
            if (o, c) in party:   # neighbour draws the other half: mirror the measured side
                m = dhi if dhi else dlo
                dlo = dhi = m or default
            lo = -(dlo if dlo is not None else default)
            hi = dhi if dhi is not None else default
            mat = mat or ("RC" if lay == "CEN_CON" else "DRY")
            basis = "measured" if (dlo is not None or dhi is not None) else "default_by_layer"
        walls.append({"id": f"W{i+1}", "orient": o, "axis_coord": c, "span": [a, b], "lo": lo, "hi": hi, "material": mat,
                      "basis": basis, "layer": lay})
    for w in walls:   # extend ends to perpendicular walls within 300 mm (clean joins)
        for end in (0, 1):
            p = w["span"][end]; best = None
            for q in walls:
                if q["orient"] == w["orient"]: continue
                if not (q["span"][0] - 1 <= w["axis_coord"] <= q["span"][1] + 1): continue
                d = q["axis_coord"] - p
                if abs(d) <= 300 and (best is None or abs(d) < abs(best[0])): best = (d, q)
            if best:
                q = best[1]
                v = q["axis_coord"] + (q["hi"] if end == 1 else q["lo"])
                w["span"][end] = max(v, p) if end == 1 else min(v, p)
    for w in walls:
        a, b = w["span"]; c = w["axis_coord"]
        w["rect"] = [a, c + w["lo"], b, c + w["hi"]] if w["orient"] == "H" else [c + w["lo"], a, c + w["hi"], b]
    return walls


def wall_normal_of(bbox, walls, reach=200):
    """Direction pointing away from the wall a fixture's bbox side rests on (nearest parallel wall face)."""
    x1, y1, x2, y2 = bbox
    best = None
    for w in walls:
        r = w["rect"]
        if w["orient"] == "H" and min(x2, r[2]) - max(x1, r[0]) > 0.5 * (x2 - x1):
            for d, n in ((y1 - r[3], (0, 1)), (r[1] - y2, (0, -1))):
                if -50 <= d <= reach and (best is None or d < best[0]): best = (d, n)
        if w["orient"] == "V" and min(y2, r[3]) - max(y1, r[1]) > 0.5 * (y2 - y1):
            for d, n in ((x1 - r[2], (1, 0)), (r[0] - x2, (-1, 0))):
                if -50 <= d <= reach and (best is None or d < best[0]): best = (d, n)
    return best[1] if best else None


def cut_for(w, span):
    a, b = span
    return [a, w["rect"][1] - 5, b, w["rect"][3] + 5] if w["orient"] == "H" else [w["rect"][0] - 5, a, w["rect"][2] + 5, b]


def reference_openings(inserts, walls):
    """Reference doors/windows (source parts) matched to walls — used only for comparison."""
    out = []
    for ins in inserts:
        kind = {"DOOR": "door", "SINA-F-FRAME": "door", "WIN": "window"}.get(ins["layer"]) or \
               ("window" if ins["name"].startswith("실외기창") else None)
        if not kind: continue
        x1, y1, x2, y2 = ins["bbox"]; best = None
        for w in walls:
            c = w["axis_coord"]
            if w["orient"] == "H":
                dist = 0 if y1 <= c <= y2 else min(abs(c - y1), abs(c - y2)); ov = min(x2, w["span"][1]) - max(x1, w["span"][0])
            else:
                dist = 0 if x1 <= c <= x2 else min(abs(c - x1), abs(c - x2)); ov = min(y2, w["span"][1]) - max(y1, w["span"][0])
            if dist <= 300 and ov >= 300 and (best is None or (dist, -ov) < best[0]): best = ((dist, -ov), w)
        if best:
            w = best[1]
            span = [x1, x2] if w["orient"] == "H" else [y1, y2]
            out.append({"kind": kind, "block": ins["name"], "wall": w["id"], "span": span, "width_mm": round(span[1] - span[0])})
    return out


# ---------------------------------------------------------------- insulation / finish / dims
def space_at(spaces, fixed, x, y):
    for s in spaces + fixed:
        if _inside(x, y, s["polygon"]): return s
    return None


def insulation(walls, spaces, fixed, T, party, openings):
    rects, runs = {}, []
    for w in walls:
        if w["material"] == "DRY": continue
        a, b = w["span"]; c = w["axis_coord"]
        for side, fc in (("lo", c + w["lo"]), ("hi", c + w["hi"])):
            sgn = -1 if side == "lo" else 1
            other = c + (w["hi"] if side == "lo" else w["lo"])
            n = max(2, int((b - a) // 400))
            for k in range(n):
                t0 = a + (b - a) * k / n; t1 = a + (b - a) * (k + 1) / n; tm = (t0 + t1) / 2
                here = space_at(spaces, fixed, *((tm, fc + sgn * 60) if w["orient"] == "H" else (fc + sgn * 60, tm)))
                there = space_at(spaces, fixed, *((tm, other - sgn * 60) if w["orient"] == "H" else (other - sgn * 60, tm)))
                if not here or not here["heated"]: continue
                if there is None: exp = "party_wall" if (w["orient"], c) in party else "exterior_direct"
                elif there["heated"]: continue
                elif there["kind"] in ("core", "shaft"): exp = "core"
                else: exp = "exterior_indirect"
                t = T.get(exp)
                if not t: continue
                r = [t0, fc, t1, fc + sgn * t] if w["orient"] == "H" else [fc, t0, fc + sgn * t, t1]
                rects.setdefault(t, []).append(r)
                runs.append({"wall": w["id"], "side": side, "exposure": exp, "thickness_mm": t})
    wall_rects = [w["rect"] for w in walls]
    wmap = {w["id"]: w for w in walls}
    ins_cuts = []
    for o in openings:
        x1, y1, x2, y2 = o["cut"]
        ins_cuts.append([x1, y1 - 200, x2, y2 + 200] if wmap[o["wall"]]["orient"] == "H" else [x1 - 200, y1, x2 + 200, y2])
    loops = {t: union_loops(r, ins_cuts + wall_rects) for t, r in rects.items()}
    return loops, [r for rs in rects.values() for r in rs], runs


def poly_rects(poly):
    xs = sorted({p[0] for p in poly}); ys = sorted({p[1] for p in poly})
    return [[xs[i], ys[j], xs[i + 1], ys[j + 1]] for i in range(len(xs) - 1) for j in range(len(ys) - 1)
            if _inside((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2, poly)]


def finish_loops(spaces, walls, ins_all):
    wall_rects = [w["rect"] for w in walls]
    out = []
    for s in spaces:
        loops = [l for l in union_loops(poly_rects(s["polygon"]), wall_rects + ins_all) if l["outer"] and l["area"] > 0.3e6]
        s["clear_area_m2"] = round(sum(l["area"] for l in loops) / 1e6, 2)
        out.append({"space": s["id"], "name": s["name"], "loops": [l["points"] for l in loops]})
    return out


def mc_chains(walls, spaces):
    """MC chains along the south and east edges: axes of walls reaching the envelope edge."""
    xs = [p[0] for s in spaces for p in s["polygon"]]; ys = [p[1] for s in spaces for p in s["polygon"]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    sx = sorted({w["axis_coord"] for w in walls if w["orient"] == "V" and w["span"][0] <= y0 + 300 and x0 - 1 <= w["axis_coord"] <= x1 + 1})
    ey = sorted({w["axis_coord"] for w in walls if w["orient"] == "H" and w["span"][1] >= x1 - 300 and y0 - 1 <= w["axis_coord"] <= y1 + 1})
    def chain(v, side):
        if len(v) < 2: return []
        return [{"chain": "mc_overall", "side": side, "a": v[0], "b": v[-1]}] + \
               [{"chain": "mc_segment", "side": side, "a": a, "b": b} for a, b in zip(v, v[1:])]
    return chain(sx, "S") + chain(ey, "E"), (x0, x1, y0, y1)


def chord(loop, x, y, horizontal):
    hits = []
    for k in range(len(loop)):
        (ax, ay), (bx, by) = loop[k - 1], loop[k]
        if horizontal and ax == bx and min(ay, by) < y < max(ay, by): hits.append(ax)
        if not horizontal and ay == by and min(ax, bx) < x < max(ax, bx): hits.append(ay)
    c = x if horizontal else y
    lo = max((h for h in hits if h < c), default=None); hi = min((h for h in hits if h > c), default=None)
    return (lo, hi) if lo is not None and hi is not None else None


# ---------------------------------------------------------------- main
def main(cfg_path):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    J = cfg["job"]
    rows = load_tsv(cfg["dump"])
    lines = [(r[1], *map(float, r[2:6])) for r in rows if r[0] == "LINE"]
    ins_rows = [r for r in rows if r[0] == "INSERT"]
    inserts = [{"layer": r[1], "name": r[2], "bbox": list(map(float, r[8:12]))} for r in ins_rows if r[8]]
    zoning = json.load(open(cfg["zoning"], encoding="utf-8"))
    names = [r for r in load_tsv(cfg["names"])]

    kinds = cfg.get("kinds", {})
    spaces, fixed = [], []
    for s in zoning["spaces"]:
        k = kinds.get(s["name"]) or ("shaft" if s["name"].startswith("PS") or "EPS" in s["name"] else
                                     "core" if s["name"].startswith("ELEV") else "room")
        item = {"id": s["id"], "name": s["name"], "polygon": s["polygon"], "kind": k, "heated": k in ("room", "wet"),
                "area_m2": s["area_m2"], "boundary_meaning": "wall_centerline"}
        (fixed if k in ("core", "shaft") else spaces).append(item)

    walls = build_walls(lines, cfg)
    model = {"spaces": spaces, "fixed": fixed, "walls": walls}
    party = {tuple(p) for p in cfg.get("walls", {}).get("party_axes", [])}
    issues = {"walls": [f'{w["id"]} {w["orient"]}{w["axis_coord"]}: 실측 선 없음 → 기본 두께' for w in walls if w["basis"] == "default_by_layer"]}

    # pre-pass clear loops (no openings): insulation + finish depend only on walls
    _, ins_pre, _ = insulation(walls, spaces, fixed, cfg["insulation"], party, [])
    clear_pre = {f["name"]: f["loops"] for f in finish_loops(spaces, walls, ins_pre)}

    # reservations: kitchen counter wall, then UBRs (their doors), then doors, windows
    taken = {}
    kcfg = dict(cfg["kitchen"])
    res = reserve_counter(model, kcfg)
    if res:
        for wid, span in res["walls"]: taken.setdefault(wid, []).append(span)
        kcfg["reserved"] = {k: res[k] for k in ("orient", "n", "face", "span", "walls")}
    ubr_lib = {}
    by_name_ins = {}
    for r in ins_rows: by_name_ins.setdefault(r[2], r)
    for br in cfg["bathroom"]["rules"]:
        key = br["body"] + "|" + br["panel"]
        ubr_lib[key] = measure_ubr(by_name_ins[br["body"]], by_name_ins[br["panel"]], load_tsv(cfg["bathroom"]["panel_dumps"][br["panel"]]))
    ubr_rules = [{"room": br["room"], "ubr": br["body"] + "|" + br["panel"], "door_to": br["door_to"], "door_width": br["door_width"]}
                 for br in cfg["bathroom"]["rules"]]
    ubr, bath_doors, bath_issues = place_ubr(model, ubr_rules, ubr_lib, clear_pre)
    for d in bath_doors: taken.setdefault(d["wall"], []).append(d["span"])
    bath_rooms = {r["room"] for r in ubr_rules}
    dc = cfg["doors"]
    doors, door_issues = place_doors(model, [r for r in dc["rules"] if r["room"] not in bath_rooms], taken=taken,
                                     corridor_max=dc.get("corridor_max"), jamb=dc.get("jamb", 150),
                                     corridor_tie=dc.get("corridor_tie", "entry"))
    doors = bath_doors + doors
    for k, d in enumerate(doors): d["id"] = f"D{k + 1}"
    wins, win_issues = place_windows(model, cfg["windows"]["rules"], cfg["windows"].get("widths", []), taken=taken)
    wmap = {w["id"]: w for w in walls}
    openings = []
    for o in doors + wins:
        w = wmap[o["wall"]]
        o["cut"] = cut_for(w, o["span"])
        c = sum(o["span"]) / 2
        o["center"] = (c, w["axis_coord"]) if w["orient"] == "H" else (w["axis_coord"], c)
        openings.append(o)
    cuts = [o["cut"] for o in openings]

    groups, higher = {}, []
    for mat in ("RC", "MAS", "DRY"):
        rects = [w["rect"] for w in walls if w["material"] == mat]
        groups[mat] = union_loops(rects, cuts + higher)
        higher += rects
    ins_loops, ins_all, ins_runs = insulation(walls, spaces, fixed, cfg["insulation"], party, openings)
    finish = finish_loops(spaces, walls, ins_all)
    clear_loops = {f["name"]: f["loops"] for f in finish}

    # block library: instances in this unit first, then other reference dumps of the same project
    ref_walls = {"": walls}
    for extra in cfg.get("lib_dumps", []):
        er = [r for r in load_tsv(extra) if r[0] == "INSERT"]
        for r in er:
            if r[2] not in by_name_ins:
                by_name_ins[r[2]] = r; ref_walls[r[2]] = None   # wall normal unknown for borrowed instances
    lib, lib_notes = {}, []
    for name in kcfg.get("lib_blocks", [kcfg["sink"], kcfg["cooktop"], kcfg["table"]] + ([kcfg["washer"]["block"]] if kcfg.get("washer") else [])):
        r = by_name_ins.get(name)
        if not r: continue
        ip, rot, xs = (float(r[3]), float(r[4])), round(float(r[5])) % 360, round(float(r[6]))
        wb = list(map(float, r[8:12]))
        lb = local_bbox_from_instance(ip, rot, xs, wb)
        normal = None
        if name in (kcfg["sink"], kcfg["cooktop"]) or (kcfg.get("washer") and name == kcfg["washer"]["block"]):
            n = wall_normal_of(wb, walls) if ref_walls.get(name, walls) is not None else None
            if n is None:
                n = tuple(kcfg.get("ref_wall_normal", (1, 0))); lib_notes.append(f"{name}: 기준 벽 방향 추정 실패 → {n} 가정")
            nx, ny = inverse(rot, xs, n); normal = (round(nx), round(ny))
        lib[name] = {"lbbox": lb, "rot": rot, "xs": xs, "normal": normal}
    missing = [b for b in (kcfg["sink"], kcfg["cooktop"], kcfg["table"]) if b not in lib]
    kit, kit_issues = ([], [f"참조 블록 없음: {missing}"]) if missing else \
        place_kitchen(model, kcfg, lib, clear_loops, openings, [w["rect"] for w in walls])
    kit_issues = lib_notes + kit_issues
    fixtures = ubr + kit

    dims, env = mc_chains(walls, spaces)
    label_at = {n[1]: (float(n[2]) + 150, float(n[3]) - 300) for n in names if n[0] == "실명"}
    clear_dims = []
    for f in finish:
        if f["name"] not in cfg.get("clear_dim_rooms", []) or f["name"] not in label_at: continue
        x, y = label_at[f["name"]]
        for lp in f["loops"]:
            hc = chord(lp, x, y, True); vc = chord(lp, x, y, False)
            if hc and vc:
                clear_dims += [{"space": f["name"], "dir": "h", "a": [hc[0], y], "b": [hc[1], y]},
                               {"space": f["name"], "dir": "v", "a": [x + 600, vc[0]], "b": [x + 600, vc[1]]}]
                break
    labels = [{"text": n[1], "at": [float(n[2]), float(n[3])]} for n in names if n[0] == "실명"]
    for el in cfg.get("extra_labels", []):
        s = next((s for s in spaces if s["name"] == el["space"]), None)
        if s:
            cx, cy = centroid(s["polygon"]); labels.append({"text": el["text"], "at": [round(cx) - 400, round(cy)]})

    model.update({"version": 1, "unit": {"block": cfg["block"], "mode": "rule"}, "openings": openings, "fixtures": fixtures,
                  "insulation_runs": ins_runs, "finish": finish, "dimensions": dims + clear_dims, "annotations": labels,
                  "ubr_lib": ubr_lib,
                  "issues": {**issues, "doors": door_issues, "windows": win_issues, "bathroom": bath_issues, "kitchen": kit_issues}})
    json.dump(model, open(os.path.join(J, "model.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=list)
    json.dump(reference_openings(inserts, walls), open(os.path.join(J, "reference_openings.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(cfg, open(os.path.join(J, "profile.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    emit_ops(cfg, model, groups, ins_loops, finish, ubr, kit, doors, wins, walls, dims, clear_dims, labels, env)
    return model


# ---------------------------------------------------------------- LISP emission
def emit_ops(cfg, model, groups, ins_loops, finish, ubr, kit, doors, wins, walls, dims, clear_dims, labels, env):
    J = cfg["job"]; DWG = cfg["out_dwg"]; OPS = cfg["ops_dir"]; sfx = cfg.get("op_suffix", "001")
    os.makedirs(os.path.join(J, "ops"), exist_ok=True); os.makedirs(OPS, exist_ok=True)
    wmap = {w["id"]: w for w in walls}
    def q(s): return '"' + s.replace("\\", "/").replace('"', '\\"') + '"'
    def pts(p): return "'(" + " ".join(f"({x:.1f} {y:.1f})" for x, y in p) + ")"
    steps = []
    def op(step, body, locals_="ms o hs h old"):
        sid = f"{step}-{sfx}"
        code = (f'(upc:run {q(DWG)} {q(OPS)} {q(sid)} (quote (lambda (doc / {locals_}) (setq ms (vla-get-modelspace doc)) '
                + "\n ".join(body) + ")))")
        open(os.path.join(J, "ops", f"{sid}.lsp"), "w", encoding="utf-8").write(code + "\n"); steps.append(sid)
    def line(p1, p2, lay): return f'(upc:set (vla-addline ms (upc:pt {p1[0]:.1f} {p1[1]:.1f}) (upc:pt {p2[0]:.1f} {p2[1]:.1f})) {q(lay)})'
    def P2(w, t, n): return (t, n) if w["orient"] == "H" else (n, t)
    def loops_body(loops, layer, hatch=None):
        out = []
        for k, lp in enumerate(loops):
            if not lp["outer"]: continue
            out.append(f'(setq o (upc:set (upc:pline ms {pts(lp["points"])} t) {q(layer)}) hs nil)')
            for hh in loops:
                if not hh["outer"] and hh.get("parent") == k:
                    out.append(f'(setq hs (cons (list (upc:set (upc:pline ms {pts(hh["points"])} t) {q(layer)})) hs))')
            if hatch:
                pat, sc, ang, hl = hatch
                out.append(f'(upc:set (upc:hatch ms {q(pat)} {sc} {ang} (list o) hs) {q(hl)})')
        return out
    def insert(f, lay):
        return (f'(setq o (vla-insertblock ms (upc:pt {f["insert"][0]:.1f} {f["insert"][1]:.1f}) {q(f["block"])} {f["xscale"]} 1 1 '
                f'{math.radians(f["rotation_deg"]):.6f})) (upc:set o {q(lay)})')

    L = cfg["layers"]
    blocks = sorted({f["block"] for f in ubr + kit if f.get("block")} | {f["panel"]["block"] for f in ubr})
    sid = f"std-{sfx}"
    open(os.path.join(J, "ops", f"{sid}.lsp"), "w", encoding="utf-8").write(
        f'(upc:run {q(DWG)} {q(OPS)} {q(sid)} (quote (lambda (doc / r) (setq r (upc:import doc {q(cfg["src_dwg"])} (list {" ".join(q(l) for l in L["import"])}) '
        f'(list {" ".join(q(d) for d in L["dimstyles"])}) (list {q(L["textstyle"])}) (list {" ".join(q(b) for b in blocks)}))) '
        f'(upc:write-utf8 {q(J + "/" + sid + ".report.txt")} r))))\n')
    steps.append(sid)

    body = loops_body(groups["RC"], "CONC") + loops_body(groups["MAS"], "WAL", ("ANSI31", 10, 0, "A_HAT")) + loops_body(groups["DRY"], "WAL_DRY")
    for w in walls:
        a, b = w["span"]
        body.append(line(P2(w, a, w["axis_coord"]), P2(w, b, w["axis_coord"]), "CEN_CON" if w["material"] == "RC" else "CEN_WALL"))
    op("wall", body)

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
        fs = face(w, d["swing_side"]); ht = d["hinge_t"]; ot = t1 if abs(ht - t0) < 1 else t0
        H = P2(w, ht, fs); E = P2(w, ht, fs + sgn * d["width_mm"]); C = P2(w, ot, fs)
        body.append(line(H, E, "DOOR"))
        a1 = math.atan2(E[1] - H[1], E[0] - H[0]); a2 = math.atan2(C[1] - H[1], C[0] - H[0])
        if (a2 - a1) % (2 * math.pi) > math.pi: a1, a2 = a2, a1
        body.append(f'(upc:set (vla-addarc ms (upc:pt {H[0]:.1f} {H[1]:.1f}) {d["width_mm"]} {a1:.6f} {a2:.6f}) "DOOR")')
    op("door", body)

    body = []
    for wn in wins:
        w = wmap[wn["wall"]]; t0, t1 = wn["span"]; flo, fhi = face(w, "lo"), face(w, "hi")
        body.append(f'(upc:set (upc:pline ms {pts([P2(w, t0, flo), P2(w, t1, flo), P2(w, t1, fhi), P2(w, t0, fhi)])} t) "WIN")')
        th = fhi - flo
        for f in ((0.35, 0.65) if wn["type"] == "double" else (0.5,)):
            body.append(line(P2(w, t0, flo + th * f), P2(w, t1, flo + th * f), "WIN"))
    op("win", body)

    body = []
    for t, loops in ins_loops.items(): body += loops_body(loops, "INS", ("DASH", 10, 0, "INS"))
    op("ins", body)
    op("bath", [insert(f, "FUR") for f in ubr] + [insert(dict(f["panel"]), f["panel"]["layer"]) for f in ubr])
    body = []
    for f in kit:
        if f.get("block"):
            body.append(insert(f, {"sink": "FUR", "cooktop": "FUR", "table": "FUR_가구", "washer": "FUR_가전"}[f["kind"]]))
        else:
            x1, y1, x2, y2 = f["rect"]
            body.append(f'(upc:set (upc:pline ms {pts([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])} t) "FUR")')
    op("kit", body)
    body = []
    for f in finish:
        for lp in f["loops"]: body.append(f'(upc:set (upc:pline ms {pts(lp)} t) "FIN")')
    for f in finish:
        if f["name"] in cfg.get("tiles", []):
            for lp in f["loops"]:
                body.append(f'(setq o (upc:pline ms {pts(lp)} t)) (upc:set o "바닥타일") '
                            f'(setq h (vla-addhatch ms acHatchPatternTypeUserDefined "_USER" :vlax-true)) (vla-put-patternspace h 300) (vla-put-patterndouble h :vlax-true) '
                            f'(vla-appendouterloop h (upc:objarray (list o))) (vla-evaluate h) (upc:set h "바닥타일")')
    op("fin", body)
    x0, x1, y0, y1 = env
    body = []
    for d in dims:
        if d["side"] == "S":
            off = y0 - (1500 if d["chain"] == "mc_overall" else 900)
            body.append(f'(setq o (vla-adddimrotated ms (upc:pt {d["a"]} {y0}) (upc:pt {d["b"]} {y0}) (upc:pt {(d["a"]+d["b"])/2} {off}) 0)) (vla-put-stylename o {q(L["dim_mc"])}) (upc:set o "DIM")')
        else:
            off = x1 + (1700 if d["chain"] == "mc_overall" else 1100)
            body.append(f'(setq o (vla-adddimrotated ms (upc:pt {x1} {d["a"]}) (upc:pt {x1} {d["b"]}) (upc:pt {off} {(d["a"]+d["b"])/2}) (/ pi 2))) (vla-put-stylename o {q(L["dim_mc"])}) (upc:set o "DIM")')
    for d in clear_dims:
        ang = "0" if d["dir"] == "h" else "(/ pi 2)"
        loc = f'{(d["a"][0]+d["b"][0])/2} {d["a"][1]}' if d["dir"] == "h" else f'{d["a"][0]} {(d["a"][1]+d["b"][1])/2}'
        body.append(f'(setq o (vla-adddimrotated ms (upc:pt {d["a"][0]} {d["a"][1]}) (upc:pt {d["b"][0]} {d["b"][1]}) (upc:pt {loc}) {ang})) (vla-put-stylename o {q(L["dim_clear"])}) (upc:set o "DIM")')
    op("dim", body)
    op("ann", [f'(setq o (vla-addtext ms {q(l["text"])} (upc:pt {l["at"][0]} {l["at"][1]}) 120)) (vla-put-stylename o {q(L["textstyle"])}) (upc:set o "실명")' for l in labels])
    run_all = [f'(upc:new {q(DWG)} nil)'] + [f'(load {q(J + "/ops/" + s + ".lsp")})' for s in steps]
    open(os.path.join(J, "ops", "run_all.lsp"), "w", encoding="utf-8").write("(list\n " + "\n ".join(run_all) + ")\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    m = main(sys.argv[1])
    print(json.dumps({"spaces": len(m["spaces"]), "walls": len(m["walls"]),
                      "doors": [(o["room"], o["to"], o["wall"], [round(v) for v in o["span"]]) for o in m["openings"] if o["kind"] == "door"],
                      "windows": [(o["room"], o["wall"], o.get("side"), o["width_mm"]) for o in m["openings"] if o["kind"] == "window"],
                      "fixtures": [(f["kind"], f["space"], [round(v) for v in (f.get("footprint") or f.get("rect"))]) for f in m["fixtures"]],
                      "issues": m["issues"]}, ensure_ascii=False, indent=0))
