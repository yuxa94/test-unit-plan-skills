"""Rule-based door placement (unit-plan-doors).

place_doors(model, rules, entry_name="현관") -> (openings, issues)
rules: list of {"room", "to": [names] | "__core__", "width", "swing": "in"|"out", "type": "swing"|"sliding"|"open"}
  - candidates: every shared wall segment with any `to` space that is long enough
  - corridor_max (mm): a segment whose free depth in front of the door (to the next wall on the
    other side) is <= corridor_max counts as facing a corridor/hall and is preferred;
    then the `to` order, then the longest segment
  - corridor_tie: tie-break between hall-facing candidates (e.g. both room corners face the hall):
      "entry" (nearer the entry, default) | "far_entry" | "living" (nearer the centre of the space in
      front of the door, i.e. toward the main living area) | "rc_wall" (hinge corner on an RC wall)
  - position inside the segment, per rule "position" (profile):
      "corner": at the room's inner corner — the segment end that is a vertex of the room polygon
                (both: the one nearer the entry; neither: centre). The opening starts `jamb` mm
                from the face of the perpendicular wall at that corner; the hinge is on that side.
      "center": centred in the segment; hinge on the end nearer the entry.
      "entry" : legacy — the end nearer the entry, `jamb` mm from the segment end.
  - swings into `room` ("in") or into the other space ("out")
Each opening: {id, kind:"door", type, room, to, wall, side_room, span:[t0,t1], width_mm, hinge_t, swing_side, basis:"rule"}
"""
from upgeom import wall_sides, shared, by_name, centroid, subtract_spans

JAMB = 150  # default clearance from the corner to the opening (frame + finish); profile overrides


def _pt(w, t):
    return (t, w["axis_coord"]) if w["orient"] == "H" else (w["axis_coord"], t)


def _corner_face(model, w, t_end, toward):
    """Room-side face of the perpendicular wall at the segment end t_end (toward = +1 if the segment
    continues toward +t from t_end). None if no perpendicular wall is within 200 mm."""
    best = None
    for q in model["walls"]:
        if q["orient"] == w["orient"]: continue
        if not (q["span"][0] - 1 <= w["axis_coord"] <= q["span"][1] + 1): continue
        if abs(q["axis_coord"] - t_end) > 200: continue
        f = q["axis_coord"] + (q["hi"] if toward > 0 else q["lo"])
        if best is None or abs(q["axis_coord"] - t_end) < abs(best[1] - t_end): best = (f, q["axis_coord"])
    return best[0] if best else None


def door_positions(model, w, a, b, room, width, mode, jamb, entry_xy):
    """-> list of (t0 of the opening, hinge_t, basis). "corner" yields one option per room corner;
    the caller ranks them (corridor first, then entry distance)."""
    ex, ey = entry_xy
    pa, pb = _pt(w, a), _pt(w, b)
    near_a = (pa[0] - ex) ** 2 + (pa[1] - ey) ** 2 <= (pb[0] - ex) ** 2 + (pb[1] - ey) ** 2
    if mode == "center":
        t0 = (a + b - width) / 2
        return [(t0, (t0 if near_a else t0 + width), "위치: 벽 구간 가운데")]
    if mode == "corner":
        def is_corner(t):
            p = _pt(w, t)
            return any(abs(v[0] - p[0]) <= 200 and abs(v[1] - p[1]) <= 200 for v in room["polygon"])
        out = []
        if is_corner(a):
            f = _corner_face(model, w, a, +1)
            t0 = max(a, f) + jamb if f is not None else a + jamb
            out.append((t0, t0, f"위치: 실 모서리 + 문틀 여유 {jamb}"))
        if is_corner(b):
            f = _corner_face(model, w, b, -1)
            t1 = (min(b, f) if f is not None else b) - jamb
            out.append((t1 - width, t1, f"위치: 실 모서리 + 문틀 여유 {jamb}"))
        if out:
            return out
        t0 = (a + b - width) / 2
        return [(t0, (t0 if near_a else t0 + width), "위치: 모서리 없음 → 가운데")]
    t0 = a + jamb if near_a else b - jamb - width
    return [(t0, (t0 if near_a else t0 + width), "위치: 현관 쪽 끝")]


def clear_depth(model, w, room_side, t):
    """Free distance in front of the door: from the wall face on the far side (away from the room)
    to the nearest other wall body along the wall normal, at axis position t. None if nothing is hit."""
    far = "hi" if room_side == "lo" else "lo"
    f = w["axis_coord"] + (w["hi"] if far == "hi" else w["lo"])
    sgn = 1 if far == "hi" else -1
    best = None
    for q in model["walls"]:
        if q is w: continue
        x1, y1, x2, y2 = q["rect"]
        if w["orient"] == "H":
            if not (x1 < t < x2): continue
            d = (y1 - f) if sgn > 0 else (f - y2)
        else:
            if not (y1 < t < y2): continue
            d = (x1 - f) if sgn > 0 else (f - x2)
        if d > 1 and (best is None or d < best): best = d
    return best


def _corner_material(model, w, t, reach=250):
    """Material of the perpendicular wall at axis position t of wall w (the hinge corner)."""
    best = None
    for q in model["walls"]:
        if q["orient"] == w["orient"]: continue
        if not (q["span"][0] - 1 <= w["axis_coord"] <= q["span"][1] + 1): continue
        d = abs(q["axis_coord"] - t)
        if d <= reach and (best is None or d < best[0]): best = (d, q.get("material"))
    return best[1] if best else None


def place_doors(model, rules, entry_name="현관", taken=None, corridor_max=None, jamb=JAMB, corridor_tie="entry"):
    sides = wall_sides(model)
    entry = by_name(model, entry_name)
    ex, ey = centroid(entry["polygon"]) if entry else (0, 0)
    taken = taken or {}  # wall id -> [[t0,t1], ...] already used
    openings, issues = [], []
    for r in rules:
        room = by_name(model, r["room"])
        if not room:
            issues.append(f'{r["room"]}: 실 없음'); continue
        if r.get("type") == "open":
            issues.append(f'{r["room"]}: 문 없는 개구부(규칙) — 작도 없음'); continue
        if r["to"] == "__core__":
            targets = [s for s in model.get("fixed", []) if s["kind"] == "core"]
        else:
            targets = [by_name(model, n) for n in r["to"]]
        rj = r.get("jamb", jamb)   # per-rule override of the profile clearance
        need = r["width"] + 2 * rj
        # shared pieces per wall for all targets; contiguous pieces on the same wall/side are merged,
        # so a virtual split (e.g. 거실 | 주방) does not cut the door segment short of the room corner
        pieces = {}
        for rank, tgt in enumerate(t for t in targets if t):
            for w, t0, t1, side in shared(model, sides, room["id"], tgt["id"]):
                pieces.setdefault((w["id"], side), []).append([t0, t1, rank, tgt])
        cands = []
        wmap = {w["id"]: w for w in model["walls"]}
        for (wid, side), ps in pieces.items():
            w = wmap[wid]
            ps.sort(key=lambda p: p[0])
            merged = []
            for p in ps:
                if merged and p[0] - merged[-1]["t1"] <= 1:
                    merged[-1]["t1"] = max(merged[-1]["t1"], p[1]); merged[-1]["parts"].append(p)
                else:
                    merged.append({"t0": p[0], "t1": p[1], "parts": [p]})
            for mg in merged:
                for a, b in subtract_spans([mg["t0"], mg["t1"]], taken.get(wid, []), gap=100):
                    if b - a < need: continue
                    for t0d, hinge, pos_basis in door_positions(model, w, a, b, room, r["width"], r.get("position", "entry"), rj, (ex, ey)):
                        if t0d < a - 1 or t0d + r["width"] > b + 1: continue
                        mid = t0d + r["width"] / 2
                        part = min(mg["parts"], key=lambda p: 0 if p[0] <= mid <= p[1] else min(abs(mid - p[0]), abs(mid - p[1])))
                        depth = clear_depth(model, w, side, mid)
                        # corridor preference is for interior circulation only: a narrow shaft/niche
                        # attached to the core is not a corridor (84B 현관 사례)
                        corridor = (corridor_max is not None and depth is not None and depth <= corridor_max
                                    and part[3].get("kind") not in ("core", "shaft"))
                        mp = _pt(w, mid)
                        tc = centroid(part[3]["polygon"])
                        cands.append({"w": w, "a": a, "b": b, "side": side, "tgt": part[3], "rank": part[2],
                                      "hinge": hinge, "t0": t0d, "depth": depth, "corridor": corridor, "pos_basis": pos_basis,
                                      "entry_d": (mp[0] - ex) ** 2 + (mp[1] - ey) ** 2,
                                      "living_d": (mp[0] - tc[0]) ** 2 + (mp[1] - tc[1]) ** 2,
                                      "rc_corner": _corner_material(model, w, hinge) == "RC"})
        if cands:
            # corridor/hall-facing first, then the `to` order of the space in front of the door,
            # then the longest segment, then the tie-break (corridor_tie for hall-facing doors)
            def tie(c):
                if not c["corridor"] or corridor_tie == "entry": return (c["entry_d"],)
                if corridor_tie == "far_entry": return (-c["entry_d"],)
                if corridor_tie == "living": return (c["living_d"],)
                if corridor_tie == "rc_wall": return (not c["rc_corner"], c["entry_d"])
                return (c["entry_d"],)
            c = min(cands, key=lambda c: (not c["corridor"], c["rank"], -(c["b"] - c["a"])) + tie(c))
            w, side = c["w"], c["side"]
            span = [c["t0"], c["t0"] + r["width"]]
            other = "hi" if side == "lo" else "lo"
            swing_side = side if r.get("swing", "in") == "in" else other
            openings.append({"kind": "door", "type": r.get("type", "swing"), "room": room["name"], "to": c["tgt"]["name"],
                             "wall": w["id"], "side_room": side, "span": span, "width_mm": r["width"],
                             "hinge_t": c["hinge"], "swing_side": swing_side,
                             "front_depth_mm": None if c["depth"] is None else round(c["depth"]),
                             "basis": ("rule: 복도·홀 면 우선" if c["corridor"] else "rule: 가장 긴 벽") + " / " + c["pos_basis"]})
            taken.setdefault(w["id"], []).append(span)
        else:
            issues.append(f'{r["room"]}: {r["to"]} 와 맞닿은 벽 중 폭 {r["width"]}+문틀 여유를 둘 구간 없음')
    for k, o in enumerate(openings):
        o["id"] = f"D{k + 1}"
    return openings, issues
