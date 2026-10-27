"""Union of axis-aligned rectangles minus cut rectangles -> closed outline loops.

Used by unit-plan-walls / insulation / finish to turn wall bodies (axis +/- thickness)
into clean CAD outlines and hatch boundaries. Orthogonal geometry only.

Input JSON (stdin or file):
  {"groups": {"RC": {"add": [[x1,y1,x2,y2], ...], "cut": [[x1,y1,x2,y2], ...]}, ...}}
Output JSON (stdout):
  {"groups": {"RC": {"loops": [{"points": [[x,y],...], "outer": true, "area": 123.0}, ...]}}}
Outer loops are counter-clockwise, holes clockwise. Collinear vertices are removed.
Each hole carries "parent" = index of the outer loop containing it. Hatch an outer loop
together with its holes as inner loops; never hatch a hole loop on its own.
"""
import json
import sys


def _norm(r):
    x1, y1, x2, y2 = r
    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)


def union_loops(add, cut=()):
    add = [_norm(r) for r in add]
    cut = [_norm(r) for r in cut]
    xs = sorted({v for r in add + cut for v in (r[0], r[2])})
    ys = sorted({v for r in add + cut for v in (r[1], r[3])})
    nx, ny = len(xs) - 1, len(ys) - 1
    if nx < 1 or ny < 1:
        return []
    filled = [[False] * ny for _ in range(nx)]
    for i in range(nx):
        cx = (xs[i] + xs[i + 1]) / 2
        for j in range(ny):
            cy = (ys[j] + ys[j + 1]) / 2
            inside = any(r[0] < cx < r[2] and r[1] < cy < r[3] for r in add)
            if inside and any(r[0] < cx < r[2] and r[1] < cy < r[3] for r in cut):
                inside = False
            filled[i][j] = inside

    def f(i, j):
        return 0 <= i < nx and 0 <= j < ny and filled[i][j]

    # directed boundary edges with the filled cell on the left
    out = {}
    for i in range(nx):
        for j in range(ny):
            if not filled[i][j]:
                continue
            x0, x1, y0, y1 = xs[i], xs[i + 1], ys[j], ys[j + 1]
            if not f(i, j - 1):
                out.setdefault((x0, y0), []).append((x1, y0))
            if not f(i + 1, j):
                out.setdefault((x1, y0), []).append((x1, y1))
            if not f(i, j + 1):
                out.setdefault((x1, y1), []).append((x0, y1))
            if not f(i - 1, j):
                out.setdefault((x0, y1), []).append((x0, y0))

    def turn_key(prev, cur, nxt):
        # prefer the sharpest left turn so touching corners split into separate loops
        dx1, dy1 = cur[0] - prev[0], cur[1] - prev[1]
        dx2, dy2 = nxt[0] - cur[0], nxt[1] - cur[1]
        cross = dx1 * dy2 - dy1 * dx2
        dot = dx1 * dx2 + dy1 * dy2
        return (-cross, -dot)

    loops = []
    while out:
        start = next(iter(out))
        pts = [start]
        prev, cur = None, start
        while True:
            cands = out[cur]
            nxt = cands[0] if prev is None or len(cands) == 1 else min(cands, key=lambda n: turn_key(prev, cur, n))
            cands.remove(nxt)
            if not cands:
                del out[cur]
            prev, cur = cur, nxt
            if cur == start:
                break
            pts.append(cur)
        # drop collinear vertices
        clean = []
        n = len(pts)
        for k in range(n):
            a, b, c = pts[k - 1], pts[k], pts[(k + 1) % n]
            if (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) != 0:
                clean.append(b)
        area = sum(clean[k - 1][0] * clean[k][1] - clean[k][0] * clean[k - 1][1] for k in range(len(clean))) / 2
        loops.append({"points": [list(p) for p in clean], "outer": area > 0, "area": abs(area)})
    # attach each hole to the smallest outer loop that contains it
    for hole in (lp for lp in loops if not lp["outer"]):
        px, py = hole["points"][0]
        px, py = px + 1e-6, py + 1e-6
        best = None
        for k, outer in enumerate(loops):
            if outer["outer"] and _inside(px, py, outer["points"]) and (best is None or outer["area"] < loops[best]["area"]):
                best = k
        hole["parent"] = best
    return loops


def _inside(x, y, pts):
    c = False
    for k in range(len(pts)):
        (x1, y1), (x2, y2) = pts[k - 1], pts[k]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def main():
    data = json.load(open(sys.argv[1], encoding="utf-8") if len(sys.argv) > 1 else sys.stdin)
    result = {"groups": {}}
    for name, g in data["groups"].items():
        result["groups"][name] = {"loops": union_loops(g.get("add", []), g.get("cut", []))}
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
