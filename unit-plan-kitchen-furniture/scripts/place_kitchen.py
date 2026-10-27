"""Rule-based kitchen / appliance placement (unit-plan-kitchen-furniture).

place_kitchen(model, cfg, lib, clear_loops, openings) -> (fixtures, issues)
cfg: {"room": "주방/식당", "layout": "I", "depth": 650, "min_len": 1800,
      "fridge_position": "outside" | "counter_far_end" | "pantry", "fridge_width": 900, "fridge_depth": 750,
      "arrangement": "sink_window" | "cooktop_window", "living": ["거실"],
      "sink": "싱크", "cooktop": "쿡탑", "gap": 600, "table": "식탁-1300x800",
      "washer": {"block": "세탁기-850", "room": "발코니2"}}
lib[block] = {"lbbox", "rot", "xs", "normal": local unit vector pointing away from the wall (or None)}
Rules:
  counter  = reserved wall run (reserve_counter) or longest wall-backed edge free of openings (I layout)
  sink     = arrangement "sink_window": counter end nearer the kitchen window, cooktop `gap` beyond it;
             arrangement "cooktop_window": cooktop at the window end, sink at the end nearer `living`
  fridge   = from the profile: not on the counter / counter end opposite the sink / inside the pantry
  table    = centre of the largest clear rectangle left after the counter strip, long side parallel
  washer   = corner of the largest clear rectangle of its room, if the footprint fits
"""
from upgeom import max_rect_in_loop, world_bbox, apply, subtract_spans, _inside, wall_sides, by_name, face, loop_bbox


def reserve_counter(model, cfg, merge=150, gap=250):
    """Run BEFORE doors/windows: pick the kitchen's longest interior wall run (walls whose room-side
    faces are within `merge` mm and contiguous within `gap` mm count as one run) and return it, so
    door/window rules leave it free. Returns {"walls": [(wall_id, [t0, t1])], "orient", "n", "face", "span"}."""
    sides = wall_sides(model)
    room = by_name(model, cfg["room"])
    spaces = {s["id"]: s for s in model["spaces"] + model.get("fixed", [])}
    pieces = []
    for w in model["walls"]:
        for t0, t1, lo, hi in sides[w["id"]]:
            for mine, other, side in ((lo, hi, "lo"), (hi, lo, "hi")):
                if mine != room["id"] or other is None: continue
                o = spaces[other]
                if o["kind"] in ("balcony", "service") and not o["heated"]: continue
                n = (0, 1 if side == "hi" else -1) if w["orient"] == "H" else (1 if side == "hi" else -1, 0)
                pieces.append({"w": w, "t": [t0, t1], "orient": w["orient"], "n": n, "face": face(w, side)})
    runs = []
    for p in sorted(pieces, key=lambda p: (p["orient"], p["n"], p["t"][0])):
        r = runs[-1] if runs else None
        if r and r["orient"] == p["orient"] and r["n"] == p["n"] and abs(r["face0"] - p["face"]) <= merge and p["t"][0] - r["span"][1] <= gap:
            r["span"][1] = max(r["span"][1], p["t"][1]); r["walls"].append((p["w"]["id"], p["t"]))
            r["faces"].append(p["face"])
        else:
            runs.append({"orient": p["orient"], "n": p["n"], "face0": p["face"], "faces": [p["face"]],
                         "span": list(p["t"]), "walls": [(p["w"]["id"], p["t"])]})
    if not runs: return None
    best = max(runs, key=lambda r: r["span"][1] - r["span"][0])
    best["face"] = max(best["faces"]) if sum(best["n"]) > 0 else min(best["faces"])   # innermost face
    return best


def _edges(loop):
    for k in range(len(loop)):
        (ax, ay), (bx, by) = loop[k - 1], loop[k]
        yield (ax, ay), (bx, by)


def _place_against(L, n, t_start, along, face_c, orient):
    """Insert so the block's back (local normal side) sits on the wall face, starting at t_start."""
    for rot in (0, 90, 180, 270):
        wn = apply(rot, L["xs"], L["normal"])
        if (round(wn[0]), round(wn[1])) != n: continue
        wb = world_bbox(rot, L["xs"], L["lbbox"])
        if orient == "H":   # wall runs along x, normal is +-y
            tx = t_start
            ty = face_c if n[1] > 0 else face_c - (wb[3] - wb[1])
        else:
            ty = t_start
            tx = face_c if n[0] > 0 else face_c - (wb[2] - wb[0])
        ins = (tx - wb[0], ty - wb[1])
        fp = [tx, ty, tx + wb[2] - wb[0], ty + wb[3] - wb[1]]
        return rot, ins, fp
    return None


def place_kitchen(model, cfg, lib, clear_loops, openings, walls_rects):
    fixtures, issues = [], []
    loops = clear_loops.get(cfg["room"])
    if not loops:
        return fixtures, [f'{cfg["room"]}: 안목 영역 없음']
    loop = max(loops, key=len)
    all_clear = [lp for ls in clear_loops.values() for lp in ls]
    best = None
    res = cfg.get("reserved")
    if res:   # counter wall reserved before doors/windows (see reserve_counter)
        bb = loop_bbox(loop)
        lo_, hi_ = (bb[0], bb[2]) if res["orient"] == "H" else (bb[1], bb[3])
        f0, f1 = max(res["span"][0], lo_), min(res["span"][1], hi_)
        if f1 - f0 >= cfg["min_len"]:
            best = (f0, f1, res["face"], tuple(res["n"]), res["orient"])
    for (ax, ay), (bx, by) in ([] if best else _edges(loop)):
        orient = "H" if ay == by else "V"
        a, b = sorted((ax, bx)) if orient == "H" else sorted((ay, by))
        c = ay if orient == "H" else ax
        mid = (a + b) / 2
        # interior normal: test which side of the edge is inside the loop
        n = None
        for cand in ((0, 1), (0, -1)) if orient == "H" else ((1, 0), (-1, 0)):
            px, py = (mid + 0, c + cand[1] * 30) if orient == "H" else (c + cand[0] * 30, mid)
            if _inside(px, py, loop): n = cand
        if not n: continue
        ox, oy = (mid, c - n[1] * 30) if orient == "H" else (c - n[0] * 30, mid)
        if any(_inside(ox, oy, lp) for lp in all_clear):   # open side (virtual split) — no wall
            continue
        blocked = []
        for o in openings:
            r = o.get("cut")
            if not r: continue
            if orient == "H" and r[1] - 450 <= c <= r[3] + 450: blocked.append((r[0], r[2]))
            if orient == "V" and r[0] - 450 <= c <= r[2] + 450: blocked.append((r[1], r[3]))
        for f0, f1 in subtract_spans([a, b], blocked, gap=50):
            if f1 - f0 >= cfg["min_len"] and (best is None or f1 - f0 > best[1] - best[0]):
                best = (f0, f1, c, n, orient)
    if not best:
        return fixtures, [f'{cfg["room"]}: 길이 {cfg["min_len"]} 이상인 벽면(개구부 제외) 없음']
    f0, f1, c, n, orient = best
    d = cfg["depth"]
    strip = [f0, c, f1, c + n[1] * d] if orient == "H" else [c, f0, c + n[0] * d, f1]
    strip = [min(strip[0], strip[2]), min(strip[1], strip[3]), max(strip[0], strip[2]), max(strip[1], strip[3])]
    if cfg.get("layout") == "L":
        return _place_L(model, cfg, lib, clear_loops, openings, loop, all_clear, best, strip, fixtures, issues)
    fixtures.append({"kind": "counter", "space": cfg["room"], "rect": strip, "basis": "rule: 가장 긴 벽면(I형)"})
    # which counter end gets the sink: profile `arrangement`
    #   "sink_window"    : sink at the end nearer the kitchen window, cooktop `gap` beyond it
    #   "cooktop_window" : cooktop at the window (ventilation) end, sink at the end nearer the
    #                      dining/living side (`living` rooms, default 거실); both 100 mm from their ends
    def end_pt(t): return (t, c) if orient == "H" else (c, t)
    def near(t, pts): return min((end_pt(t)[0] - p[0]) ** 2 + (end_pt(t)[1] - p[1]) ** 2 for p in pts)
    wins = [o["center"] for o in openings if o["kind"] == "window" and o.get("room") == cfg["room"] and o.get("center")]
    arrangement = cfg.get("arrangement", "sink_window")
    S, K = lib[cfg["sink"]], lib[cfg["cooktop"]]
    sw = world_bbox(S["rot"], S["xs"], S["lbbox"]); sink_len = max(sw[2] - sw[0], sw[3] - sw[1])
    kw = world_bbox(K["rot"], K["xs"], K["lbbox"]); ck_len = max(kw[2] - kw[0], kw[3] - kw[1])
    window_at_f1 = (near(f1, wins) <= near(f0, wins)) if wins else None
    if arrangement == "cooktop_window":
        from upgeom import centroid
        living = [centroid(s["polygon"]) for s in model["spaces"] if s["name"] in cfg.get("living", ["거실"])]
        sink_at_f1 = (near(f1, living) <= near(f0, living)) if living else (not window_at_f1 if window_at_f1 is not None else True)
        sink_basis = "rule: 식탁·거실 쪽 끝"
        if window_at_f1 is None:
            issues.append("쿡탑: 주방 창 없음 → 싱크 반대쪽 끝에 둠")
            ck_at_f1 = not sink_at_f1; ck_basis = "rule: 창 없음 → 싱크 반대쪽 끝"
        else:
            ck_at_f1 = window_at_f1; ck_basis = "rule: 창(환기) 쪽 끝"
            if ck_at_f1 == sink_at_f1:
                issues.append("싱크·쿡탑: 창 쪽 끝과 거실 쪽 끝이 같음 → 싱크를 반대쪽 끝으로 옮김")
                sink_at_f1 = not ck_at_f1
        t_sink = f1 - 100 - sink_len if sink_at_f1 else f0 + 100
        t_ck = f1 - 100 - ck_len if ck_at_f1 else f0 + 100
        if abs((t_sink + sink_len / 2) - (t_ck + ck_len / 2)) < (sink_len + ck_len) / 2 + cfg["gap"]:
            issues.append(f'싱크·쿡탑: 간격 {cfg["gap"]} 미확보')
    else:
        if window_at_f1 is not None:
            sink_at_f1, sink_basis = window_at_f1, "rule: 창 쪽 끝"
        else:
            sink_at_f1, sink_basis = True, "rule: 창 없음 → 조리대 끝"
        ck_basis = "rule: 싱크에서 gap"
        if sink_at_f1:
            t_sink = f1 - 100 - sink_len; t_ck = t_sink - cfg["gap"] - ck_len
        else:
            t_sink = f0 + 100; t_ck = t_sink + sink_len + cfg["gap"]
    # fridge from the profile: outside (not on the counter) | counter_far_end | pantry
    fw = cfg.get("fridge_width", 900)
    pos = cfg.get("fridge_position", "outside")
    fr = None
    if pos == "counter_far_end":
        fr = [f0, f0 + fw] if sink_at_f1 else [f1 - fw, f1]
        rect_f = [fr[0], strip[1], fr[1], strip[3]] if orient == "H" else [strip[0], fr[0], strip[2], fr[1]]
        fixtures.append({"kind": "fridge", "space": cfg["room"], "rect": rect_f, "basis": "profile: 조리대 싱크 반대쪽 끝"})
    elif pos == "pantry":
        pl = clear_loops.get(cfg.get("pantry", "팬트리"))
        r3 = max_rect_in_loop(max(pl, key=len)) if pl else None
        fd = cfg.get("fridge_depth", 750)
        if r3 and min(r3[2] - r3[0], r3[3] - r3[1]) >= min(fw, fd) and max(r3[2] - r3[0], r3[3] - r3[1]) >= max(fw, fd):
            wide = (r3[2] - r3[0]) >= (r3[3] - r3[1])
            rect_f = [r3[0], r3[1], r3[0] + (fw if wide else fd), r3[1] + (fd if wide else fw)]
            fixtures.append({"kind": "fridge", "space": cfg.get("pantry", "팬트리"), "rect": rect_f, "basis": "profile: 팬트리"})
        else:
            issues.append(f'냉장고: 팬트리 안목에 {fw}x{fd} 자리 없음')
    else:
        issues.append("냉장고: 프로파일상 조리대 밖 — 자리 미작도(위치 미정)")
    for name, p, blk, t, ln in (("sink", _place_against(S, n, t_sink, None, c, orient), cfg["sink"], t_sink, sink_len),
                                ("cooktop", _place_against(K, n, t_ck, None, c, orient), cfg["cooktop"], t_ck, ck_len)):
        if not p:
            issues.append(f'{name}: 블록 방향을 벽 법선 {n}에 맞출 수 없음'); continue
        if t < f0 or t + ln > f1:
            issues.append(f'{name}: 조리대 길이 부족(조리대 밖으로 나감)')
        if fr and t < fr[1] and t + ln > fr[0]:
            issues.append(f'{name}: 냉장고 자리와 겹침')
        rot, ins, fp = p
        fixtures.append({"kind": name, "space": cfg["room"], "block": blk, "insert": list(ins), "rotation_deg": rot,
                         "xscale": lib[blk]["xs"], "footprint": fp, "basis": sink_basis if name == "sink" else ck_basis})
    _table_and_washer(model, cfg, lib, clear_loops, loop, [(strip, n, orient)], orient, fixtures, issues)
    return fixtures, issues


def _leg_end(loop, all_clear, openings, coord, orient2, t_from, direction, tol=150):
    """Wall-backed free length of the loop edge near line `coord` (orientation orient2, within `tol`;
    the clear face can sit a little inside the end of leg 1), starting near t_from and running in
    `direction` (+1/-1). Returns (far end coordinate, actual edge coordinate) or None."""
    found = []
    for (ax, ay), (bx, by) in _edges(loop):
        if orient2 == "H" and ay == by and abs(ay - coord) <= tol:
            a, b = sorted((ax, bx)); ec = ay
        elif orient2 == "V" and ax == bx and abs(ax - coord) <= tol:
            a, b = sorted((ay, by)); ec = ax
        else:
            continue
        if not (a - tol <= t_from <= b + tol): continue
        found.append((b - a, a, b, ec))
    for _, a, b, coord in sorted(found, reverse=True):
        mid = (a + b) / 2
        # wall-backed: the point just outside the edge is not in any room's clear area
        for s in (1, -1):
            px, py = (mid, coord + s * 30) if orient2 == "H" else (coord + s * 30, mid)
            if _inside(px, py, loop):
                ox, oy = (mid, coord - s * 30) if orient2 == "H" else (coord - s * 30, mid)
                if any(_inside(ox, oy, lp) for lp in all_clear): return None
        blocked = []
        for o in openings:
            r = o.get("cut")
            if not r: continue
            if orient2 == "H" and r[1] - 450 <= coord <= r[3] + 450: blocked.append((r[0], r[2]))
            if orient2 == "V" and r[0] - 450 <= coord <= r[2] + 450: blocked.append((r[1], r[3]))
        for f0, f1 in subtract_spans([a, b], blocked, gap=50):
            if f0 - tol <= t_from <= f1 + tol:
                return (f1 if direction > 0 else f0), coord
    return None


def _place_L(model, cfg, lib, clear_loops, openings, loop, all_clear, best, strip1, fixtures, issues):
    """ㄱ자형: leg 1 = reserved/longest wall (cooktop), leg 2 = the perpendicular wall at the leg-1 end
    where a real wall turns the corner (sink). The depth x depth corner square stays empty; both
    fixtures keep `corner_offset` from the corner square."""
    f0, f1, c, n, orient = best
    d = cfg["depth"]; off = cfg.get("corner_offset", 400)
    orient2 = "V" if orient == "H" else "H"
    S, K = lib[cfg["sink"]], lib[cfg["cooktop"]]
    sw = world_bbox(S["rot"], S["xs"], S["lbbox"]); sink_len = max(sw[2] - sw[0], sw[3] - sw[1])
    kw = world_bbox(K["rot"], K["xs"], K["lbbox"]); ck_len = max(kw[2] - kw[0], kw[3] - kw[1])
    dir2 = n[0] if orient == "V" else n[1]          # leg 2 runs into the room, away from leg 1's wall
    cands = []
    for e0, back in ((f1, -1), (f0, +1)):            # corner at f1 -> leg-2 normal points back toward f0
        r = _leg_end(loop, all_clear, openings, e0, orient2, c, dir2)
        if r is None: continue
        far, e = r                                     # e = actual clear face of the leg-2 wall
        length = abs(far - c)
        if length >= d + off + sink_len + 100:
            cands.append((length, e, back, far))
    if not cands:
        cfg2 = dict(cfg); cfg2["layout"] = "I"
        fx, iss = place_kitchen(model, cfg2, lib, clear_loops, openings, [])
        return fx, ["ㄱ자 주방: 첫 번째 벽 끝에서 꺾이는 실제 벽(개구부 제외)이 싱크를 둘 만큼 길지 않음 → I형으로 배치"] + iss
    length, e, back, far = max(cands)
    # leg 1 ends at the leg-2 face
    if back < 0: f1 = min(f1, e)
    else: f0 = max(f0, e)
    strip1 = [f0, c, f1, c + n[1] * d] if orient == "H" else [c, f0, c + n[0] * d, f1]
    strip1 = [min(strip1[0], strip1[2]), min(strip1[1], strip1[3]), max(strip1[0], strip1[2]), max(strip1[1], strip1[3])]
    n2 = (0, back) if orient2 == "H" else (back, 0)
    # counters: leg 1 full; leg 2 from leg-1's wall face to its far end
    a2, b2 = sorted((c, far))
    strip2 = [a2, e, b2, e + n2[1] * d] if orient2 == "H" else [e, a2, e + n2[0] * d, b2]
    strip2 = [min(strip2[0], strip2[2]), min(strip2[1], strip2[3]), max(strip2[0], strip2[2]), max(strip2[1], strip2[3])]
    fixtures.append({"kind": "counter", "space": cfg["room"], "rect": strip1, "basis": "rule: ㄱ자 첫 번째 벽(가장 긴 벽)"})
    fixtures.append({"kind": "counter", "space": cfg["room"], "rect": strip2, "basis": "rule: ㄱ자 두 번째 벽(꺾이는 벽)"})
    # cooktop on leg 1 next to the corner square, sink on leg 2 next to the corner square
    t_ck = (e - d - off - ck_len) if back < 0 else (e + d + off)
    t_sink = (c + dir2 * (d + off)) if dir2 > 0 else (c - d - off - sink_len)
    legs = {"sink": (S, n2, t_sink, e, orient2, sink_len, (a2, b2), "rule: ㄱ자 두 번째 벽, 코너에서 %d" % off),
            "cooktop": (K, n, t_ck, c, orient, ck_len, (f0, f1), "rule: ㄱ자 첫 번째 벽, 코너에서 %d" % off)}
    if cfg.get("l_sink_leg", "secondary") == "primary":
        legs["sink"], legs["cooktop"] = (S, n, (e - d - off - sink_len) if back < 0 else (e + d + off), c, orient, sink_len, (f0, f1), "rule: ㄱ자 첫 번째 벽"), \
                                        (K, n2, (c + dir2 * (d + off)) if dir2 > 0 else (c - d - off - ck_len), e, orient2, ck_len, (a2, b2), "rule: ㄱ자 두 번째 벽")
    for name in ("sink", "cooktop"):
        L, nn, t, face_c, ori, ln, (lo, hi), basis = legs[name]
        p = _place_against(L, nn, t, None, face_c, ori)
        if not p:
            issues.append(f'{name}: 블록 방향을 벽 법선 {nn}에 맞출 수 없음'); continue
        if t < lo - 1 or t + ln > hi + 1:
            issues.append(f'{name}: ㄱ자 조리대 길이 부족(조리대 밖으로 나감)')
        rot, ins, fp = p
        fixtures.append({"kind": name, "space": cfg["room"], "block": cfg[name], "insert": list(ins), "rotation_deg": rot,
                         "xscale": L["xs"], "footprint": fp, "basis": basis})
    if cfg.get("fridge_position", "outside") == "outside":
        issues.append("냉장고: 프로파일상 조리대 밖 — 자리 미작도(위치 미정)")
    elif cfg.get("fridge_position") == "counter_far_end":
        issues.append("냉장고: ㄱ자형에서 counter_far_end는 아직 미지원 — 미작도")
    _table_and_washer(model, cfg, lib, clear_loops, loop, [(strip1, n, orient), (strip2, n2, orient2)], orient, fixtures, issues)
    return fixtures, issues


def _table_and_washer(model, cfg, lib, clear_loops, loop, strips, orient, fixtures, issues):
    """Table: centre of the largest clear rectangle after every counter strip (+900 aisle);
    washer: corner of the largest clear rectangle of its room."""
    rect = max_rect_in_loop(loop)
    for strip, n, ori in strips:
        if ori == "H":
            if n[1] > 0: rect[1] = max(rect[1], strip[3] + 900)
            else: rect[3] = min(rect[3], strip[1] - 900)
        else:
            if n[0] > 0: rect[0] = max(rect[0], strip[2] + 900)
            else: rect[2] = min(rect[2], strip[0] - 900)
    T = lib[cfg["table"]]
    tb = world_bbox(0, T["xs"], T["lbbox"]); long_x = (tb[2] - tb[0]) >= (tb[3] - tb[1])
    rot_t = 0 if (orient == "H") == long_x else 90
    wb = world_bbox(rot_t, T["xs"], T["lbbox"])
    w, h = wb[2] - wb[0], wb[3] - wb[1]
    if rect[2] - rect[0] >= w and rect[3] - rect[1] >= h:
        cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
        fixtures.append({"kind": "table", "space": cfg["room"], "block": cfg["table"], "insert": [cx - w / 2 - wb[0], cy - h / 2 - wb[1]],
                         "rotation_deg": rot_t, "xscale": T["xs"], "footprint": [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], "basis": "rule"})
    else:
        issues.append(f'식탁: 조리대 앞 900 통로를 두면 {round(rect[2]-rect[0])}x{round(rect[3]-rect[1])} 남아 {round(w)}x{round(h)} 불가')
    if cfg.get("washer"):
        place_washer(model, cfg["washer"], lib, clear_loops, fixtures, issues)


def place_washer(model, wcfg, lib, clear_loops, fixtures, issues):
    """Washer in wcfg["room"]. Candidates: every rotation and every alignment of the footprint to the
    clear-loop coordinates that fits inside the loop. Ranking by wcfg["priority"]:
      "exterior_first" (default): back against an exterior wall first, then nearest water point
      "water_first"             : nearest water point first, then exterior wall
    then more sides against walls (corner). water_points: [[x, y], ...] (수전·배수, profile)."""
    from upgeom import space_at
    from place_bathroom import poly_in_loop
    def fits(lp, r): return poly_in_loop([(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])], lp)
    loops = clear_loops.get(wcfg["room"])
    if not loops:
        issues.append(f'세탁기: {wcfg["room"]} 안목 영역 없음'); return
    loop = max(loops, key=len)
    W = lib[wcfg["block"]]
    water = [tuple(p) for p in wcfg.get("water_points", [])]
    prio = wcfg.get("priority", "exterior_first")
    xs_v = sorted({p[0] for p in loop}); ys_v = sorted({p[1] for p in loop})
    best = None
    for rot in (0, 90, 180, 270):
        wb = world_bbox(rot, W["xs"], W["lbbox"]); w, h = wb[2] - wb[0], wb[3] - wb[1]
        # back side of the block (measured from the reference: lib normal points away from its wall)
        back = None
        if W.get("normal"):
            nw = apply(rot, W["xs"], W["normal"]); back = (-round(nw[0]), -round(nw[1]))
        for x0 in set(xs_v + [x - w for x in xs_v]):
            for y0 in set(ys_v + [y - h for y in ys_v]):
                fp = [x0, y0, x0 + w, y0 + h]
                if not fits(loop, fp): continue
                cx, cy = x0 + w / 2, y0 + h / 2
                backs, ext, back_ok = 0, False, back is None
                for d_, (px, py), (qx, qy) in (((0, -1), (cx, y0 - 30), (cx, y0 - 400)), ((0, 1), (cx, y0 + h + 30), (cx, y0 + h + 400)),
                                               ((-1, 0), (x0 - 30, cy), (x0 - 400, cy)), ((1, 0), (x0 + w + 30, cy), (x0 + w + 400, cy))):
                    if _inside(px, py, loop): continue          # this side is free, not against the boundary
                    backs += 1
                    is_back = back is None or d_ == back
                    if d_ == back: back_ok = True
                    if is_back and space_at(model, qx, qy) is None: ext = True   # beyond the back wall is outside the unit
                if not back_ok: continue                         # the block's back must rest on a wall
                dist = min((((cx - a) ** 2 + (cy - b) ** 2) ** 0.5 for a, b in water), default=1e9)
                key = (not ext, dist, -backs) if prio == "exterior_first" else (dist, not ext, -backs)
                if best is None or key < best[0]:
                    best = (key, rot, fp, wb, ext, dist, backs)
    if not best:
        issues.append(f'세탁기: {wcfg["room"]} 안목에 {wcfg["block"]} 들어갈 자리 없음'); return
    key, rot, fp, wb, ext, dist, backs = best
    basis = ("외벽 등대기" if ext else "외벽 없음") + (f", 수전·배수까지 {round(dist)}" if dist < 1e9 else ", 수전 정보 없음")
    if not ext: issues.append(f'세탁기: {wcfg["room"]}에서 외벽에 붙는 자리 없음 → {basis}')
    fixtures.append({"kind": "washer", "space": wcfg["room"], "block": wcfg["block"], "insert": [fp[0] - wb[0], fp[1] - wb[1]],
                     "rotation_deg": rot, "xscale": W["xs"], "footprint": fp, "basis": f"rule({prio}): {basis}"})
