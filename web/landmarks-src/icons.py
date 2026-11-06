"""Original flat icons for the "Walk across Saudi Arabia" track.

Drawn from scratch as simplified geometric illustrations (no traced artwork, no logos).
Style "Playful Bold": chunky flat shapes, 3px ink outline, rounded joins, light-tint
rounded-square backdrop, no text, no gradients. Every icon is a 96x96 viewBox.
"""
import math

INK = "#38393B"
LEAF, LEAF_D = "#3FBF4A", "#2F9A38"
FLAME, SKY, SUN, BERRY = "#FF8A1F", "#22A6F2", "#FFC52E", "#9B6BFF"
SAND, MUD, SAND_L = "#D9A46C", "#B97C45", "#F2D2A9"
WHITE = "#FFFFFF"
ROSE, ROSE_D = "#FF7AB0", "#E0528F"           # only for Taif's roses
T_SKY, T_SUN, T_LEAF, T_FLAME, T_BERRY = "#DBF1FD", "#FFF4D1", "#DDF6DF", "#FFEBD6", "#EEE6FF"

OUT = f'stroke="{INK}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"'


def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


def band(y, fill, extra=""):
    """Fill from height y to the bottom of the rounded backdrop (x 2..94, y 2..94, r 22)."""
    if y <= 72:
        d = f"M2 {f(y)}H94V72A22 22 0 0 1 72 94H24A22 22 0 0 1 2 72Z"
    else:
        dx = math.sqrt(22 ** 2 - (y - 72) ** 2)
        d = f"M{f(24 - dx)} {f(y)}H{f(72 + dx)}A22 22 0 0 1 72 94H24A22 22 0 0 1 {f(24 - dx)} {f(y)}Z"
    return f'<path d="{d}" fill="{fill}" {extra}/>'


def strip(y1, y2, fill):
    """Horizontal strip with straight sides (valid while y2 <= 72)."""
    return f'<rect x="2" y="{f(y1)}" width="92" height="{f(y2 - y1)}" fill="{fill}"/>'


def crenel(x0, x1, y, h=6, w=4, fill=SAND):
    """Row of touching triangular merlons along a wall top (Najdi parapet)."""
    n = max(1, round((x1 - x0) / w))
    step = (x1 - x0) / n
    pts = [f"M{f(x0)} {f(y)}"]
    for i in range(n):
        pts.append(f"L{f(x0 + step * (i + .5))} {f(y - h)}L{f(x0 + step * (i + 1))} {f(y)}")
    return f'<path d="{"".join(pts)}Z" fill="{fill}"/>'


def tri_row(x0, x1, y, h=4, w=5, gap=3, fill=MUD, down=False):
    """Spaced small triangles (decorative vents / merlons) without outline."""
    out, x = [], x0
    while x + w <= x1 + .01:
        if down:
            out.append(f"M{f(x)} {f(y)}H{f(x + w)}L{f(x + w / 2)} {f(y + h)}Z")
        else:
            out.append(f"M{f(x)} {f(y)}H{f(x + w)}L{f(x + w / 2)} {f(y - h)}Z")
        x += w + gap
    return f'<path d="{"".join(out)}" fill="{fill}" stroke="none"/>'


FROND = "M0 0C6-9 16-10 22-2C15-5 7-4 0 0Z"


def palm(x, y, h=30, s=1.0, lean=0, dates=False):
    """Date palm: tapered trunk from (x, y) up h px, five fronds at the crown."""
    cx, cy = x + lean, y - h
    trunk = (f'<path d="M{f(x - 3.2 * s)} {f(y)}Q{f(x + lean * .2)} {f(y - h * .5)} {f(cx - 1.6 * s)} {f(cy)}'
             f'H{f(cx + 1.6 * s)}Q{f(x + lean * .2 + 2 * s)} {f(y - h * .5)} {f(x + 3.2 * s)} {f(y)}Z" fill="{MUD}"/>')
    rings = "".join(
        f'<path d="M{f(x + lean * t - 2.4 * s)} {f(y - h * t)}h{f(4.8 * s)}" stroke-width="1.8" fill="none"/>'
        for t in (.3, .55, .78))
    sw = 3 / s
    fr = []
    for ang, scl, col, mir in ((-70, .8, LEAF, True), (-70, .8, LEAF, False), (-28, 1, LEAF_D, True),
                               (-28, 1, LEAF_D, False), (22, 1, LEAF, True), (22, 1, LEAF, False)):
        m = "scale(-1 1) " if mir else ""
        fr.append(f'<path d="{FROND}" transform="{m}rotate({ang}) scale({scl})" fill="{col}"/>')
    d = ""
    if dates:
        d = (f'<g stroke-width="{f(2 / s)}">'
             f'<path d="M-5 2Q-9 10-6 14Q-1 12-2 4Z" fill="{FLAME}"/>'
             f'<path d="M5 2Q9 10 6 14Q1 12 2 4Z" fill="{MUD}"/>'
             f'<circle cx="-6.5" cy="9" r="1.4" fill="{SUN}" stroke="none"/>'
             f'<circle cx="6" cy="9" r="1.4" fill="{FLAME}" stroke="none"/></g>')
    crown = f'<g transform="translate({f(cx)} {f(cy)}) scale({f(s)})" stroke-width="{f(sw)}">{d}{"".join(fr)}</g>'
    return trunk + rings + crown


def thick_line(d, color, w=7):
    """A stroked line with an ink outline (draws ink underlay then colour)."""
    return (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{w + 6}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')


def waves(y, fill=SKY, crest=WHITE, amp=3, n=4):
    """Sea from y to bottom, with a wavy top and white crest marks."""
    seg = 92 / n
    d = f"M2 {f(y)}"
    for i in range(n):
        x = 2 + seg * i
        d += f"Q{f(x + seg / 4)} {f(y - amp)} {f(x + seg / 2)} {f(y)}T{f(x + seg)} {f(y)}"
    sea = band(y + 1, fill)
    top = f'<path d="{d}V{f(y + 4)}H2Z" fill="{fill}"/>'
    marks = "".join(
        f'<path d="M{f(2 + seg * i + 6)} {f(y + 8 + (i % 2) * 5)}q3-3 6 0" fill="none" stroke="{crest}" stroke-width="2.5" stroke-linecap="round"/>'
        for i in range(n))
    return sea + top + marks


def edge_shape(fill_d, top_d, fill):
    """Shape that touches the backdrop sides: fill unstroked, outline only the open top contour."""
    return (f'<path d="{fill_d}" fill="{fill}"/>'
            f'<path d="{top_d}" fill="none" {OUT}/>')


def sun_disc(cx, cy, r=8):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{SUN}"/>'


# ---------------------------------------------------------------- icons

def masmak():
    return T_SKY, (
        band(80, SAND_L) + f"<g {OUT}>"
        # main wall with parapet
        + f'<rect x="32" y="44" width="32" height="38" fill="{SAND}"/>'
        + crenel(32, 64, 44, h=6, w=4, fill=SAND)
        + tri_row(35, 62, 52, h=4, w=4, gap=2, fill=MUD, down=True)
        # big wooden door
        + f'<path d="M40 82V64Q48 56 56 64V82Z" fill="{MUD}"/>'
        + f'<path d="M48 61V82" fill="none" stroke-width="2"/>'
        # tapered towers
        + f'<path d="M12 82L18 30H32L37 82Z" fill="{SAND}"/>'
        + crenel(18, 32, 30, h=6, w=4.67, fill=SAND)
        + f'<path d="M59 82L64 30H78L84 82Z" fill="{SAND}"/>'
        + crenel(64, 78, 30, h=6, w=4.67, fill=SAND)
        + "</g>"
        + f'<rect x="23.5" y="42" width="3" height="9" rx="1.5" fill="{INK}"/>'
        + f'<rect x="69.5" y="42" width="3" height="9" rx="1.5" fill="{INK}"/>'
        + f'<rect x="23" y="60" width="3.5" height="7" rx="1.5" fill="{INK}"/>'
        + f'<rect x="70" y="60" width="3.5" height="7" rx="1.5" fill="{INK}"/>'
        + f'<circle cx="51.5" cy="73" r="1.5" fill="{INK}"/>'
    )


def kingdom():
    return T_SUN, (
        band(84, SAND_L)
        + f"<g {OUT}>"
        + f'<path d="M30 86L33 54Q34.5 30 37 9Q41 42 48 44Q55 42 59 9Q61.5 30 63 54L66 86Z" fill="{SKY}"/>'
        + f'<path d="M37 21H59" fill="none" stroke-width="7"/>'
        + f'<path d="M37.5 21H58.5" fill="none" stroke="{WHITE}" stroke-width="2"/>'
        + f'<path d="M24 86H72" fill="none"/>'
        + "</g>"
        + f'<path d="M40 50L38 84" stroke="{WHITE}" stroke-opacity=".55" stroke-width="3" stroke-linecap="round"/>'
        + f'<path d="M34 62H62M33.5 72H62.5" stroke="{INK}" stroke-opacity=".25" stroke-width="2"/>'
    )


def wadi():
    return T_SKY, (
        band(46, LEAF_D) + band(52, "#7FD486")
        + edge_shape("M2 38Q14 32 26 36L36 50Q22 54 2 58Z", "M2 38Q14 32 26 36L36 50Q22 54 2 58", SAND)
        + edge_shape("M94 34Q82 28 70 33L61 49Q76 53 94 56Z", "M94 34Q82 28 70 33L61 49Q76 53 94 56", SAND)
        + f'<path d="M8 44Q18 42 28 44M76 41Q85 39 92 42" stroke="{MUD}" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
        + thick_line("M49 50C40 58 60 64 48 72S38 86 47 95", SKY, 7)
        + f"<g {OUT}>" + palm(24, 84, 26, .85, lean=-1) + palm(72, 82, 24, .8, lean=1) + "</g>"
    )


def turaif():
    return T_SUN, (
        band(82, SAND)
        + f"<g {OUT}>"
        + f'<rect x="44" y="28" width="38" height="56" fill="{SAND}"/>'
        + crenel(44, 82, 28, h=6, w=4.75, fill=SAND)
        + f'<rect x="14" y="48" width="40" height="36" fill="{SAND_L}"/>'
        + crenel(14, 54, 48, h=6, w=5, fill=SAND_L)
        + f'<path d="M70 84L72 18H80L82 84Z" fill="{SAND}"/>'
        + crenel(72, 80, 18, h=5, w=4, fill=SAND)
        + "</g>"
        + tri_row(48, 68, 36, h=4, w=5, gap=3, fill=MUD, down=True)
        + tri_row(17, 52, 56, h=4, w=5, gap=3, fill=MUD, down=True)
        + "".join(f'<rect x="{x}" y="{y}" width="4" height="6" rx="1" fill="{INK}"/>'
                  for x, y in ((50, 46), (60, 46), (50, 62), (60, 62), (20, 66), (30, 66), (40, 66)))
        + f'<rect x="74.5" y="32" width="3" height="7" rx="1.5" fill="{INK}"/>'
        + f'<rect x="74.5" y="52" width="3" height="7" rx="1.5" fill="{INK}"/>'
        + f'<path d="M28 84V76Q32 72 36 76V84Z" fill="{MUD}" {OUT}/>'
    )


def edge():
    return T_SUN, (
        sun_disc(74, 24, 9)
        + band(66, SAND_L)
        + f'<path d="M58 66L66 59L80 61L94 58V66Z" fill="{SAND}" opacity=".7"/>'
        + edge_shape("M2 40L30 34L48 38L56 36L60 44L56 56L62 70L57 82L60 94H24A22 22 0 0 1 2 72Z",
                     "M2 40L30 34L48 38L56 36L60 44L56 56L62 70L57 82L60 93", SAND)
        + f'<path d="M6 50L40 46L56 50M6 62L38 58L56 63M8 76L36 72L57 76" stroke="{MUD}" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
        + f'<path d="M58 44L54 56L60 70L55 82" stroke="{MUD}" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        # tiny person standing at the edge
        + f'<circle cx="51" cy="25" r="2.6" fill="{INK}"/>'
        + f'<path d="M51 28V33M51 33L49 37M51 33L53 37M48 30L54 29" stroke="{INK}" stroke-width="2.2" stroke-linecap="round" fill="none"/>'
    )


def ushaiqer():
    return T_LEAF, (
        f"<g {OUT}>" + palm(22, 60, 30, .8, lean=-1) + palm(74, 56, 28, .8, lean=1) + "</g>"
        + band(80, SAND)
        + f"<g {OUT}>"
        + f'<rect x="36" y="38" width="22" height="46" fill="{SAND}"/>'
        + tri_row(36, 58, 38, h=5, w=4, gap=2.5, fill=SAND).replace('stroke="none"', '')
        + f'<rect x="12" y="54" width="28" height="30" fill="{SAND_L}"/>'
        + f'<rect x="56" y="50" width="28" height="34" fill="{SAND_L}"/>'
        + f'<path d="M12 54H40M56 50H84" fill="none"/>'
        + "</g>"
        + tri_row(15, 38, 61, h=3, w=4, gap=3, fill=MUD, down=True)
        + tri_row(59, 82, 57, h=3, w=4, gap=3, fill=MUD, down=True)
        + "".join(f'<rect x="{x}" y="{y}" width="4" height="6" rx="1" fill="{INK}"/>'
                  for x, y in ((45, 46), (18, 68), (64, 64), (75, 64)))
        + f'<path d="M24 84V74Q28 70 32 74V84Z" fill="{MUD}" {OUT}/>'
        + f'<path d="M42 84V70Q47 65 52 70V84Z" fill="{MUD}" {OUT}/>'
        + f'<path d="M66 84V76Q70 72 74 76V84Z" fill="{MUD}" {OUT}/>'
    )


def buraydah():
    return T_SUN, (
        band(82, SAND_L)
        + f"<g {OUT}>" + palm(28, 84, 32, .9, lean=-2, dates=True)
        + palm(60, 86, 48, 1.12, lean=2, dates=True) + "</g>"
    )


def hail():
    camel = ("M26 60Q27 52 34 51Q38 44 44 48Q48 51 52 54L57 46Q58 41 63 41L67 43L64 46Q63 53 59 60Q56 63 52 63H32Q27 63 26 60Z")
    legs = "M31 62L30 74M36 63L37 74M49 63L48 74M54 62L56 74M27 58Q23 62 24 67"
    return T_FLAME, (
        edge_shape("M2 58L20 30L32 42L46 20L64 44L74 34L94 54V72H2Z", "M2 58L20 30L32 42L46 20L64 44L74 34L94 54", SAND)
        + f'<path d="M40 30L46 20L52 28M70 38L74 34L78 38" stroke="{WHITE}" stroke-opacity=".7" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        + band(70, SAND_L)
        + f"<g {OUT}>"
        + f'<path d="M10 88Q8 60 20 50Q42 38 68 46Q84 52 84 70L86 88Z" fill="{MUD}"/>'
        + "</g>"
        + f'<g transform="translate(4 0)"><path d="{camel}" fill="{SAND_L}"/>'
        + f'<path d="{legs}" fill="none" stroke="{SAND_L}" stroke-width="3.4" stroke-linecap="round"/></g>'
        + f'<path d="M66 58L74 62M68 70H76" stroke="{SAND_L}" stroke-width="3" stroke-linecap="round"/>'
    )


def alula():
    return T_FLAME, (
        sun_disc(76, 20, 7)
        + band(80, SAND_L)
        + f"<g {OUT}>"
        + f'<path d="M8 84C7 66 12 52 24 46C36 40 44 28 60 24C76 21 87 32 87 48C87 60 81 70 83 84H71C71 70 68 58 61 53C55 49 48 53 46 62C45 70 46 78 46 84Z" fill="{SAND}"/>'
        + "</g>"
        + f'<path d="M16 50Q28 44 42 44M14 66Q24 62 38 62M64 30Q76 32 81 44" stroke="{MUD}" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
        + f'<path d="M78 56Q76 68 77 80" stroke="{MUD}" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
        + f'<path d="M30 44Q40 38 48 32" stroke="{WHITE}" stroke-opacity=".55" stroke-width="3" fill="none" stroke-linecap="round"/>'
    )


def hegra():
    steps_l = "M30 30H34V26H38V22H42V18H46"
    steps_r = "M66 30H62V26H58V22H54V18H50"
    return T_SUN, (
        band(84, SAND_L)
        + f"<g {OUT}>"
        + f'<path d="M6 86C4 54 12 26 34 14C52 6 76 12 86 34C92 50 90 70 90 86Z" fill="{SAND}"/>'
        + f'<path d="M28 86V34H68V86Z" fill="{SAND_L}"/>'
        + f'<path d="{steps_l}V30H30Z" fill="{SAND_L}"/><path d="{steps_r}V30H66Z" fill="{SAND_L}"/>'
        + f'<path d="M26 36H70V41H26Z" fill="{SAND_L}"/>'
        + f'<path d="M40 86V62H56V86Z" fill="{MUD}"/>'
        + f'<path d="M38 60L48 52L58 60Z" fill="{SAND_L}"/>'
        + "</g>"
        + f'<path d="M33 46V84M63 46V84" stroke="{MUD}" stroke-width="2.5" stroke-linecap="round"/>'
        + f'<path d="M10 60Q14 48 20 42M80 40Q84 50 84 62" stroke="{MUD}" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
    )


def balad():
    lattice = lambda x, y, w, h: "".join(
        [f'<path d="M{f(x + w * i / 4)} {y}V{y + h}" />' for i in (1, 2, 3)]
        + [f'<path d="M{x} {f(y + h * j / 4)}H{x + w}" />' for j in (1, 2, 3)])
    return T_SKY, (
        band(86, SAND)
        + f"<g {OUT}>"
        + f'<rect x="24" y="16" width="48" height="72" fill="{WHITE}"/>'
        + crenel(24, 72, 16, h=5, w=6, fill=WHITE)
        + f'<rect x="31" y="24" width="34" height="22" rx="2" fill="{MUD}"/>'
        + f'<rect x="29" y="44" width="38" height="5" rx="2" fill="{MUD}"/>'
        + f'<rect x="31" y="54" width="34" height="18" rx="2" fill="{LEAF_D}"/>'
        + f'<rect x="29" y="70" width="38" height="5" rx="2" fill="{LEAF_D}"/>'
        + f'<path d="M42 88V80H54V88Z" fill="{MUD}"/>'
        + "</g>"
        + f'<g stroke="{INK}" stroke-opacity=".55" stroke-width="1.6">{lattice(31, 24, 34, 20)}{lattice(31, 54, 34, 16)}</g>'
        + f'<path d="M26 52H70M26 78H70" stroke="{SAND}" stroke-width="2" />'
    )


def fountain():
    plume = ("M48 15C40 13 30 20 26 36C32 28 39 24 46 24Z", "M48 15C56 13 66 20 70 36C64 28 57 24 50 24Z")
    return T_SKY, (
        sun_disc(16, 18, 6)
        + f'<path d="M2 66H20V60H26V64H34V66Z" fill="{SAND}" opacity=".8"/>'
        + waves(68)
        + f"<g {OUT}>"
        + "".join(f'<path d="{p}" fill="{WHITE}"/>' for p in plume)
        + f'<path d="M45.5 70L47 16Q48 12 49 16L50.5 70Z" fill="{WHITE}"/>'
        + f'<path d="M38 70Q48 64 58 70Z" fill="{WHITE}"/>'
        + "</g>"
        + "".join(f'<circle cx="{x}" cy="{y}" r="2" fill="{SKY}"/>' for x, y in ((24, 44), (30, 50), (72, 44), (66, 50), (27, 56), (69, 56)))
    )


def jtower():   # Jeddah Corniche
    return T_SKY, (
        sun_disc(76, 18, 7)
        + waves(44, amp=2.5, n=4)
        + band(66, SAND_L)
        + f'<path d="M2 66H94V71H2Z" fill="{SAND}"/>'
        + f'<path d="M10 80H34M44 86H70M60 76H86" stroke="{SAND}" stroke-width="3" stroke-linecap="round"/>'
        + f"<g {OUT}>"
        + f'<path d="M6 60H90" fill="none"/>'
        + "".join(f'<path d="M{x} 60V66" fill="none" stroke-width="2.5"/>' for x in (12, 26, 70, 84))
        + f'<path d="M44 84H56L54 80H46Z" fill="{INK}"/>'
        + f'<path d="M50 80V26" fill="none" stroke-width="4"/>'
        + f'<path d="M50 30Q50 20 60 20" fill="none" stroke-width="3"/>'
        + f'<path d="M56 21H66L63 28H59Z" fill="{SUN}"/>'
        + f'<path d="M50 30Q50 20 40 20" fill="none" stroke-width="3"/>'
        + f'<path d="M34 21H44L41 28H37Z" fill="{SUN}"/>'
        + "</g>"
        + f'<circle cx="61" cy="32" r="3" fill="{SUN}" opacity=".6"/><circle cx="39" cy="32" r="3" fill="{SUN}" opacity=".6"/>'
    )


def dammam():
    return T_SKY, (
        sun_disc(20, 22, 7)
        + f"<g {OUT}>"
        + f'<path d="M48 16V62" fill="none" stroke-width="3.5"/>'
        + f'<path d="M50 18L76 56H50Z" fill="{WHITE}"/>'
        + f'<path d="M46 26L26 56H46Z" fill="{SAND_L}"/>'
        + f'<path d="M12 58H84L76 74Q50 80 22 74Z" fill="{MUD}"/>'
        + f'<path d="M12 58L8 52M84 58L88 50" fill="none" stroke-width="3.5"/>'
        + "</g>"
        + f'<path d="M18 64H80" stroke="{SAND}" stroke-width="2.5" stroke-linecap="round"/>'
        + waves(72, amp=2.5, n=4)
    )


def murabba():
    return T_LEAF, (
        f"<g {OUT}>" + palm(81, 62, 34, .6, lean=1) + "</g>"
        + band(80, SAND_L)
        + f"<g {OUT}>"
        + f'<rect x="12" y="34" width="62" height="48" fill="{SAND}"/>'
        + crenel(12, 74, 34, h=6, w=5.17, fill=SAND)
        + f'<path d="M12 56H74" fill="none" stroke-width="2.5"/>'
        + f'<path d="M35 82V66Q43 59 51 66V82Z" fill="{MUD}"/>'
        + "</g>"
        + tri_row(16, 72, 41, h=4, w=4, gap=4, fill=MUD, down=True)
        + "".join(f'<rect x="{x}" y="{y}" width="5" height="7" rx="1" fill="{INK}"/>'
                  for x, y in ((18, 45), (30, 45), (52, 45), (64, 45), (19, 64), (62, 64)))
        + f'<rect x="40.5" y="44" width="5" height="9" rx="2.5" fill="{INK}"/>'
    )


def museum():
    return T_BERRY, (
        band(82, SAND_L)
        + f"<g {OUT}>"
        + f'<path d="M8 82V64C28 62 52 50 70 30C76 24 84 20 88 20V82Z" fill="{SAND_L}"/>'
        + f'<path d="M8 64C28 62 52 50 70 30C76 24 84 20 88 20V30C82 31 76 36 72 40C56 58 32 70 8 72Z" fill="{SAND}"/>'
        + f'<path d="M14 82V76H82V82Z" fill="{SKY}"/>'
        + "</g>"
        + "".join(f'<path d="M{x} 77V81" stroke="{INK}" stroke-opacity=".5" stroke-width="2"/>' for x in (26, 38, 50, 62, 74))
        + f'<path d="M30 64V73M44 58V71M58 50V69M72 40V67" stroke="{MUD}" stroke-width="2.5" stroke-linecap="round"/>'
    )


def boulevard():
    windows = []
    for x0, y0, cols, rows in ((14, 50, 2, 4), (36, 30, 2, 7), (58, 44, 2, 5), (76, 56, 2, 3)):
        for c in range(cols):
            for r in range(rows):
                windows.append(f'<rect x="{x0 + c * 6}" y="{y0 + r * 6}" width="3" height="3" rx="1" fill="{SUN}"/>')
    star = lambda x, y, r: f'<path d="M{x} {y - r}Q{x} {y} {x + r} {y}Q{x} {y} {x} {y + r}Q{x} {y} {x - r} {y}Q{x} {y} {x} {y - r}Z" fill="{SUN}"/>'
    return T_BERRY, (
        f'<path d="M70 10A10 10 0 1 0 80 24A8 8 0 1 1 70 10Z" fill="{SUN}" {OUT}/>'
        + star(20, 18, 4) + star(40, 12, 3) + star(56, 22, 2.5)
        + f"<g {OUT}>"
        + f'<rect x="10" y="44" width="18" height="44" rx="2" fill="{BERRY}"/>'
        + f'<path d="M32 88V28L42 18L52 28V88Z" fill="{INK}"/>'
        + f'<rect x="54" y="38" width="18" height="50" rx="2" fill="{BERRY}"/>'
        + f'<rect x="72" y="50" width="16" height="38" rx="2" fill="{INK}"/>'
        + "</g>"
        + "".join(windows)
        + f'<path d="M42 18V10" stroke="{INK}" stroke-width="3" stroke-linecap="round"/><circle cx="42" cy="9" r="2.2" fill="{FLAME}"/>'
        + band(86, INK)
    )


def rose(x, y, r=7):
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="{ROSE}"/>'
            f'<path d="M{x - r * .45} {y + r * .1}Q{x} {y - r * .7} {x + r * .45} {y}Q{x} {y + r * .5} {x - r * .1} {y - r * .05}" fill="none" stroke="{ROSE_D}" stroke-width="2.2" stroke-linecap="round"/>')


def taif():
    return T_SKY, (
        edge_shape("M2 56L22 30L36 44L54 22L74 46L84 38L94 48V70H2Z", "M2 56L22 30L36 44L54 22L74 46L84 38L94 48", SAND)
        + f'<path d="M48 30L54 22L60 30M18 35L22 30L26 35" stroke="{WHITE}" stroke-opacity=".6" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        + band(62, LEAF)
        + f'<path d="M4 61.5Q26 56 50 62T92 60" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>'
        + f"<g {OUT}>"
        + f'<path d="M30 92V76M50 92V70M70 92V76" fill="none" stroke="{LEAF_D}" stroke-width="3"/>'
        + f'<path d="M50 82Q58 76 62 80Q56 86 50 84Z" fill="{LEAF_D}"/>'
        + f'<path d="M30 84Q22 80 18 84Q24 89 30 87Z" fill="{LEAF_D}"/>'
        + rose(30, 72, 8) + rose(50, 64, 9) + rose(70, 72, 8)
        + "</g>"
    )


def abha():
    return T_SKY, (
        band(42, LEAF_D)
        + f'<path d="M2 50Q48 34 94 46V58Q48 46 2 62Z" fill="{LEAF}"/>'
        + f'<path d="M2 66Q48 50 94 62V74Q48 62 2 78Z" fill="{LEAF}"/>'
        + f'<path d="M4 50Q48 34 92 46M4 62Q48 46 92 58M4 66Q48 50 92 62M4 78Q48 62 92 74" fill="none" {OUT} stroke-width="2.5"/>'
        + f'<path d="M4 42Q48 26 92 38" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>'
        + f"<g {OUT}>"
        + f'<path d="M54 46V14H80V42Z" fill="{WHITE}"/>'
        + "</g>"
        + "".join(f'<path d="M54 {y}H80" stroke="{c}" stroke-width="3"/>' for y, c in ((20, FLAME), (26, SKY), (32, BERRY), (38, SUN)))
        + f'<path d="M54 14V46M80 14V42" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>'
        + tri_row(55, 80, 14, h=4, w=4, gap=1.2, fill=FLAME)
        + f'<rect x="64" y="34" width="6" height="9" rx="1" fill="{INK}"/>'
        + f'<path d="M62 22H72V30H62Z" fill="{LEAF}" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/>'
        + f'<path d="M8 86Q28 80 50 84" stroke="{LEAF_D}" stroke-width="3" fill="none" stroke-linecap="round"/>'
    )


def start():
    return T_LEAF, (
        band(80, "#BDE9C1")
        + f"<g {OUT}>"
        + f'<path d="M30 84V12" fill="none" stroke-width="5"/>'
        + f'<path d="M30 16Q42 10 52 16T76 16V50Q64 56 52 50T30 50Z" fill="{LEAF}"/>'
        + f'<ellipse cx="30" cy="84" rx="12" ry="4" fill="{LEAF_D}"/>'
        + "</g>"
        + f'<path d="M38 26Q46 22 52 25" stroke="{WHITE}" stroke-opacity=".7" stroke-width="3" fill="none" stroke-linecap="round"/>'
        + f'<circle cx="30" cy="11" r="4" fill="{SUN}" {OUT}/>'
    )


def finish():
    cells = []
    for r in range(4):
        for c in range(5):
            if (r + c) % 2 == 0:
                cells.append(f'<rect x="{32 + c * 9}" y="{16 + r * 9}" width="9" height="9" fill="{INK}"/>')
    return T_SUN, (
        band(80, "#FFE29A")
        + f'<g transform="skewY(-6) translate(0 4)">'
        + f'<rect x="32" y="16" width="45" height="36" fill="{WHITE}"/>' + "".join(cells)
        + f'<rect x="32" y="16" width="45" height="36" fill="none" {OUT}/>' + "</g>"
        + f"<g {OUT}>"
        + f'<path d="M30 84V12" fill="none" stroke-width="5"/>'
        + f'<ellipse cx="30" cy="84" rx="12" ry="4" fill="{SUN}"/>'
        + "</g>"
        + f'<circle cx="30" cy="11" r="4" fill="{SUN}" {OUT}/>'
    )


NAMES = {
    "masmak": "Masmak Fortress", "kingdom": "Kingdom Centre", "wadi": "Wadi Hanifa",
    "turaif": "At-Turaif, Diriyah", "edge": "Edge of the World", "ushaiqer": "Ushaiqer Heritage Village",
    "buraydah": "Buraydah date palms", "hail": "Hail rock art", "alula": "Elephant Rock, AlUla",
    "hegra": "Hegra", "balad": "Al-Balad, Jeddah", "fountain": "King Fahd's Fountain",
    "jtower": "Jeddah Corniche", "dammam": "Dammam seafront", "murabba": "Al Murabba Palace",
    "museum": "National Museum", "boulevard": "Riyadh Boulevard", "taif": "Taif rose fields",
    "abha": "Abha mountains", "start": "Start", "finish": "Finish",
}
BUILDERS = {k: globals()[k] for k in NAMES}


def svg(key, label=None):
    tint, body = BUILDERS[key]()
    label = (label or NAMES[key]).replace('"', "&quot;").replace("'", "&#39;")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-label="{label}">'
            f'<rect x="2" y="2" width="92" height="92" rx="22" fill="{tint}"/>{body}</svg>')
