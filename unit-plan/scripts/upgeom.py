"""Shared geometry for unit-plan rule scripts (orthogonal plans, mm).

model.json conventions used here:
  spaces/fixed: {"id","name","polygon","kind","heated"}
  walls: {"id","orient":"H"|"V","axis_coord","span":[a,b],"lo","hi","rect":[x1,y1,x2,y2],"material"}
A wall's "lo" side is -y (H) / -x (V); "hi" side is +y / +x.
"""
from rectunion import union_loops, _inside


def space_at(model, x, y):
    for s in model["spaces"] + model.get("fixed", []):
        if _inside(x, y, s["polygon"]):
            return s
    return None


def face(w, side):
    return w["axis_coord"] + (w["lo"] if side == "lo" else w["hi"])


def pt(w, t, n):
    """point at axis position t, normal coordinate n"""
    return (t, n) if w["orient"] == "H" else (n, t)


def wall_sides(model, step=50):
    """For each wall: merged intervals [t0, t1, lo_space_id|None, hi_space_id|None] along the axis."""
    out = {}
    for w in model["walls"]:
        a, b = w["span"]
        segs, t = [], a
        while t < b:
            t1 = min(b, t + step); tm = (t + t1) / 2
            lo = space_at(model, *pt(w, tm, face(w, "lo") - 60))
            hi = space_at(model, *pt(w, tm, face(w, "hi") + 60))
            key = (lo["id"] if lo else None, hi["id"] if hi else None)
            if segs and segs[-1][2:] == list(key) and abs(segs[-1][1] - t) < 1e-6:
                segs[-1][1] = t1
            else:
                segs.append([t, t1, *key])
            t = t1
        out[w["id"]] = segs
    return out


def shared(model, sides, a_id, b_id):
    """Wall intervals separating spaces a and b: [(wall, t0, t1, side_of_a)]."""
    res = []
    for w in model["walls"]:
        for t0, t1, lo, hi in sides[w["id"]]:
            if (lo, hi) == (a_id, b_id): res.append((w, t0, t1, "lo"))
            elif (lo, hi) == (b_id, a_id): res.append((w, t0, t1, "hi"))
    return res


def by_name(model, name):
    return next((s for s in model["spaces"] + model.get("fixed", []) if s["name"] == name), None)


def centroid(poly):
    return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))


def subtract_spans(span, blocked, gap=0):
    """span [a,b] minus blocked spans (each widened by gap) -> list of free [a,b]."""
    free = [list(span)]
    for c0, c1 in blocked:
        c0, c1 = c0 - gap, c1 + gap
        nxt = []
        for a, b in free:
            if c1 <= a or c0 >= b: nxt.append([a, b]); continue
            if c0 > a: nxt.append([a, c0])
            if c1 < b: nxt.append([c1, b])
        free = nxt
    return free


def loop_bbox(loop):
    xs = [p[0] for p in loop]; ys = [p[1] for p in loop]
    return [min(xs), min(ys), max(xs), max(ys)]


def max_rect_in_loop(loop, step=50):
    """Largest axis-aligned rectangle inside an orthogonal loop (coarse grid search)."""
    xs = sorted({p[0] for p in loop}); ys = sorted({p[1] for p in loop})
    best, area = None, 0
    for i, x0 in enumerate(xs):
        for x1 in xs[i + 1:]:
            for j, y0 in enumerate(ys):
                for y1 in ys[j + 1:]:
                    a = (x1 - x0) * (y1 - y0)
                    if a <= area: continue
                    ok = all(_inside(x0 + (x1 - x0) * fx, y0 + (y1 - y0) * fy, loop)
                             for fx in (0.01, 0.5, 0.99) for fy in (0.01, 0.5, 0.99))
                    if ok: best, area = [x0, y0, x1, y1], a
    return best


# ---- block transforms (rotation multiple of 90 deg, x-scale +-1) ----
ROT = {0: ((1, 0), (0, 1)), 90: ((0, -1), (1, 0)), 180: ((-1, 0), (0, -1)), 270: ((0, 1), (-1, 0))}


def apply(rot, xs, p):
    (a, b), (c, d) = ROT[rot]
    x, y = p[0] * xs, p[1]
    return (a * x + b * y, c * x + d * y)


def inverse(rot, xs, p):
    (a, b), (c, d) = ROT[rot]
    x = a * p[0] + c * p[1]; y = b * p[0] + d * p[1]   # transpose = inverse for rotations
    return (x / xs, y)


def local_bbox_from_instance(ins_xy, rot, xs, world_bbox):
    x1, y1, x2, y2 = world_bbox
    pts = [inverse(round(rot) % 360, xs, (x - ins_xy[0], y - ins_xy[1])) for x in (x1, x2) for y in (y1, y2)]
    return [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)]


def world_bbox(rot, xs, lb, ins=(0, 0)):
    pts = [apply(rot, xs, (x, y)) for x in (lb[0], lb[2]) for y in (lb[1], lb[3])]
    return [min(p[0] for p in pts) + ins[0], min(p[1] for p in pts) + ins[1],
            max(p[0] for p in pts) + ins[0], max(p[1] for p in pts) + ins[1]]
