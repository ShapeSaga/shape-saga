"""Planches manga : animaux géométriques coloriés en traits, sans mains, textes en anglais."""
import cairo, math, random
import numpy as np

W, H = 1080, 1920
INK = (0.06, 0.06, 0.08)
WHITE = (0.98, 0.97, 0.95)
RD, RDK = (.86, .18, .14), (.45, .05, .05)
GN, GDK = (.18, .62, .26), (.04, .28, .09)
PU, PUK = (.50, .25, .78), (.25, .08, .42)
R = random.Random(4)


# ---------------- outils ----------------
def new():
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    return s, c


def poly(c, P, close=True):
    c.new_path()
    c.move_to(*P[0])
    for p in P[1:]:
        c.line_to(*p)
    if close:
        c.close_path()


def ink(c, w, col=INK, a=1):
    c.set_source_rgba(*col, a)
    c.set_line_width(w)


def ellipse(c, x, y, rx, ry):
    c.save()
    c.translate(x, y)
    c.scale(rx, ry)
    c.new_path()
    c.arc(0, 0, 1, 0, 2 * math.pi)
    c.restore()


def hatch(c, mk, ang, sp, w, col, a=1):
    """Couleur faite de traits parallèles, limitée à la forme tracée par mk()."""
    c.save()
    mk()
    c.clip()
    x1, y1, x2, y2 = c.clip_extents()
    cx, cy, L = (x1 + x2) / 2, (y1 + y2) / 2, math.hypot(x2 - x1, y2 - y1)
    dx, dy = math.cos(ang), math.sin(ang)
    d = -L / 2
    while d < L / 2:
        ox, oy = cx - dy * d, cy + dx * d
        j = R.uniform(-.4, .4) * w
        poly(c, [(ox - dx * L / 2, oy - dy * L / 2 + j), (ox + dx * L / 2, oy + dy * L / 2 - j)], False)
        ink(c, w * R.uniform(.75, 1.15), col, a)
        c.stroke()
        d += sp
    c.restore()


def halftone(c, step, rmax, fn, col=INK, a=1):
    c.set_source_rgba(*col, a)
    for y in range(0, H, step):
        off = step / 2 if (y // step) % 2 else 0
        for x in range(0, W + step, step):
            v = fn(x + off, y)
            if v > .03:
                c.new_path()
                c.arc(x + off, y, rmax * min(v, 1), 0, 6.3)
                c.fill()


def focus(c, cx, cy, n, r0, col=INK, a=1, wmax=.01):
    c.set_source_rgba(*col, a)
    for _ in range(n):
        t, w, r = R.uniform(0, 2 * math.pi), R.uniform(.002, wmax), R.uniform(*r0)
        poly(c, [(cx + r * math.cos(t), cy + r * math.sin(t)),
                 (cx + 2400 * math.cos(t - w), cy + 2400 * math.sin(t - w)),
                 (cx + 2400 * math.cos(t + w), cy + 2400 * math.sin(t + w))])
        c.fill()


def text(c, txt, font, size, x, y, col=INK, outline=None, ow=0, angle=0):
    c.save()
    c.select_font_face(font)
    c.set_font_size(size)
    e = c.text_extents(txt)
    c.translate(x, y)
    c.rotate(angle)
    c.move_to(-e.width / 2 - e.x_bearing, -e.height / 2 - e.y_bearing)
    c.text_path(txt)
    if outline:
        c.set_source_rgb(*outline)
        c.set_line_width(ow)
        c.stroke_preserve()
    c.set_source_rgb(*col)
    c.fill()
    c.restore()


def bubble_oval(c, x, y, rx, ry, tail, lines, size=58, font="Comic Neue"):
    ellipse(c, x, y, rx, ry)
    c.set_source_rgb(1, 1, 1)
    c.fill_preserve()
    ink(c, 6)
    c.stroke()
    tx, ty = tail
    a = math.atan2(ty - y, tx - x)
    b1 = (x + rx * .8 * math.cos(a - .25), y + ry * .8 * math.sin(a - .25))
    b2 = (x + rx * .8 * math.cos(a + .25), y + ry * .8 * math.sin(a + .25))
    poly(c, [b1, (tx, ty), b2])
    c.set_source_rgb(1, 1, 1)
    c.fill()
    poly(c, [b1, (tx, ty), b2], False)
    ink(c, 6)
    c.stroke()
    n = len(lines)
    for i, l in enumerate(lines):
        text(c, l, font, size, x, y + (i - (n - 1) / 2) * size * 1.08)


def bubble_burst(c, x, y, rx, ry, lines, size=150, col=(.85, .1, .1)):
    pts = []
    for i in range(36):
        a = i * 2 * math.pi / 36
        r = 1.0 if i % 2 else 1.27 + R.uniform(-.06, .08)
        pts.append((x + rx * r * math.cos(a), y + ry * r * math.sin(a)))
    poly(c, pts)
    c.set_source_rgb(1, 1, 1)
    c.fill_preserve()
    ink(c, 8)
    c.stroke()
    n = len(lines)
    for i, (l, s) in enumerate(lines):
        text(c, l, "Bangers", s, x, y + (i - (n - 1) / 2) * size * .95, col, INK, max(6, s / 14), math.radians(-4))


def frame(c, P):
    poly(c, P)
    ink(c, 10)
    c.stroke()


def drop(c, x, y, s=1):
    poly(c, [(x, y - 22 * s), (x + 12 * s, y + 2 * s), (x, y + 14 * s), (x - 12 * s, y + 2 * s)])
    c.set_source_rgb(.65, .88, 1)
    c.fill_preserve()
    ink(c, 3.5 * s)
    c.stroke()


def liquid(c, top, y1=H, amp=14, x0=0, x1=W):
    wave = [(x, top + amp * math.sin(x / 55) + amp * .4 * math.sin(x / 17)) for x in range(x0, x1 + 1, 10)]
    mk = lambda: poly(c, wave + [(x1, y1), (x0, y1)])
    mk()
    c.set_source_rgb(*WHITE)
    c.fill()
    hatch(c, mk, math.radians(-20), 9, 3.4, PU)
    hatch(c, mk, math.radians(60), 14, 2.6, PUK, .8)
    poly(c, wave, False)
    ink(c, 7)
    c.stroke()
    for _ in range(10):
        bx, by, r = R.uniform(x0 + 80, x1 - 80), R.uniform(top + 40, top + 200), R.uniform(5, 15)
        c.new_path()
        c.arc(bx, by, r, 0, 6.3)
        ink(c, 3, WHITE)
        c.stroke()


# ---------------- les personnages ----------------
def eye(c, x, y, rx, ry, iris, look=(0, 0), pupil=.32, tears=False, narrow=False):
    ellipse(c, x, y, rx, ry)
    c.set_source_rgb(1, 1, 1)
    c.fill_preserve()
    ink(c, rx * .1)
    c.stroke()
    c.save()
    ellipse(c, x, y, rx, ry)
    c.clip()
    ix, iy = x + look[0] * rx * .35, y + look[1] * ry * .35
    ellipse(c, ix, iy, rx * .62, ry * .62)
    g = cairo.RadialGradient(ix, iy + ry * .2, 1, ix, iy, ry * .62)
    g.add_color_stop_rgb(0, *[min(1, v + .35) for v in iris])
    g.add_color_stop_rgb(1, *[v * .45 for v in iris])
    c.set_source(g)
    c.fill_preserve()
    ink(c, rx * .05)
    c.stroke()
    ellipse(c, ix, iy, rx * .62 * pupil * 1.6, ry * .62 * pupil * 1.6)
    c.set_source_rgb(*INK)
    c.fill()
    ellipse(c, ix - rx * .28, iy - ry * .3, rx * .2, ry * .14)
    c.set_source_rgb(1, 1, 1)
    c.fill()
    ellipse(c, ix + rx * .22, iy + ry * .3, rx * .08, ry * .06)
    c.fill()
    if tears:
        poly(c, [(x - rx, y + ry * .45)] + [(x - rx + i * rx / 6, y + ry * .45 + ry * .06 * math.sin(i * 1.3)) for i in range(13)] + [(x + rx, y + ry), (x - rx, y + ry)])
        c.set_source_rgba(.55, .82, 1, .6)
        c.fill()
    if narrow:                                   # paupière haute abaissée : regard déterminé
        n = narrow
        poly(c, [(x - rx * 1.2, y - ry * 1.3), (x + rx * 1.2, y - ry * 1.3), (x + rx * 1.2, y - ry * (.85 if n < 0 else .38)), (x - rx * 1.2, y - ry * (.38 if n < 0 else .85))])
        c.set_source_rgb(*WHITE)
        c.fill()
    c.restore()
    if narrow:
        poly(c, [(x - rx * 1.05, y - ry * (.38 if narrow < 0 else .9)), (x + rx * 1.05, y - ry * (.9 if narrow < 0 else .38))], False)
        ink(c, rx * .16)
        c.stroke()


def fox(c, cx, cy, S, rot, expr, look=(0, 0)):
    """Le carré rouge devenu renard. Repère local : visage de -135 à 135."""
    k = S / 270
    sp, lw = 9 / k ** .55, 3.4 / k ** .55
    c.save()
    c.translate(cx, cy)
    c.rotate(rot)
    c.scale(k, k)
    s = 135
    for ex in (-1, 1):
        ear = [(ex * s, -s + 20), (ex * (s - 10), -s - 105), (ex * (s - 105), -s)]
        poly(c, ear); c.set_source_rgb(*WHITE); c.fill()
        hatch(c, lambda e=ear: poly(c, e), math.radians(60), sp, lw, RD)
        poly(c, ear); ink(c, 8); c.stroke()
        inner = [(ex * (s - 18), -s - 5), (ex * (s - 22), -s - 65), (ex * (s - 75), -s - 5)]
        hatch(c, lambda e=inner: poly(c, e), math.radians(-30), sp * .7, lw * .8, RDK)
    face = lambda: c.rectangle(-s, -s, 2 * s, 2 * s)
    face(); c.set_source_rgb(*WHITE); c.fill()
    hatch(c, face, math.radians(50), sp, lw, RD)
    hatch(c, lambda: poly(c, [(s, -s), (s, s), (-s, s)]), math.radians(-40), sp * 1.1, lw * .8, RDK, .8)
    muz = [(-s, 0), (-s / 2, -10), (0, 45), (s / 2, -10), (s, 0), (s, s), (-s, s)]
    poly(c, muz); c.set_source_rgb(*WHITE); c.fill()
    hatch(c, lambda: poly(c, [(-s, 60), (s, 60), (s, s), (-s, s)]), math.radians(-40), sp * 1.3, lw * .6, INK, .25)
    poly(c, muz[:5], False); ink(c, 5); c.stroke()
    face(); ink(c, 9); c.stroke()
    poly(c, [(-16, 18), (16, 18), (0, 34)]); c.set_source_rgb(*INK); c.fill()
    BR = (.86, .45, .12)
    if expr == "serene":
        for sx in (-1, 1):
            c.new_path(); c.arc(sx * 55, -40, 30, math.radians(200), math.radians(340)); ink(c, 8); c.stroke()
        c.new_path(); c.arc(0, 40, 26, math.radians(25), math.radians(155)); ink(c, 7); c.stroke()
        drop(c, 92, 0, .8)
    elif expr == "determined":
        for sx in (-1, 1):
            eye(c, sx * 58, -32, 40, 34, BR, (0, 0), .26, narrow=sx)
            poly(c, [(sx * 118, -96), (sx * 24, -64), (sx * 20, -46), (sx * 112, -76)]); c.set_source_rgb(*INK); c.fill()
        m = [(-58, 50), (58, 50), (52, 92), (-52, 92)]
        poly(c, m); c.set_source_rgb(1, 1, 1); c.fill_preserve(); ink(c, 6); c.stroke()
        poly(c, [(-56, 71), (56, 71)], False); ink(c, 3); c.stroke()
        for u in (-28, 0, 28):
            poly(c, [(u, 52), (u, 90)], False); ink(c, 3); c.stroke()
        drop(c, 112, -112, .9)
    elif expr == "scared":
        for sx in (-1, 1):
            eye(c, sx * 56, -32, 36, 42, BR, look, .2)
            poly(c, [(sx * 100, -95), (sx * 25, -110), (sx * 22, -96), (sx * 98, -82)]); c.set_source_rgb(*INK); c.fill()
        wob = [(-34 + i * 68 / 10, 70 + 6 * math.sin(i * 2.4)) for i in range(11)]
        poly(c, wob + [(30, 95), (-30, 95)]); c.set_source_rgb(.2, .05, .06); c.fill_preserve(); ink(c, 5); c.stroke()
        drop(c, -115, -100, .8); drop(c, 120, -60, .6)
    c.restore()


def cat(c, cx, cy, Rr, expr, look=(0, 0), tear_len=0):
    """Le rond vert devenu chat. Repère local : rayon 200."""
    k = Rr / 200
    sp, lw = 11 / k ** .55, 4 / k ** .55
    c.save()
    c.translate(cx, cy)
    c.scale(k, k)
    r = 200
    for t in (math.radians(232), math.radians(308)):
        bx, by = r * .93 * math.cos(t), r * .93 * math.sin(t)
        tip = ((r + 70) * math.cos(t), (r + 70) * math.sin(t))
        nx, ny = -math.sin(t), math.cos(t)
        ear = [(bx + nx * 55, by + ny * 55), tip, (bx - nx * 55, by - ny * 55)]
        poly(c, ear); c.set_source_rgb(*WHITE); c.fill()
        hatch(c, lambda e=ear: poly(c, e), math.radians(70), sp, lw, GN)
        poly(c, ear); ink(c, 9); c.stroke()
    circ = lambda: (c.new_path(), c.arc(0, 0, r, 0, 2 * math.pi))
    circ(); c.set_source_rgb(*WHITE); c.fill()
    hatch(c, circ, math.radians(35), sp, lw, GN)

    def ombre():
        circ(); c.clip()
        c.new_path(); c.arc(-55, -60, r * 1.02, 0, 2 * math.pi)
        c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD); c.rectangle(-500, -500, 1000, 1000)
    hatch(c, ombre, math.radians(-50), sp, lw * .8, GDK, .85)
    c.set_fill_rule(cairo.FILL_RULE_WINDING)
    circ(); ink(c, 10); c.stroke()
    # nez + moustaches
    poly(c, [(-10, 30), (10, 30), (0, 42)]); c.set_source_rgb(.85, .35, .45); c.fill_preserve(); ink(c, 3); c.stroke()
    for sx in (-1, 1):
        for q in (-1, 0, 1):
            poly(c, [(sx * 62, 38 + q * 8), (sx * 120, 30 + q * 17)], False); ink(c, 3); c.stroke()
    G = (.25, .75, .30)
    if expr in ("scared", "crying", "resolve"):
        for sx in (-1, 1):
            if expr == "crying":
                poly(c, [(sx * 120, -98), (sx * 38, -132), (sx * 33, -120), (sx * 116, -86)])
            elif expr == "resolve":
                poly(c, [(sx * 135, -150), (sx * 22, -78), (sx * 18, -56), (sx * 128, -124)])
            else:
                poly(c, [(sx * 120, -100), (sx * 40, -122), (sx * 36, -110), (sx * 116, -88)])
            c.set_source_rgb(*INK); c.fill()
            if tear_len and expr != "scared":
                x0 = sx * 75 + sx * 14
                L = [(x0 + 7 * math.sin(y / 22) - 12, y) for y in range(10, int(10 + tear_len), 6)]
                Rt = [(x0 + 7 * math.sin(y / 22) + 12 + (y - 10) * .04, y) for y in range(10, int(10 + tear_len), 6)]
                if len(L) > 2:
                    poly(c, L + Rt[::-1]); c.set_source_rgb(.62, .87, 1); c.fill_preserve(); ink(c, 3); c.stroke()
            eye(c, sx * 75, -40, 50, 60, G, look, .18 if expr != "resolve" else .3, tears=expr != "scared", narrow=sx if expr == "resolve" else False)
            for q in range(4):
                poly(c, [(sx * (60 + q * 10) - 4, 62), (sx * (60 + q * 10) - 9, 74)], False); ink(c, 3, (.85, .25, .30)); c.stroke()
        if expr == "crying":
            m = [(-52 + i * 104 / 16, 112 - 30 * math.sin(math.pi * i / 16) + 3 * math.sin(i * 2.3)) for i in range(17)] + [(34, 130), (0, 137), (-34, 130)]
            poly(c, m); c.set_source_rgb(.18, .04, .06); c.fill_preserve(); ink(c, 5); c.stroke()
            ellipse(c, 0, 129, 18, 6); c.set_source_rgb(.85, .35, .40); c.fill()
        elif expr == "resolve":
            m = [(-42, 92), (42, 92), (38, 122), (-38, 122)]
            poly(c, m); c.set_source_rgb(1, 1, 1); c.fill_preserve(); ink(c, 5); c.stroke()
            poly(c, [(-40, 107), (40, 107)], False); ink(c, 2.5); c.stroke()
            for u in (-20, 0, 20):
                poly(c, [(u, 93), (u, 121)], False); ink(c, 2.5); c.stroke()
        else:
            wob = [(-30 + i * 6, 95 + 5 * math.sin(i * 2.4)) for i in range(11)]
            poly(c, wob + [(28, 116), (-28, 116)]); c.set_source_rgb(.2, .05, .06); c.fill_preserve(); ink(c, 4); c.stroke()
            drop(c, 150, -120, .7)
    elif expr == "sad_smile":
        for sx in (-1, 1):
            c.new_path(); c.arc(sx * 75, -45, 40, math.radians(20), math.radians(160)); ink(c, 8); c.stroke()
            poly(c, [(sx * 120, -112), (sx * 40, -128), (sx * 36, -116), (sx * 116, -100)]); c.set_source_rgb(*INK); c.fill()
            for q in range(4):
                poly(c, [(sx * (60 + q * 10) - 4, 62), (sx * (60 + q * 10) - 9, 74)], False); ink(c, 3, (.85, .25, .30)); c.stroke()
        drop(c, 112, 5, .9)
        c.new_path(); c.arc(0, 70, 28, math.radians(30), math.radians(150)); ink(c, 6); c.stroke()
    c.restore()


# ---------------- les planches ----------------
FR = [(40, 60), (1040, 60), (1040, 1860), (40, 1860)]


def page():
    s, c = new()
    c.set_source_rgb(*WHITE)
    c.paint()
    return s, c


def layer():
    return new()


def p_danger():
    s, c = page()
    c.save(); poly(c, FR); c.clip()
    halftone(c, 16, 7, lambda x, y: max(0, (900 - y) / 900) * .9, INK, .55)
    focus(c, 540, 1500, 160, (700, 1000), INK, .8)
    liquid(c, 1430)
    fox(c, 330, 950, 330, math.radians(5), "scared", (0, 1))
    cat(c, 770, 1000, 175, "scared", (-.2, 1))
    c.restore(); frame(c, FR)
    b1, c1 = layer()
    bubble_burst(c1, 700, 330, 290, 110, [("IT'S RISING!!", 110)], 110)
    b2, c2 = layer()
    bubble_oval(c2, 300, 560, 220, 95, (330, 730), ["Stay close", "to me."], 56)
    return s, [(b1, .15, (700, 330)), (b2, 1.0, (300, 560))]


def p_go():
    s, c = page()
    c.save(); poly(c, FR); c.clip()
    c.set_source_rgb(1, .93, .90); c.paint()
    focus(c, 540, 1180, 360, (480, 640), RDK, .9)
    halftone(c, 14, 6.5, lambda x, y: max(0, (math.hypot(x - 540, y - 1180) - 700) / 500), INK, .8)
    fox(c, 540, 1220, 700, math.radians(-5), "determined")
    c.restore(); frame(c, FR)
    b, cb = layer()
    bubble_burst(cb, 540, 300, 400, 160, [("GO!!", 190), ("I GOT YOU!", 100)], 150)
    return s, [(b, .12, (540, 300))]


def p_sink_cry():
    """Page en 2 cases : renard qui s'enfonce (haut), cri du chat (bas). Rend (page haut seule, page complète)."""
    s, c = page()
    P1 = [(40, 60), (1040, 60), (1040, 640), (40, 730)]
    c.save(); poly(c, P1); c.clip()
    g = cairo.LinearGradient(0, 60, 0, 730)
    g.add_color_stop_rgb(0, .12, .10, .18); g.add_color_stop_rgb(1, .26, .16, .34)
    c.set_source(g); c.paint()
    for _ in range(40):
        y, x = R.uniform(80, 600), R.uniform(-100, 900)
        poly(c, [(x, y), (x + R.uniform(150, 500), y)], False); ink(c, R.uniform(1, 3), WHITE, R.uniform(.08, .25)); c.stroke()
    fox(c, 560, 520, 280, math.radians(-7), "serene")
    liquid(c, 565, 740, 12)
    c.restore(); frame(c, P1)
    bubble_oval(c, 270, 210, 190, 90, (420, 330), ["Go on...", "without me."], 54)
    top = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ct = cairo.Context(top); ct.set_source_surface(s); ct.paint()
    P2 = [(40, 770), (1040, 680), (1040, 1860), (40, 1860)]
    c.save(); poly(c, P2); c.clip()
    c.set_source_rgb(*WHITE); c.paint()
    focus(c, 540, 1280, 420, (560, 700), INK, 1)
    halftone(c, 14, 6.5, lambda x, y: max(0, (math.hypot(x - 540, y - 1420) - 620) / 600), INK, .9)
    cat(c, 540, 1440, 520, "crying", (0, .15), tear_len=320)
    c.restore(); frame(c, P2)
    b, cb = layer()
    bubble_burst(cb, 560, 820, 360, 130, [("RED!!!", 200)], 190)
    return top, s, [(b, .1, (560, 820))]


def p_resolve():
    s, c = page()
    c.save(); poly(c, FR); c.clip()
    c.set_source_rgb(.93, 1, .93); c.paint()
    ang = math.radians(-70)
    for _ in range(140):                                       # lignes de vitesse vers le haut
        x = R.uniform(0, W); y = R.uniform(0, H); L = R.uniform(200, 700)
        poly(c, [(x, y), (x + L * math.cos(ang), y + L * math.sin(ang))], False); ink(c, R.uniform(2, 6), GDK, .5); c.stroke()
    cat(c, 540, 1100, 430, "resolve", (0, -.3), tear_len=150)
    c.restore(); frame(c, FR)
    b, cb = layer()
    bubble_burst(cb, 540, 300, 420, 150, [("I WON'T LET IT", 96), ("BE FOR NOTHING!", 96)], 110, GDK)
    return s, [(b, .15, (540, 300))]


def p_end():
    s, c = page()
    c.save(); poly(c, FR); c.clip()
    c.set_source_rgb(1, .98, .88); c.paint()
    for i in range(22):                                        # rayons de lumière de la sortie
        a = math.radians(20 + i * 140 / 21)
        w = .035
        mk = lambda a=a: poly(c, [(540, -40), (540 + 2400 * math.cos(a - w), -40 + 2400 * math.sin(a - w)), (540 + 2400 * math.cos(a + w), -40 + 2400 * math.sin(a + w))])
        if i % 2 == 0:
            hatch(c, mk, math.radians(10), 10, 3, (.98, .75, .15), .9)
    liquid(c, 1420)
    for i in range(6):                                         # dernières bulles là où Rouge a coulé
        c.new_path(); c.arc(560 + 18 * math.sin(i), 1500 + i * 55, 8 + i * 2, 0, 6.3); ink(c, 3.5, WHITE); c.stroke()
    cat(c, 540, 830, 250, "sad_smile")
    c.restore(); frame(c, FR)
    b, cb = layer()
    bubble_oval(cb, 540, 1240, 300, 90, (560, 1100), ["Thank you... Red."], 62)
    return s, [(b, .7, (540, 1240))]


def p_card():
    s, c = page()
    text(c, "EVERY SHAPE", "Bangers", 140, 540, 700)
    text(c, "HAS A STORY.", "Bangers", 140, 540, 860)
    text(c, "A new story tomorrow.", "Comic Neue", 64, 540, 1060)
    sq = lambda: c.rectangle(380, 1200, 130, 130)
    sq(); c.set_source_rgb(*WHITE); c.fill(); hatch(c, sq, math.radians(50), 9, 3.4, RD); sq(); ink(c, 7); c.stroke()
    ci = lambda: (c.new_path(), c.arc(635, 1265, 66, 0, 6.3))
    ci(); c.set_source_rgb(*WHITE); c.fill(); hatch(c, ci, math.radians(35), 9, 3.4, GN); ci(); ink(c, 7); c.stroke()
    b, cb = layer()
    text(cb, "FOLLOW  >", "Bangers", 130, 540, 1550, (.85, .1, .1), INK, 9)
    return s, [(b, .6, (540, 1550))]


def build_all():
    top, full, cry_b = p_sink_cry()
    return dict(danger=p_danger(), go=p_go(), sink=(top, []), cry=(full, cry_b),
                resolve=p_resolve(), end=p_end(), card=p_card())


if __name__ == "__main__":
    import subprocess
    P = build_all()
    for k, (s, bs) in P.items():
        c = cairo.Context(s)
        for b, _, _ in bs:
            c.set_source_surface(b); c.paint()
        s.write_to_png(f"/tmp/claude-0/-home-claude/56676813-256f-5641-9475-e8a27abd9f2e/scratchpad/{k}.png")
    print("ok")
