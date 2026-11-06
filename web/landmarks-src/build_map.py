"""Build the simplified Saudi Arabia map used by web/landmarks.js.

Source: Natural Earth 1:50m Admin 0 Countries (public domain),
https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_50m_admin_0_countries.geojson
downloaded into this folder as ne_50m_admin_0_countries.geojson.

Projection (simple equirectangular, recorded in map.json and landmarks.js):
    x = OX + (lon - LON0) * cos(23.5 deg) * S
    y = OY + (LAT0 - lat) * S
Output: map.json  {viewBox, saudi, neighbors, projection}
Run:    python -I build_map.py ne_50m_admin_0_countries.geojson map.json
"""
import json, math, sys

LON0, LAT0 = 34.0, 32.6          # top-left geographic anchor
COSLAT = math.cos(math.radians(23.5))
S = 49.0                         # px per degree of latitude
OX, OY = 10.0, 3.0               # small padding offsets
W, H = 1000, 820
NEIGHBOURS = {"YEM", "OMN", "ARE", "QAT", "BHR", "KWT", "IRQ", "JOR", "EGY",
              "ISR", "PSE", "SYR", "IRN", "ERI", "SDN", "DJI", "ETH", "LBN"}


def project(lat, lon):
    return (OX + (lon - LON0) * COSLAT * S, OY + (LAT0 - lat) * S)


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]; bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy) or 1e-9
        best, idx = -1, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            d = abs(dy * px - dx * py + bx * ay - by * ax) / L
            if d > best:
                best, idx = d, i
        if best > eps:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(pts, keep) if k]


def clip(poly, xmin, ymin, xmax, ymax):
    """Sutherland-Hodgman clip of a polygon to a rectangle."""
    def edge(points, inside, inter):
        out = []
        for i in range(len(points)):
            cur, prev = points[i], points[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(inter(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(inter(prev, cur))
        return out

    def ix(x):
        return lambda p, q: (x, p[1] + (q[1] - p[1]) * (x - p[0]) / (q[0] - p[0]))

    def iy(y):
        return lambda p, q: (p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1]), y)

    for inside, inter in ((lambda p: p[0] >= xmin, ix(xmin)), (lambda p: p[0] <= xmax, ix(xmax)),
                          (lambda p: p[1] >= ymin, iy(ymin)), (lambda p: p[1] <= ymax, iy(ymax))):
        if not poly:
            break
        poly = edge(poly, inside, inter)
    return poly


def rings(geom):
    if geom["type"] == "Polygon":
        return [r for r in geom["coordinates"]]
    return [r for poly in geom["coordinates"] for r in poly]


def to_path(ring_list, eps, min_area, box=None):
    out = []
    for ring in ring_list:
        pts = [project(lat, lon) for lon, lat in ring]
        if box:
            pts = clip(pts, *box)
        if len(pts) < 3:
            continue
        area = abs(sum(pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1] for i in range(len(pts)))) / 2
        if area < min_area:
            continue
        if pts[0] == pts[-1]:
            pts = pts[:-1]
        m = len(pts) // 2   # split the closed ring in two open chains so RDP has a real baseline
        pts = rdp(pts[:m + 1], eps)[:-1] + rdp(pts[m:] + [pts[0]], eps)[:-1]
        if len(pts) < 3:
            continue
        s = "M" + "L".join(f"{x:.1f} {y:.1f}".replace(".0 ", " ").replace(".0L", "L") for x, y in pts) + "Z"
        out.append(s)
    return "".join(out)


def main(src, dst):
    data = json.load(open(src, encoding="utf-8"))
    saudi, neigh = None, []
    for f in data["features"]:
        p = f["properties"]
        code = p.get("ISO_A3") if p.get("ISO_A3") not in (None, "-99") else p.get("ADM0_A3")
        if code == "SAU":
            saudi = f["geometry"]
        elif code in NEIGHBOURS:
            neigh.append(f["geometry"])
    assert saudi, "SAU not found"
    sp = to_path(rings(saudi), eps=0.35, min_area=4)
    box = (-20, -20, W + 20, H + 20)
    np_ = to_path([r for g in neigh for r in rings(g)], eps=0.9, min_area=30, box=box)
    xs = [project(lat, lon)[0] for r in rings(saudi) for lon, lat in r]
    ys = [project(lat, lon)[1] for r in rings(saudi) for lon, lat in r]
    out = {
        "viewBox": f"0 0 {W} {H}",
        "saudi": sp,
        "neighbors": np_,
        "projection": {"type": "equirectangular", "lon0": LON0, "lat0": LAT0, "cosLat": round(COSLAT, 6),
                       "standardParallel": 23.5, "scale": S, "ox": OX, "oy": OY,
                       "formula": "x = ox + (lon - lon0) * cosLat * scale; y = oy + (lat0 - lat) * scale"},
        "saudiBBoxPx": [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)],
        "source": "Natural Earth 1:50m Admin 0 Countries (public domain), nvkelso/natural-earth-vector",
    }
    json.dump(out, open(dst, "w", encoding="utf-8"), indent=1)
    print("saudi", len(sp), "bytes; neighbors", len(np_), "bytes; bbox", out["saudiBBoxPx"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
