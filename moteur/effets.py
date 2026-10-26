"""Fonds de planches manga : chaque fonction peint une page entière 1080x1920 (le cadre est appliqué ensuite).
 - émotion : pluie, vitre, sakura, coucher, aube, plumes, etoiles
 - shonen  : vitesse, eclair, aura, onde, explosion, soleil
Signature commune : f(c, col, rr) ; col = couleur du héros, rr = random.Random de l'épisode (variations)."""
import math, random, cairo

W, H = 1080, 1920
INK = (.07, .06, .09)


def _lg(y0, y1, stops, x0=0, x1=0):
    g = cairo.LinearGradient(x0, y0, x1, y1)
    for o, col, a in stops:
        g.add_color_stop_rgba(o, *col, a)
    return g


def _fond(c, stops):
    c.set_source(_lg(0, H, stops)); c.paint()


def _glow(c, x, y, r, col, a0=.9, a1=0., core=0.):
    g = cairo.RadialGradient(x, y, r * core, x, y, r)
    g.add_color_stop_rgba(0, *col, a0); g.add_color_stop_rgba(1, *col, a1)
    c.set_source(g); c.new_path(); c.arc(x, y, r, 0, 6.2832); c.fill()


def _star4(c, x, y, r, col, a=1.0):
    c.new_path()
    for i in range(8):
        ang = i * math.pi / 4 - math.pi / 2
        rad = r if i % 2 == 0 else r * .2
        (c.move_to if i == 0 else c.line_to)(x + rad * math.cos(ang), y + rad * math.sin(ang))
    c.close_path(); c.set_source_rgba(*col, a); c.fill()


def _sparkles(c, rr, n, col=(1, 1, 1), rmin=6, rmax=26, box=(0, 0, W, H)):
    for _ in range(n):
        x, y = rr.uniform(box[0], box[2]), rr.uniform(box[1], box[3])
        r = rr.uniform(rmin, rmax)
        _glow(c, x, y, r * 1.6, col, .5, 0, .1); _star4(c, x, y, r, col, .95)


def _wedges(c, cx, cy, n, r_in, r_out, col, a, rr, wmin=.012, wmax=.05):
    """Traits de vitesse effilés qui partent du centre (effet manga 'choc')."""
    for _ in range(n):
        ang = rr.uniform(0, 6.2832); w = rr.uniform(wmin, wmax); ri = rr.uniform(*r_in)
        c.new_path()
        c.move_to(cx + ri * math.cos(ang - w), cy + ri * math.sin(ang - w))
        c.line_to(cx + r_out * math.cos(ang), cy + r_out * math.sin(ang))
        c.line_to(cx + ri * math.cos(ang + w), cy + ri * math.sin(ang + w)); c.close_path()
        c.set_source_rgba(*col, a * rr.uniform(.55, 1)); c.fill()


def _rays(c, cx, cy, n, col, a, rot=0, alt=True, r=2600):
    for i in range(n):
        if alt and i % 2:
            continue
        a0 = rot + i * 2 * math.pi / n; a1 = a0 + math.pi / n
        c.new_path(); c.move_to(cx, cy); c.line_to(cx + r * math.cos(a0), cy + r * math.sin(a0)); c.line_to(cx + r * math.cos(a1), cy + r * math.sin(a1)); c.close_path()
        c.set_source_rgba(*col, a); c.fill()


def _halftone(c, step, rmax, fn, col, a=1.0):
    c.set_source_rgba(*col, a)
    for y in range(0, H, step):
        off = step / 2 if (y // step) % 2 else 0
        for x in range(-step, W + step, step):
            k = fn(x + off, y)
            if k > .04:
                c.new_path(); c.arc(x + off, y, rmax * min(1, k), 0, 6.2832); c.fill()


def _bolt(c, x0, y0, x1, y1, rr, jitter=70, seg=9):
    pts = [(x0, y0)]
    for i in range(1, seg):
        t = i / seg
        pts.append((x0 + (x1 - x0) * t + rr.uniform(-jitter, jitter), y0 + (y1 - y0) * t + rr.uniform(-jitter * .35, jitter * .35)))
    pts.append((x1, y1))
    return pts


def _trace(c, pts, w, col, a):
    c.new_path(); c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.set_source_rgba(*col, a); c.set_line_width(w); c.set_line_join(cairo.LINE_JOIN_MITER); c.stroke()


def _flamme(c, x, y, w, h, cols, sway=0):
    for k, col in enumerate(cols):
        s = 1 - k * .24
        c.new_path(); c.move_to(x - w * s / 2, y)
        c.curve_to(x - w * s * .6, y - h * s * .45, x + sway * s - w * s * .15, y - h * s * .7, x + sway * s, y - h * s)
        c.curve_to(x + sway * s + w * s * .1, y - h * s * .62, x + w * s * .62, y - h * s * .4, x + w * s / 2, y)
        c.close_path(); c.set_source_rgb(*col); c.fill()


def _petale(c, x, y, s, ang, col, a):
    c.save(); c.translate(x, y); c.rotate(ang)
    c.new_path(); c.move_to(0, -s); c.curve_to(s * .9, -s * .6, s * .8, s * .5, 0, s); c.curve_to(-s * .8, s * .5, -s * .9, -s * .6, 0, -s)
    c.set_source_rgba(*col, a); c.fill()
    c.move_to(0, -s * .8); c.line_to(0, s * .7); c.set_source_rgba(1, 1, 1, .35); c.set_line_width(1.5); c.stroke()
    c.restore()


def _plume(c, x, y, s, ang, a):
    c.save(); c.translate(x, y); c.rotate(ang)
    c.new_path(); c.move_to(0, -s)
    c.curve_to(s * .5, -s * .55, s * .45, s * .5, 0, s); c.curve_to(-s * .45, s * .5, -s * .5, -s * .55, 0, -s)
    c.set_source_rgba(1, 1, 1, a); c.fill_preserve(); c.set_source_rgba(.85, .75, .5, a * .8); c.set_line_width(2); c.stroke()
    c.move_to(0, -s); c.curve_to(s * .05, 0, -s * .05, s * .4, 0, s * 1.25); c.set_source_rgba(.8, .7, .45, a); c.set_line_width(2.5); c.stroke()
    for k in range(-5, 6):
        c.move_to(0, k * s * .13); c.line_to(s * .42 * (1 - abs(k) / 7), k * s * .13 + s * .12); c.set_source_rgba(.85, .75, .5, a * .5); c.set_line_width(1.2); c.stroke()
    c.restore()


def _nuage(c, x, y, s, col, a):
    for dx, dy, r in ((-1.0, .2, .75), (-.4, -.15, 1.0), (.35, -.05, .9), (1.0, .22, .7), (0, .3, 1.1)):
        _glow(c, x + dx * s, y + dy * s, r * s, col, a, 0, .4)


# =================================================================== ÉMOTION
def fond_pluie(c, col, rr):
    _fond(c, [(0, (.13, .16, .26), 1), (.55, (.30, .36, .48), 1), (1, (.50, .58, .68), 1)])
    for _ in range(11):
        _nuage(c, rr.uniform(0, W), rr.uniform(-40, 380), rr.uniform(140, 260), (.08, .10, .18), .55)
    for _ in range(26):                                              # lumières floues de la ville
        _glow(c, rr.uniform(0, W), rr.uniform(1000, 1650), rr.uniform(40, 120), rr.choice(((.5, .7, 1), (1, .8, .5), (.7, .6, 1))), .35, 0, .2)
    c.set_source(_lg(1620, H, [(0, (.55, .65, .78), .0), (1, (.75, .82, .92), .85)])); c.rectangle(0, 1620, W, H - 1620); c.fill()   # sol mouillé
    for _ in range(260):
        x, y, L = rr.uniform(-100, W + 100), rr.uniform(-100, 1700), rr.uniform(70, 190)
        c.move_to(x, y); c.line_to(x - L * .22, y + L); c.set_source_rgba(.85, .92, 1, rr.uniform(.18, .55)); c.set_line_width(rr.uniform(1.6, 3.6)); c.stroke()
    for _ in range(40):                                              # ondulations
        x, y = rr.uniform(60, 1020), rr.uniform(1680, 1880); r = rr.uniform(14, 52)
        c.save(); c.translate(x, y); c.scale(1, .28); c.new_path(); c.arc(0, 0, r, 0, 6.28); c.restore()
        c.set_source_rgba(1, 1, 1, .45); c.set_line_width(2); c.stroke()


def fond_vitre(c, col, rr):
    cx, cy = 540, 960
    _fond(c, [(0, (.05, .04, .14), 1), (1, (.16, .08, .24), 1)])
    _glow(c, cx, cy, 900, (.45, .25, .85), .55, 0, 0)
    ends = []
    n = 17
    for i in range(n):
        ang = i * 2 * math.pi / n + rr.uniform(-.1, .1)
        pts = [(cx, cy)]
        r = 0
        a = ang
        while r < 1500:
            r += rr.uniform(70, 150); a += rr.uniform(-.06, .06)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        ends.append(pts)
    for i in range(n):                                               # éclats de verre : triangles entre fissures voisines
        p, q = ends[i], ends[(i + 1) % n]
        for k in range(1, min(len(p), len(q)) - 1):
            c.new_path(); c.move_to(*p[k]); c.line_to(*p[k + 1]); c.line_to(*q[k + 1]); c.line_to(*q[k]); c.close_path()
            c.set_source_rgba(*((.75, .85, 1) if rr.random() > .5 else (.2, .15, .45)), rr.uniform(.06, .30)); c.fill()
    for pts in ends:
        _trace(c, pts, 9, (.7, .85, 1), .35); _trace(c, pts, 3.5, (1, 1, 1), .95)
        for k in range(2, len(pts) - 1, 2):                          # branches secondaires
            bx, by = pts[k]; a = rr.uniform(0, 6.28); L = rr.uniform(60, 150)
            _trace(c, [(bx, by), (bx + L * math.cos(a), by + L * math.sin(a))], 2.2, (1, 1, 1), .8)
    for r in (95, 190, 300):                                         # fissures en toile d'araignée
        pts = [(cx + r * math.cos(i * 6.2832 / n + rr.uniform(-.05, .05)), cy + r * math.sin(i * 6.2832 / n)) for i in range(n)]
        _trace(c, pts + [pts[0]], 2.2, (1, 1, 1), .75)
    _glow(c, cx, cy, 260, (1, 1, 1), .85, 0, .15)
    _sparkles(c, rr, 24, (.85, .93, 1), 5, 16)


def fond_vitesse(c, col, rr):
    cx, cy = 540, 1000
    c.set_source_rgb(1, 1, 1); c.paint()
    _glow(c, cx, cy, 1300, _tint(col, .75), .50, 0, .1)
    _wedges(c, cx, cy, 220, (330, 520), 2400, INK, .95, rr, .006, .030)
    _wedges(c, cx, cy, 70, (500, 760), 2400, INK, .55, rr, .004, .014)
    _halftone(c, 14, 6, lambda x, y: max(0, (math.hypot(x - cx, y - cy) - 700) / 700), INK, .55)
    _glow(c, cx, cy, 460, (1, 1, 1), 1, 0, .8)


def fond_eclair(c, col, rr):
    _fond(c, [(0, (.07, .03, .20), 1), (.6, (.20, .08, .42), 1), (1, (.12, .05, .26), 1)])
    _glow(c, 540, 900, 900, (.55, .35, 1), .55, 0, 0)
    _wedges(c, 540, 900, 80, (300, 500), 2200, (.75, .6, 1), .35, rr, .004, .02)
    for sx in (60, 300, 540, 780, 1020):
        tx = rr.uniform(200, 880)
        pts = _bolt(c, sx, -20, tx, rr.uniform(850, 1250), rr, 80, 11)
        _trace(c, pts, 34, (.5, .3, 1), .20); _trace(c, pts, 18, (.7, .6, 1), .35); _trace(c, pts, 9, (.9, .9, 1), .8); _trace(c, pts, 4, (1, 1, 1), 1)
        for k in range(2, len(pts) - 2, 3):
            b = _bolt(c, pts[k][0], pts[k][1], pts[k][0] + rr.uniform(-260, 260), pts[k][1] + rr.uniform(120, 330), rr, 40, 5)
            _trace(c, b, 7, (.7, .6, 1), .5); _trace(c, b, 2.5, (1, 1, 1), 1)
    c.set_source(_lg(1650, H, [(0, (.04, .02, .12), 0), (1, (.04, .02, .12), 1)])); c.rectangle(0, 1650, W, H - 1650); c.fill()
    for _ in range(14):                                              # sol fendu éclairé
        x = rr.uniform(0, W); pts = _bolt(c, x, 1900, x + rr.uniform(-160, 160), 1700 + rr.uniform(0, 120), rr, 30, 6)
        _trace(c, pts, 8, (.7, .6, 1), .5); _trace(c, pts, 3, (1, 1, 1), 1)
    _sparkles(c, rr, 22, (.85, .8, 1), 5, 18)


def fond_aura(c, col, rr):
    _fond(c, [(0, (.08, .02, .04), 1), (.7, (.30, .06, .03), 1), (1, (.55, .13, .02), 1)])
    _glow(c, 540, 1000, 950, (1, .45, .08), .75, 0, 0)
    _wedges(c, 540, 1000, 150, (320, 560), 2300, (1, .75, .25), .55, rr, .005, .022)
    for lay, (cols, hs) in enumerate((([(.55, .06, .02), (.85, .20, .03), (1, .48, .08)], (900, 1300)),
                                      ([(.95, .30, .04), (1, .58, .10), (1, .85, .35)], (700, 1050)))):
        for i in range(9):
            x = 40 + i * 125 + rr.uniform(-30, 30) + lay * 50
            _flamme(c, x, 2000, rr.uniform(240, 330), rr.uniform(*hs), cols, rr.uniform(-120, 120))
    _glow(c, 540, 1050, 420, (1, .95, .7), .75, 0, .2)               # aura brûlante autour du héros
    for _ in range(110):                                             # braises
        x, y = rr.uniform(0, W), rr.uniform(0, 1900); r = rr.uniform(3, 9)
        _glow(c, x, y, r * 2.2, (1, .7, .2), .9, 0, .2)
    _sparkles(c, rr, 10, (1, .9, .5), 6, 20)


def fond_onde(c, col, rr):
    cx, cy = 540, 1000
    _fond(c, [(0, (1, .92, .55), 1), (1, (1, .62, .20), 1)])
    _rays(c, cx, cy, 36, (1, 1, .85), .55, rr.uniform(0, 1))
    for k, (rx, ry) in enumerate(((330, 300), (520, 470), (730, 660), (960, 880), (1200, 1090))):   # ondes de choc
        c.save(); c.translate(cx, cy); c.scale(rx / 100, ry / 100); c.new_path(); c.arc(0, 0, 100, 0, 6.2832); c.restore()
        c.set_source_rgba(1, 1, 1, .50 - k * .06); c.set_line_width(60 - k * 8); c.stroke_preserve(); c.set_source_rgba(*INK, .92); c.set_line_width(7); c.stroke()
    _halftone(c, 16, 7, lambda x, y: max(0, (math.hypot(x - cx, y - cy) - 380) / 900), (.85, .25, .05), .55)
    for _ in range(26):                                              # débris projetés
        a = rr.uniform(0, 6.2832); d = rr.uniform(380, 950); s = rr.uniform(20, 70)
        x, y = cx + d * math.cos(a), cy + d * math.sin(a) * 1.05
        pts = [(x + s * math.cos(a + k * 1.26 + rr.uniform(-.3, .3)), y + s * math.sin(a + k * 1.26 + rr.uniform(-.3, .3))) for k in range(5)]
        c.new_path(); c.move_to(*pts[0]); [c.line_to(*p) for p in pts[1:]]; c.close_path()
        c.set_source_rgb(.55, .33, .20); c.fill_preserve(); c.set_source_rgba(*INK, 1); c.set_line_width(5); c.stroke()
    c.set_source(_lg(1600, H, [(0, (.45, .25, .12), 0), (1, (.45, .25, .12), .9)])); c.rectangle(0, 1600, W, H - 1600); c.fill()
    for _ in range(9):                                               # nuages de poussière
        _nuage(c, rr.uniform(0, W), rr.uniform(1700, 1900), rr.uniform(90, 160), (.95, .85, .65), .75)


def fond_explosion(c, col, rr):
    cx, cy = 540, 1000
    _fond(c, [(0, (.10, .03, .03), 1), (1, (.25, .06, .04), 1)])
    g = cairo.RadialGradient(cx, cy, 40, cx, cy, 1100)
    for o, k in ((0, (1, 1, .9)), (.18, (1, .92, .35)), (.4, (1, .55, .1)), (.7, (.75, .15, .05)), (1, (.15, .03, .03))):
        g.add_color_stop_rgba(o, *k, 1)
    c.set_source(g); c.paint()
    _wedges(c, cx, cy, 160, (260, 420), 2300, (1, 1, .85), .6, rr, .004, .02)
    for ring in range(2):                                            # nuage en champignon : boules encrées
        for i in range(16):
            a = i * 6.2832 / 16 + ring * .2; r = 520 + ring * 160 + rr.uniform(-40, 40)
            x, y, s = cx + r * math.cos(a), cy + r * math.sin(a), rr.uniform(120, 210)
            c.new_path(); c.arc(x, y, s, 0, 6.2832)
            _gc = cairo.RadialGradient(x - s * .3, y - s * .3, 10, x, y, s)
            _gc.add_color_stop_rgba(0, 1, .85, .3, 1); _gc.add_color_stop_rgba(1, .75, .18, .06, 1)
            c.set_source(_gc); c.fill_preserve(); c.set_source_rgba(*INK, 1); c.set_line_width(9); c.stroke()
    _glow(c, cx, cy, 480, (1, 1, .9), 1, 0, .55)
    for _ in range(40):                                              # étincelles filantes
        a = rr.uniform(0, 6.2832); d = rr.uniform(600, 1200); L = rr.uniform(40, 110)
        x, y = cx + d * math.cos(a), cy + d * math.sin(a)
        c.move_to(x, y); c.line_to(x + L * math.cos(a), y + L * math.sin(a)); c.set_source_rgba(1, .9, .4, .95); c.set_line_width(rr.uniform(3, 7)); c.stroke()


def fond_aube(c, col, rr):
    _fond(c, [(0, (.62, .80, 1), 1), (.55, (1, .90, .72), 1), (1, (1, .78, .45), 1)])
    cx, cy = 540, 1350
    _glow(c, cx, cy, 1300, (1, .93, .6), .85, 0, 0)
    _rays(c, cx, cy, 30, (1, 1, .85), .35, rr.uniform(0, 1))
    for i in range(7):
        _nuage(c, rr.uniform(0, W), rr.uniform(200, 1100), rr.uniform(100, 190), (1, .9, .85), .55)
        _nuage(c, rr.uniform(0, W), rr.uniform(220, 1100), rr.uniform(60, 120), (1, 1, 1), .5)
    _glow(c, cx, cy, 330, (1, 1, .9), 1, .0, .45)
    _sparkles(c, rr, 30, (1, 1, .9), 7, 28)


def fond_sakura(c, col, rr):
    _fond(c, [(0, (1, .86, .92), 1), (.5, (.96, .80, 1), 1), (1, (1, .90, .88), 1)])
    for _ in range(18):
        _glow(c, rr.uniform(0, W), rr.uniform(0, H), rr.uniform(60, 200), rr.choice(((1, .7, .85), (1, .9, 1), (.85, .75, 1))), .42, 0, .3)
    c.set_source_rgba(.35, .20, .22, .9); c.set_line_width(26)                 # branche en fleurs
    c.move_to(-20, 120); c.curve_to(250, 190, 450, 60, 760, 170); c.stroke()
    c.set_line_width(14); c.move_to(300, 160); c.curve_to(360, 270, 330, 340, 380, 430); c.stroke()
    for _ in range(46):
        t = rr.random(); x = -20 + t * 800; y = 120 + 60 * math.sin(t * 3) + rr.uniform(-60, 90)
        for k in range(5):
            _petale(c, x + 22 * math.cos(k * 1.2566), y + 22 * math.sin(k * 1.2566), 20, k * 1.2566 + 1.57, (1, .72, .82), .95)
        _glow(c, x, y, 8, (1, .9, .4), 1, 1, 0)
    for _ in range(95):                                              # pétales qui tombent
        _petale(c, rr.uniform(0, W), rr.uniform(0, H), rr.uniform(11, 30), rr.uniform(0, 6.28), rr.choice(((1, .72, .84), (1, .82, .9), (.98, .62, .78))), rr.uniform(.5, .95))
    _sparkles(c, rr, 14, (1, 1, 1), 5, 15)


def fond_coucher(c, col, rr):
    _fond(c, [(0, (.28, .16, .45), 1), (.4, (.78, .30, .45), 1), (.7, (1, .55, .30), 1), (1, (1, .78, .40), 1)])
    cx, cy = 540, 1260
    _glow(c, cx, cy, 1100, (1, .75, .35), .75, 0, 0)
    _rays(c, cx, cy, 24, (1, .85, .5), .18, rr.uniform(0, 1))
    c.new_path(); c.arc(cx, cy, 190, 0, 6.2832); c.set_source(_lg(cy - 190, cy + 190, [(0, (1, .97, .75), 1), (1, (1, .62, .25), 1)])); c.fill()
    for k in range(3):
        _nuage(c, rr.uniform(100, 980), rr.uniform(800, 1250), rr.uniform(120, 220), (.95, .35, .35), .45)
    for i, (yb, amp, col2) in enumerate(((1400, 110, (.40, .20, .42)), (1580, 130, (.26, .12, .34)), (1760, 120, (.13, .06, .20)))):
        ph = rr.uniform(0, 6)
        c.new_path(); c.move_to(0, H)
        for x in range(0, W + 1, 12):
            c.line_to(x, yb - amp * (.5 * math.sin(x / 170 + ph) + .3 * math.sin(x / 69 + ph * 2) + .2))
        c.line_to(W, H); c.close_path(); c.set_source_rgb(*col2); c.fill()
    for _ in range(11):                                              # oiseaux
        x, y = rr.uniform(120, 960), rr.uniform(450, 1000)
        c.move_to(x - 18, y); c.curve_to(x - 9, y - 12, x - 2, y - 9, x, y); c.curve_to(x + 2, y - 9, x + 9, y - 12, x + 18, y)
        c.set_source_rgba(.12, .06, .18, .85); c.set_line_width(3.5); c.stroke()
    _sparkles(c, rr, 12, (1, .92, .7), 5, 17)


def fond_plumes(c, col, rr):
    _fond(c, [(0, (.78, .86, 1), 1), (.5, (1, .96, .86), 1), (1, (1, .90, .70), 1)])
    cx, cy = 540, 640
    _glow(c, cx, cy, 1200, (1, 1, .92), .95, 0, 0)
    _rays(c, cx, -80, 22, (1, 1, .9), .38, 1.1, True, 2800)
    for r, w in ((380, 5), (440, 3), (500, 2)):                      # auréole
        c.new_path(); c.arc(cx, cy + 330, r, 0, 6.2832); c.set_source_rgba(1, .9, .5, .85); c.set_line_width(w); c.stroke()
    for _ in range(70):
        _plume(c, rr.uniform(0, W), rr.uniform(0, H), rr.uniform(20, 58), rr.uniform(-1.2, 1.2), rr.uniform(.55, .95))
    for k in range(6):
        _nuage(c, k * 220, 1880, 150, (1, 1, 1), .9)
    _sparkles(c, rr, 26, (1, .95, .7), 6, 22)


def fond_etoiles(c, col, rr):
    _fond(c, [(0, (.03, .04, .15), 1), (.6, (.14, .12, .34), 1), (1, (.35, .22, .52), 1)])
    for _ in range(260):
        x, y, s = rr.uniform(0, W), rr.uniform(0, 1500), rr.uniform(.6, 2.6)
        _glow(c, x, y, s * 4, (.88, .92, 1), .6, 0, .1)
        if s > 2.1:
            _star4(c, x, y, s * 7, (1, 1, 1), .9)
    _glow(c, 800, 330, 380, (.8, .85, 1), .4, 0, .3)
    c.new_path(); c.arc(800, 330, 150, 0, 6.2832); c.set_source(_lg(180, 480, [(0, (1, .98, .88), 1), (1, (.9, .88, .75), 1)])); c.fill()
    for _ in range(3):                                               # étoiles filantes
        x, y = rr.uniform(120, 700), rr.uniform(120, 800)
        c.move_to(x, y); c.line_to(x + 260, y + 120); c.set_source(_lg(y, y + 120, [(0, (1, 1, 1), 0), (1, (1, 1, 1), 1)], x, x + 260)); c.set_line_width(5); c.stroke()
    for _ in range(18):                                              # lanternes qui montent
        x, y, s = rr.uniform(60, 1020), rr.uniform(400, 1850), rr.uniform(26, 62)
        _glow(c, x, y, s * 3, (1, .7, .25), .55, 0, .1)
        c.new_path(); c.rectangle(x - s / 2, y - s * .6, s, s * 1.2)
        c.set_source(_lg(y - s * .6, y + s * .6, [(0, (1, .9, .5), 1), (1, (1, .5, .15), 1)])); c.fill_preserve()
        c.set_source_rgba(.3, .1, .05, .8); c.set_line_width(2.4); c.stroke()
    c.set_source(_lg(1650, H, [(0, (.05, .05, .18), 0), (1, (.05, .05, .18), .9)])); c.rectangle(0, 1650, W, H - 1650); c.fill()


def fond_soleil(c, col, rr):
    cx, cy = 540, 960
    _fond(c, [(0, (1, .93, .45), 1), (1, (1, .70, .20), 1)])
    _rays(c, cx, cy, 44, (1, 1, .92), .75, rr.uniform(0, 1))
    _rays(c, cx, cy, 44, (1, .55, .15), .22, rr.uniform(0, 1) + .07)
    _glow(c, cx, cy, 820, (1, 1, .9), .95, 0, .25)
    _halftone(c, 16, 6.5, lambda x, y: max(0, (math.hypot(x - cx, y - cy) - 850) / 600), (.95, .45, .05), .6)
    for _ in range(70):                                              # confettis
        x, y = rr.uniform(0, W), rr.uniform(0, H)
        c.save(); c.translate(x, y); c.rotate(rr.uniform(0, 6.28)); c.rectangle(-9, -5, 18, 10)
        c.set_source_rgb(*rr.choice(((.95, .2, .3), (.2, .6, 1), (.3, .85, .4), (1, 1, 1), (.7, .3, .9)))); c.fill(); c.restore()
    _sparkles(c, rr, 20, (1, 1, 1), 8, 30)


def _tint(col, k):
    return tuple(q * (1 - k) + k for q in col)


FONDS = dict(pluie=fond_pluie, vitre=fond_vitre, vitesse=fond_vitesse, eclair=fond_eclair, aura=fond_aura, onde=fond_onde,
             explosion=fond_explosion, aube=fond_aube, sakura=fond_sakura, coucher=fond_coucher, plumes=fond_plumes,
             etoiles=fond_etoiles, soleil=fond_soleil)

# ce que chaque type de scène peut utiliser
SCENES = dict(
    chute=["pluie", "vitre", "vitesse", "eclair"],                   # un ami tombe : tristesse, choc
    defi=["aura", "eclair", "onde", "explosion"],                    # le héros se relève : puissance
    fin=["aube", "sakura", "coucher", "plumes", "soleil", "etoiles"],  # soulagement, hommage, victoire
)
