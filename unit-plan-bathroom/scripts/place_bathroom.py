"""Rule-based UBR placement (unit-plan-bathroom).

A UBR is two blocks placed together: a body block (fixtures, door arc) and a panel block (layer like
AA-XXXX-UBR) holding the installation outline (closed polyline, includes tolerance) and the panel
walls (open polylines whose end gap is the UBR door). Both are measured once from a reference
instance (`measure_ubr`) and expressed in the body block's local frame.

place_ubr(model, rules, lib, clear_loops) -> (fixtures, doors, issues)
rules: [{"room": "욕실1", "ubr": "<lib key>", "door_to": ["현관", "거실"], "door_width": 800}, ...]
Rule:
  1. every rotation/mirror and every alignment of the outline bbox to the clear-loop coordinates is tried;
  2. the real outline (not its bbox) must lie inside the room's clear loop;
  3. the UBR door gap must sit on a wall whose other side is one of `door_to` (walkable room);
  4. ties: reference mirror/rotation first.
The bathroom door is then taken from the UBR door gap (centre and wall), width `door_width`,
swinging into the bathroom. Blocks are never scaled.
"""
from upgeom import apply, inverse, world_bbox, loop_bbox, _inside, space_at, face

TOL = 2  # mm


# ---------------------------------------------------------------- transforms
def _affine_from(f):
    """Express an affine map f (built from rot/mirror) as (rot, xs, offset)."""
    b = f((0, 0)); ex = f((1, 0)); ey = f((0, 1))
    ex = (round(ex[0] - b[0]), round(ex[1] - b[1])); ey = (round(ey[0] - b[0]), round(ey[1] - b[1]))
    for rot in (0, 90, 180, 270):
        for xs in (1, -1):
            if apply(rot, xs, (1, 0)) == ex and apply(rot, xs, (0, 1)) == ey:
                return rot, xs, b
    raise ValueError("not an orthogonal transform")


def measure_ubr(body_row, panel_row, panel_dump):
    """body_row/panel_row: INSERT rows of the reference unit dump (name, ins x, ins y, rot, xs ...).
    panel_dump: rows of the panel block exploded at the origin (dump-block.lsp)."""
    bi, br, bx = (float(body_row[3]), float(body_row[4])), round(float(body_row[5])) % 360, round(float(body_row[6]))
    pi_, pr, px = (float(panel_row[3]), float(panel_row[4])), round(float(panel_row[5])) % 360, round(float(panel_row[6]))

    def rel(p):   # panel local -> body local
        w = apply(pr, px, p); w = (w[0] + pi_[0] - bi[0], w[1] + pi_[1] - bi[1])
        return inverse(br, bx, w)

    outline, gaps = None, []
    for r in panel_dump:
        if r[0] != "PLINE" or r[1] != panel_row[1]: continue
        pts = [tuple(map(float, p.split(","))) for p in r[3].split(";") if p]
        if r[2] == "closed":
            outline = [rel(p) for p in pts]
        else:
            a, b = pts[0], pts[-1]
            if abs(a[0] - b[0]) < 1 or abs(a[1] - b[1]) < 1:
                span = max(abs(a[0] - b[0]), abs(a[1] - b[1]))
                bb = (max(p[0] for p in pts) - min(p[0] for p in pts)) * (max(p[1] for p in pts) - min(p[1] for p in pts))
                gaps.append((span, rel(a), rel(b), bb, [rel(p) for p in pts]))
    # panel line = the open polyline with the widest door gap (panel ends), outermost among those;
    # the installation outline (panel + tolerance) is the closed polyline, or — when it is drawn
    # open — the larger open polyline whose gap is narrower. It is only a warning check.
    gaps.sort(key=lambda g: (-round(g[0]), -g[3]))
    gap = gaps[0] if gaps else None
    if outline is None and gap:
        bigger = [g for g in gaps if g[3] > gap[3] * 1.01]
        if bigger: outline = max(bigger, key=lambda g: g[3])[4]
    return {"body": body_row[2], "panel": panel_row[2], "panel_layer": panel_row[1],
            "panel_rel": _affine_from(rel), "outline": gap[4] if gap else outline, "install_outline": outline,
            "door_gap": [gap[1], gap[2]] if gap else None, "ref": {"rot": br, "xs": bx}}


def _world(rot, xs, ins, p):
    q = apply(rot, xs, p); return (q[0] + ins[0], q[1] + ins[1])


def panel_insert(L, rot, xs, ins):
    """Insertion (rot, xs, point) of the panel block when the body block is placed at (rot, xs, ins)."""
    rr, rx, b = L["panel_rel"]
    return _affine_from(lambda p: _world(rot, xs, ins, (lambda q: (q[0] + b[0], q[1] + b[1]))(apply(rr, rx, p))))


# ---------------------------------------------------------------- fit test
def poly_in_loop(poly, loop):
    if not all(_inside(x, y, loop) or _on_boundary(x, y, loop) for x, y in poly): return False
    n = len(poly)
    for k in range(n):   # edge midpoints and a point just inside each edge
        (ax, ay), (bx, by) = poly[k - 1], poly[k]
        mx, my = (ax + bx) / 2, (ay + by) / 2
        if not (_inside(mx, my, loop) or _on_boundary(mx, my, loop)): return False
    return not any(_inside(vx, vy, poly) and not _on_boundary(vx, vy, poly) for vx, vy in loop)


def _on_boundary(x, y, loop):
    for k in range(len(loop)):
        (ax, ay), (bx, by) = loop[k - 1], loop[k]
        if abs(ax - bx) < 1e-6 and abs(x - ax) <= TOL and min(ay, by) - TOL <= y <= max(ay, by) + TOL: return True
        if abs(ay - by) < 1e-6 and abs(y - ay) <= TOL and min(ax, bx) - TOL <= x <= max(ax, bx) + TOL: return True
    return False


def _dist_out(x, y, loop):
    """0 if (x, y) is inside the loop, else distance to the nearest loop edge."""
    if _inside(x, y, loop) or _on_boundary(x, y, loop): return 0.0
    best = 1e18
    for k in range(len(loop)):
        (ax, ay), (bx, by) = loop[k - 1], loop[k]
        cx = min(max(x, min(ax, bx)), max(ax, bx)); cy = min(max(y, min(ay, by)), max(ay, by))
        best = min(best, ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5)
    return best


def _gap_wall(model, a, b, bath_c):
    """Wall carrying the door gap a-b and the space on the far side (from the bathroom centre)."""
    horiz = abs(a[1] - b[1]) < 1
    c = a[1] if horiz else a[0]
    t0, t1 = sorted((a[0], b[0]) if horiz else (a[1], b[1]))
    for w in model["walls"]:
        if (w["orient"] == "H") != horiz: continue
        f_lo, f_hi = face(w, "lo"), face(w, "hi")
        if not (f_lo - 150 <= c <= f_hi + 150): continue
        if min(t1, w["span"][1]) - max(t0, w["span"][0]) < 0.8 * (t1 - t0): continue
        bath_side = "lo" if (bath_c[1] if horiz else bath_c[0]) < w["axis_coord"] else "hi"
        other_face = f_hi + 60 if bath_side == "lo" else f_lo - 60
        m = (t0 + t1) / 2
        other = space_at(model, *((m, other_face) if horiz else (other_face, m)))
        return w, bath_side, (t0, t1), other
    return None


# ---------------------------------------------------------------- placement
def place_ubr(model, rules, lib, clear_loops):
    fixtures, doors, issues = [], [], []
    for r in rules:
        loops = clear_loops.get(r["room"])
        if not loops:
            issues.append(f'{r["room"]}: 안목 영역 없음'); continue
        loop = max(loops, key=len)
        L = lib[r["ubr"]]
        xs_v = sorted({p[0] for p in loop}); ys_v = sorted({p[1] for p in loop})
        cands, reasons = [], {"outline": 0, "door": 0}
        for xs in (L["ref"]["xs"], -L["ref"]["xs"]):
            for rot in (0, 90, 180, 270):
                ol0 = [apply(rot, xs, p) for p in L["outline"]]
                ob = loop_bbox(ol0); w, h = ob[2] - ob[0], ob[3] - ob[1]
                for x0 in set(xs_v + [x - w for x in xs_v]):
                    for y0 in set(ys_v + [y - h for y in ys_v]):
                        ins = (x0 - ob[0], y0 - ob[1])
                        outline = [(p[0] + ins[0], p[1] + ins[1]) for p in ol0]
                        if not poly_in_loop(outline, loop):
                            reasons["outline"] += 1; continue
                        ga, gb = (_world(rot, xs, ins, p) for p in L["door_gap"])
                        cen = ((x0 + x0 + w) / 2, (y0 + y0 + h) / 2)
                        gw = _gap_wall(model, ga, gb, cen)
                        if not gw or not gw[3] or gw[3]["name"] not in r["door_to"]:
                            reasons["door"] += 1; continue
                        pref = (xs != L["ref"]["xs"], rot != L["ref"]["rot"])
                        cands.append((pref, rot, xs, ins, outline, gw, (ga, gb)))
        if not cands:
            fb = loop_bbox(L["outline"])
            issues.append(f'{r["room"]}: {r["ubr"]} 배치 불가 — 외곽선 불일치 {reasons["outline"]}건, '
                          f'문 방향 불일치 {reasons["door"]}건 (문은 {r["door_to"]} 쪽이어야 함)')
            continue
        pref, rot, xs, ins, outline, (w, bath_side, (t0, t1), other), gap = min(cands, key=lambda c: c[0])
        pr, px, pins = panel_insert(L, rot, xs, ins)
        if L.get("install_outline"):
            io = [_world(rot, xs, ins, p) for p in L["install_outline"]]
            if not poly_in_loop(io, loop):
                over = max(max(0, min(_dist_out(x, y, loop) for _ in [0])) for x, y in io)
                issues.append(f'{r["room"]}: 실제 패널은 들어가지만 설치 여유선(패널+35)이 안목을 최대 {round(over)}mm 넘음 — 시공 여유 확인')
        fixtures.append({"kind": "ubr", "space": r["room"], "block": L["body"], "insert": list(ins), "rotation_deg": rot,
                         "xscale": xs, "outline": [list(p) for p in outline], "footprint": loop_bbox(outline),
                         "panel": {"block": L["panel"], "layer": L["panel_layer"], "insert": list(pins), "rotation_deg": pr, "xscale": px},
                         "basis": "rule: 실제 외곽선 + UBR 문이 " + other["name"] + " 쪽"})
        c = (t0 + t1) / 2; dw = r["door_width"]
        span = [c - dw / 2, c + dw / 2]
        # hinge on the gap end nearer a corner of the UBR outline bbox (door leaf rests along the side wall)
        ob = loop_bbox(outline)
        corners = [(ob[0], ob[1]), (ob[2], ob[1]), (ob[0], ob[3]), (ob[2], ob[3])]
        g_end = min(gap, key=lambda p: min((p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2 for c in corners))
        corner_t = g_end[0] if w["orient"] == "H" else g_end[1]
        hinge = span[0] if abs(corner_t - span[0]) < abs(corner_t - span[1]) else span[1]
        doors.append({"kind": "door", "type": "swing", "room": r["room"], "to": other["name"], "wall": w["id"],
                      "side_room": bath_side, "span": span, "width_mm": dw, "hinge_t": hinge, "swing_side": bath_side,
                      "basis": "ubr_door", "ubr_gap": [round(t0), round(t1)]})
    return fixtures, doors, issues
