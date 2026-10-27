"""Rule-based window placement (unit-plan-windows).

place_windows(model, rules, widths, taken) -> (openings, issues)
rules: list of {"room", "type": "double"|"single"|"outdoor_unit", "width": optional fixed width,
                "facing": optional "exterior" (only walls to the outside),
                "side": optional "N"|"S"|"E"|"W" (plan-relative: +y = N) — only walls whose outward
                        direction from the room is that side}
For each room: candidate wall intervals where the room is on one side and the other side is
outside (None) or an unheated space (balcony/service). The longest free interval (minus doors
and other openings, `margin` mm kept at both ends) gets one window: width = largest of `widths`
that fits (or the fixed width), centred in the interval.
"""
from upgeom import wall_sides, by_name, subtract_spans

MARGIN = 300


def outward(w, side):
    """Plan direction from the room (on `side` of wall w) through the wall.
    Room on the lo (-y / -x) side looks out toward +y / +x."""
    if w["orient"] == "H":
        return "N" if side == "lo" else "S"
    return "E" if side == "lo" else "W"


def place_windows(model, rules, widths, taken=None):
    sides = wall_sides(model)
    spaces = {s["id"]: s for s in model["spaces"] + model.get("fixed", [])}
    taken = taken or {}
    openings, issues = [], []
    for r in rules:
        room = by_name(model, r["room"])
        if not room:
            issues.append(f'{r["room"]}: 실 없음'); continue
        cands = []
        for w in model["walls"]:
            for t0, t1, lo, hi in sides[w["id"]]:
                for mine, other, side in ((lo, hi, "lo"), (hi, lo, "hi")):
                    if mine != room["id"]: continue
                    o = spaces.get(other)
                    ok = other is None if r.get("facing") == "exterior" else \
                        (other is None or (o and not o["heated"] and o["kind"] in ("balcony", "service")))
                    if ok and r.get("side") and outward(w, side) != r["side"]:
                        ok = False
                    if ok:
                        for a, b in subtract_spans([t0, t1], taken.get(w["id"], []), gap=100):
                            cands.append((w, a, b, side, "exterior" if other is None else o["name"]))
        if not cands:
            where = f' ({r["side"]}쪽)' if r.get("side") else ""
            issues.append(f'{r["room"]}: 외기·발코니에 면한 벽{where} 없음'); continue
        w, a, b, side, facing = max(cands, key=lambda c: c[2] - c[1])
        avail = b - a - 2 * MARGIN
        width = r.get("width") or max((x for x in widths if x <= avail), default=None)
        if not width or width > b - a:
            issues.append(f'{r["room"]}: 구간 {round(b - a)}mm에 맞는 창 폭 없음'); continue
        c = (a + b) / 2
        span = [c - width / 2, c + width / 2]
        openings.append({"kind": "window", "type": r.get("type", "double"), "room": room["name"], "facing": facing,
                         "wall": w["id"], "side_room": side, "span": span, "width_mm": width,
                         "side": outward(w, side), "basis": "profile: 방위·폭" if r.get("side") else "rule"})
        taken.setdefault(w["id"], []).append(span)
    for k, o in enumerate(openings):
        o["id"] = f"WN{k + 1}"
    return openings, issues
