"""animaux.py — tetes d'animaux geometriques, style manga hachure (pycairo uniquement).

Style reconstruit d'apres les planches du lion visibles dans EP000.mp4 :
coloriage en hachures de la couleur du personnage, contre-hachures sombres (crinieres, ombres),
encrage noir epais, grands yeux ambres brillants, larmes bleu clair.

API :
    ANIMAUX[nom] -> dict(nom_en, forme, expressions, remarques)
    dessiner(nom, c, cx, cy, S, rot, expr, col, look=(0, 0), tear_len=0)

Unites : S=760 gros plan, S=560 plan moyen. La tete (sans accessoires) a un "rayon" d'environ 0.40*S ;
avec accessoires (criniere, oreilles, trompe...) l'encombrement total reste dans un carre d'environ 1.3*S.
tear_len : longueur des larmes en pixels a l'echelle S=760 (proportionnelle a S). Avec expr="crying"
et tear_len=0, une longueur par defaut (260) est utilisee ; avec une autre expression, tear_len>0 ajoute
des larmes (ex. "determined" + larmes, comme le lion d'origine).
"""
import math, colorsys
import cairo

EYE_K = 1.45
EXPRESSIONS = ["crying", "fierce", "sad_smile", "scared", "serene", "determined"]
PAPER = (1.0, 0.992, 0.965)
INK = (0.07, 0.06, 0.07)
WHITE = (1.0, 0.985, 0.95)
IRIS_IN, IRIS_OUT = (0.86, 0.64, 0.22), (0.42, 0.27, 0.07)
TEAR, TEAR_K = (0.70, 0.86, 0.98), (0.30, 0.55, 0.85)
MOUTH_IN, TONGUE = (0.36, 0.08, 0.10), (0.93, 0.50, 0.52)
BLUSH = (0.92, 0.30, 0.32)

# ---------------------------------------------------------------- couleurs
def mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))

class Pal:
    """Palette derivee de la couleur du personnage."""
    def __init__(self, col):
        self.col = col
        self.line = mix(col, (0, 0, 0), 0.12)             # traits de hachure
        self.base = mix(col, PAPER, 0.90)                 # papier teinte sous les hachures
        h, l, s = colorsys.rgb_to_hls(*col)
        hs = (h - 0.035) % 1.0                            # sombre legerement rechauffe (jaune->orange brun)
        self.dark = colorsys.hls_to_rgb(hs, max(0.16, l * 0.52), min(1, s * 0.95))
        self.darkbase = mix(self.dark, PAPER, 0.62)
        self.mid = colorsys.hls_to_rgb(hs, l * 0.78, s)   # contre-hachures moyennes
        self.light = mix(col, PAPER, 0.55)

# ---------------------------------------------------------------- chemins
def P_poly(pts):
    def f(c):
        c.move_to(*pts[0])
        for p in pts[1:]:
            c.line_to(*p)
        c.close_path()
    return f

def P_rpoly(pts, r):
    """Polygone a coins arrondis."""
    n = len(pts)
    def f(c):
        for i in range(n):
            p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
            d1 = math.hypot(p1[0] - p0[0], p1[1] - p0[1]); d2 = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            rr = min(r, d1 / 2.2, d2 / 2.2)
            a = (p1[0] + (p0[0] - p1[0]) * rr / d1, p1[1] + (p0[1] - p1[1]) * rr / d1)
            b = (p1[0] + (p2[0] - p1[0]) * rr / d2, p1[1] + (p2[1] - p1[1]) * rr / d2)
            if i == 0:
                c.move_to(*a)
            else:
                c.line_to(*a)
            c.curve_to(p1[0], p1[1], p1[0], p1[1], *b)
        c.close_path()
    return f

def P_ell(x, y, rx, ry=None, rot=0.0):
    ry = rx if ry is None else ry
    def f(c):
        c.save(); c.translate(x, y); c.rotate(rot); c.scale(rx, ry)
        c.new_sub_path(); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore(); c.close_path()
    return f

def P_multi(*fs):
    def f(c):
        for g in fs:
            g(c)
    return f

def P_curve(pts):
    """Chemin ferme lisse (Catmull-Rom) passant par les points."""
    n = len(pts)
    def f(c):
        c.move_to(*pts[0])
        for i in range(n):
            p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
            c.curve_to(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                       p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, *p2)
        c.close_path()
    return f

def P_open(pts):
    def f(c):
        c.move_to(*pts[0])
        for p in pts[1:]:
            c.line_to(*p)
    return f

def P_ocurve(pts):
    """Courbe ouverte lisse."""
    def f(c):
        c.move_to(*pts[0])
        n = len(pts)
        for i in range(n - 1):
            p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n - 1)]
            c.curve_to(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                       p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, *p2)
    return f

def star(cx, cy, r1, r2, n, a0=-math.pi / 2, jitter=None):
    pts = []
    for i in range(2 * n):
        r = r1 if i % 2 == 0 else r2
        if jitter and i % 2 == 0:
            r *= jitter[(i // 2) % len(jitter)]
        a = a0 + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def form_pts(forme, s=1.0, sx=1.0, sy=1.0, dy=0.0):
    """Points de la forme de base (tete). Triangle = pointe en bas (menton)."""
    if forme == "square":
        k = 0.86 * s
        return [(-k * sx, -k * sy + dy), (k * sx, -k * sy + dy), (k * sx, k * sy + dy), (-k * sx, k * sy + dy)]
    if forme == "diamond":
        k = 1.05 * s
        return [(0, -k * sy + dy), (k * sx, dy), (0, k * sy + dy), (-k * sx, dy)]
    if forme == "triangle":
        k = 1.12 * s
        return [(-k * sx, -0.62 * k * sy + dy), (k * sx, -0.62 * k * sy + dy), (0, 1.0 * k * sy + dy)]
    raise ValueError(forme)

def P_form(forme, s=1.0, sx=1.0, sy=1.0, dy=0.0, r=0.10):
    if forme == "circle":
        return P_ell(0, dy, 0.98 * s * sx, 0.98 * s * sy)
    return P_rpoly(form_pts(forme, s, sx, sy, dy), r * s)

# ---------------------------------------------------------------- outils de dessin
def lw(c, w):
    c.set_line_width(w)

def ink(c, path, w=0.034, col=INK):
    c.new_path(); path(c)
    c.set_source_rgb(*col); c.set_line_width(w)
    c.set_line_join(cairo.LINE_JOIN_ROUND); c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.stroke()

def fill(c, path, col, alpha=1.0):
    c.new_path(); path(c)
    c.set_source_rgba(*col, alpha); c.fill()

def _lines(c, angle, step, lw_, col, alpha=1.0, off=0.0):
    x1, y1, x2, y2 = c.clip_extents()
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    R = math.hypot(x2 - x1, y2 - y1) / 2 + step
    ca, sa = math.cos(angle), math.sin(angle)
    c.set_source_rgba(*col, alpha); c.set_line_width(lw_); c.set_line_cap(cairo.LINE_CAP_BUTT)
    k = -R + (off % step)
    while k <= R:
        px, py = cx - sa * k, cy + ca * k
        c.move_to(px - ca * R, py - sa * R); c.line_to(px + ca * R, py + sa * R)
        k += step
    c.stroke()

def hatch(c, path, line, base=None, angle=-math.pi / 4, step=0.036, w=0.0095, cross=None, cross_step=None):
    """Remplit `path` : fond `base` puis hachures paralleles `line` ; `cross` = 2e couleur croisee."""
    c.save(); c.new_path(); path(c); c.clip()
    if base is not None:
        c.set_source_rgb(*base); c.paint()
    _lines(c, angle, step, w, line)
    if cross is not None:
        _lines(c, angle + math.pi / 2, cross_step or step, w, cross)
    c.restore()

def shade(c, path, P, region, alpha=0.75, step=0.03):
    """Ombre en contre-hachures sombres limitee a `region` (chemin) a l'interieur de `path`."""
    c.save(); c.new_path(); path(c); c.clip(); c.new_path(); region(c); c.clip()
    _lines(c, math.pi / 4, step, 0.009, P.line, alpha)
    c.restore()

def part(c, path, P, kind="col", w=0.034, angle=-math.pi / 4):
    """Piece coloriee + encree. kind: col | dark | cross | light | white | darksolid."""
    if kind == "col":
        hatch(c, path, P.line, P.base, angle)
    elif kind == "cross":
        hatch(c, path, P.mid, mix(P.mid, PAPER, 0.72), angle, 0.034, 0.011, P.dark, 0.042)
    elif kind == "dark":
        hatch(c, path, P.dark, P.darkbase, angle, 0.026, 0.012, P.dark, 0.034)
    elif kind == "light":
        hatch(c, path, P.light, mix(P.base, PAPER, 0.5), angle, 0.032, 0.008)
    elif kind == "white":
        fill(c, path, WHITE)
    elif kind == "darksolid":
        fill(c, path, P.dark)
    if w:
        ink(c, path, w)

def clip_do(c, path, fn):
    c.save(); c.new_path(); path(c); c.clip(); fn(); c.restore()

# ---------------------------------------------------------------- visage / expressions
class Face:
    def __init__(self, c, P, expr, look, tear_len):
        self.c, self.P, self.expr, self.look = c, P, expr, look
        self.tear = tear_len / 304.0 if tear_len else (260 / 304.0 if expr == "crying" else 0.0)

    # ---- yeux
    def eyes(self, ex, ey, r, ry=None, brow=True, brow_dy=0.0, brow_len=1.25, tilt=0.0, iris=None,
             brow_w=1.0, lids=True):
        """Paire d'yeux en (+-ex, ey), rayon r. iris = couleur (par defaut ambre)."""
        r *= EYE_K
        ry = (ry * EYE_K) if ry else r * 1.12
        for side in (-1, 1):
            self._eye(side * ex, ey, r, ry, side, tilt, iris, lids)
        if brow:
            for side in (-1, 1):
                self._brow(side * ex, ey - ry * 1.30 + brow_dy, r * brow_len, side, brow_w)

    def _eye(self, x, y, rx, ry, side, tilt, iris, lids):
        c, e = self.c, self.expr
        if e == "sad_smile":   # yeux fermes souriants + goutte
            ink(c, P_ocurve([(x - rx * 0.8, y + ry * 0.2), (x, y - ry * 0.28), (x + rx * 0.8, y + ry * 0.2)]),
                0.032)
            if side == 1:
                self._drop(x + rx * 0.85, y + ry * 0.25, rx * 0.30)
            if self.tear:
                self._streams(x, y + ry * 0.3, rx * 0.7)
            return
        if e == "serene":    # yeux fermes paisibles + cils
            ink(c, P_ocurve([(x - rx * 0.85, y - ry * 0.05), (x, y + ry * 0.30), (x + rx * 0.85, y - ry * 0.05)]),
                0.034)
            ink(c, P_open([(x - side * rx * 0.85, y - ry * 0.05), (x - side * rx * 1.05, y - ry * 0.22)]), 0.022)
            if self.tear:
                self._streams(x, y + ry * 0.3, rx * 0.7)
            return
        sx = 0.88 if e == "scared" else 1.0
        eye = P_ell(x, y, rx * sx, ry * (1.08 if e in ("scared", "crying") else 1.0), tilt * side)
        c.save()
        # paupieres : on coupe le haut de l'oeil
        lid = None
        if lids and e == "fierce":
            lid = (0.42 * ry, 0.30)
        elif lids and e == "determined":
            lid = (0.22 * ry, 0.18)
        if lid:
            dy, ang = lid
            # ligne inclinee : plus basse vers l'interieur (cote nez)
            ax, bx = x - rx * 1.5, x + rx * 1.5
            ya = y - ry + dy * 2 + (ang * rx * 1.5 if side == 1 else -ang * rx * 1.5)
            yb = y - ry + dy * 2 + (-ang * rx * 1.5 if side == 1 else ang * rx * 1.5)
            cut = P_poly([(ax, ya), (bx, yb), (bx, y + ry * 2), (ax, y + ry * 2)])
            c.new_path(); cut(c); c.clip()
        fill(c, eye, WHITE)
        clip_do(c, eye, lambda: self._iris(x, y, rx, ry, iris))
        if e == "crying":
            clip_do(c, eye, lambda: self._pool(x, y, rx, ry))
        ink(c, eye, 0.030)
        c.restore()
        if lid:
            ink(c, P_open([(ax + rx * 0.45, ya + (yb - ya) * 0.15), (bx - rx * 0.45, yb - (yb - ya) * 0.15)]), 0.05)
        if self.tear:
            self._streams(x, y + ry * 0.80, rx * 0.80)

    def _iris(self, x, y, rx, ry, iris):
        c, e = self.c, self.expr
        lx, ly = self.look
        k = {"scared": 0.36, "crying": 0.78, "fierce": 0.62, "determined": 0.64}.get(e, 0.66)
        ir = min(rx, ry) * k
        ix, iy = x + lx * rx * 0.28, y + ly * ry * 0.22 + (0.05 * ry if e != "scared" else 0)
        iris = self.P.col if iris is None else iris
        cin, cout = mix(iris, PAPER, 0.35), mix(iris, (0, 0, 0), 0.40)
        g = cairo.RadialGradient(ix, iy + ir * 0.2, ir * 0.1, ix, iy, ir)
        g.add_color_stop_rgb(0, *cin); g.add_color_stop_rgb(1, *cout)
        c.new_path(); c.arc(ix, iy, ir, 0, 2 * math.pi); c.set_source(g); c.fill_preserve()
        c.set_source_rgb(*INK); c.set_line_width(0.012); c.stroke()
        pr = ir * (0.22 if e == "scared" else 0.30 if e == "fierce" else 0.36)
        c.new_path(); c.set_source_rgba(*INK, 0.55); c.set_line_width(0.006)
        for kk in (1.45, 1.9):
            c.arc(ix, iy, pr * kk, 0, 2 * math.pi); c.stroke()
        c.arc(ix, iy, pr, 0, 2 * math.pi); c.set_source_rgb(*INK); c.fill()
        # reflets
        hl = 0.30 if e == "crying" else 0.24
        c.arc(ix + ir * 0.35, iy - ir * 0.38, ir * hl, 0, 2 * math.pi); c.set_source_rgb(1, 1, 1); c.fill()
        c.arc(ix - ir * 0.32, iy + ir * 0.38, ir * hl * 0.45, 0, 2 * math.pi); c.fill()
        if e == "crying":
            c.arc(ix - ir * 0.45, iy - ir * 0.05, ir * 0.12, 0, 2 * math.pi); c.fill()

    def _pool(self, x, y, rx, ry):
        c = self.c
        top = y + ry * 0.38
        pts = [(x - rx * 1.2, top)]
        for i in range(9):
            t = i / 8
            pts.append((x - rx * 1.2 + t * rx * 2.4, top + math.sin(t * math.pi * 3) * ry * 0.05))
        pts += [(x + rx * 1.2, y + ry * 1.3), (x - rx * 1.2, y + ry * 1.3)]
        fill(c, P_poly(pts), TEAR, 0.85)
        ink(c, P_open(pts[1:10]), 0.012, TEAR_K)

    def _streams(self, x, y, w):
        """Une larme large et ondulee par oeil (comme les planches d'origine)."""
        c, L = self.c, self.tear
        n = 12
        left, right = [], []
        for i in range(n + 1):
            t = i / n
            ww = w * (0.30 + 0.06 * t)
            off = math.sin(t * math.pi * 2.0 + x * 4) * w * 0.14
            left.append((x + off - ww, y + t * L)); right.append((x + off + ww, y + t * L))
        p = P_poly(left + right[::-1])
        fill(c, p, TEAR, 0.95); ink(c, p, 0.016, TEAR_K)
        ink(c, P_ocurve([(px + w * 0.12, py) for (px, py) in left[1:-1]]), 0.012, (1, 1, 1))

    def _drop(self, x, y, r):
        c = self.c
        p = P_curve([(x, y - r * 1.6), (x + r * 0.75, y + r * 0.1), (x, y + r), (x - r * 0.75, y + r * 0.1)])
        fill(c, p, TEAR); ink(c, p, 0.014, TEAR_K)
        c.arc(x - r * 0.2, y + r * 0.1, r * 0.22, 0, 2 * math.pi); c.set_source_rgb(1, 1, 1); c.fill()

    def _brow(self, x, y, L, side, wk):
        e = self.expr
        # angle positif = cote interieur plus bas
        a = {"fierce": 0.42, "determined": 0.26, "crying": -0.42, "scared": -0.50,
             "sad_smile": -0.30, "serene": -0.06}[e]
        dy = {"fierce": 0.04, "determined": 0.02, "scared": -0.10, "crying": -0.03}.get(e, 0) * L * 3
        inner = -side
        cx_, cy_ = x, y + dy
        ca, sa = math.cos(a), math.sin(a)
        # point interieur / exterieur
        xi, yi = cx_ + inner * L / 2 * ca, cy_ + L / 2 * sa
        xo, yo = cx_ - inner * L / 2 * ca, cy_ - L / 2 * sa
        th = 0.09 * wk * (1.25 if e == "fierce" else 1.0)
        nx, ny = 0, th
        p = P_rpoly([(xo, yo - th * 0.25), (xi, yi - th * 0.5), (xi, yi + th * 0.5), (xo, yo + th * 0.25)], 0.02)
        fill(self.c, p, INK)

    # ---- joues
    def blush(self, x, y, r):
        if self.expr not in ("serene", "sad_smile", "crying"):
            return
        c = self.c
        for side in (-1, 1):
            for i in range(4):
                xx = side * x + (i - 1.5) * r * 0.45
                ink(c, P_open([(xx + r * 0.18, y - r * 0.28), (xx - r * 0.18, y + r * 0.28)]), 0.016, BLUSH)

    def sweat(self, x, y, r):
        if self.expr in ("scared", "determined"):
            self._drop(x, y, r)

    # ---- bouche
    def mouth(self, x, y, w, kind="cat", open_k=1.0):
        """Bouche centree en (x, y) de largeur w. kind: cat | wide | small."""
        c, e = self.c, self.expr
        if e == "serene":
            if kind == "cat":
                self._w(x, y, w * 0.5, w * 0.16)
            else:
                ink(c, P_ocurve([(x - w * 0.4, y), (x, y + w * 0.16), (x + w * 0.4, y)]), 0.03)
        elif e == "sad_smile":
            if kind == "cat":
                self._w(x, y, w * 0.42, w * 0.12)
            else:
                ink(c, P_ocurve([(x - w * 0.32, y), (x, y + w * 0.11), (x + w * 0.32, y)]), 0.03)
            ink(c, P_open([(x - w * 0.5, y - w * 0.02), (x - w * 0.42, y + w * 0.04)]), 0.02)
            ink(c, P_open([(x + w * 0.5, y - w * 0.02), (x + w * 0.42, y + w * 0.04)]), 0.02)
        elif e == "crying":     # bouche ouverte qui tremble
            h = w * 0.55 * open_k
            p = P_curve([(x - w * 0.42, y + h * 0.15), (x - w * 0.2, y - h * 0.18), (x, y - h * 0.05),
                         (x + w * 0.2, y - h * 0.18), (x + w * 0.42, y + h * 0.15), (x + w * 0.22, y + h * 0.75),
                         (x, y + h * 0.85), (x - w * 0.22, y + h * 0.75)])
            self._open(p, x, y + h * 0.75, w * 0.26)
        elif e == "fierce":     # rugissement avec crocs
            h = w * 0.62 * open_k
            p = P_curve([(x - w * 0.5, y - h * 0.10), (x, y + h * 0.02), (x + w * 0.5, y - h * 0.10),
                         (x + w * 0.30, y + h * 0.75), (x, y + h * 0.95), (x - w * 0.30, y + h * 0.75)])
            def fangs():
                for s in (-1, 1):
                    fill(c, P_poly([(x + s * w * 0.40, y - h * 0.2), (x + s * w * 0.18, y - h * 0.1),
                                    (x + s * w * 0.30, y + h * 0.42)]), WHITE)
                    ink(c, P_poly([(x + s * w * 0.40, y - h * 0.2), (x + s * w * 0.18, y - h * 0.1),
                                   (x + s * w * 0.30, y + h * 0.42)]), 0.014)
            self._open(p, x, y + h * 0.8, w * 0.26, fangs)
        elif e == "scared":     # bouche ondulee serree
            h = w * 0.30
            pts = []
            for i in range(7):
                t = i / 6
                pts.append((x - w * 0.38 + t * w * 0.76, y + (h * 0.18 if i % 2 else -h * 0.18)))
            p = P_rpoly([(x - w * 0.42, y - h * 0.55), (x + w * 0.42, y - h * 0.55), (x + w * 0.42, y + h * 0.55),
                         (x - w * 0.42, y + h * 0.55)], h * 0.4)
            fill(c, p, WHITE); ink(c, P_open(pts), 0.016); ink(c, p, 0.028)
        elif e == "determined":  # dents serrees
            h = w * 0.26
            p = P_rpoly([(x - w * 0.36, y - h * 0.5), (x + w * 0.36, y - h * 0.4), (x + w * 0.36, y + h * 0.5),
                         (x - w * 0.36, y + h * 0.5)], h * 0.35)
            fill(c, p, WHITE)
            for i in range(1, 4):
                xx = x - w * 0.36 + i * w * 0.18
                ink(c, P_open([(xx, y - h * 0.48), (xx, y + h * 0.48)]), 0.012)
            ink(c, P_open([(x - w * 0.36, y), (x + w * 0.36, y)]), 0.012)
            ink(c, p, 0.028)

    def _w(self, x, y, w, h):
        ink(self.c, P_ocurve([(x - w, y - h * 0.3), (x - w * 0.5, y + h), (x, y)]), 0.028)
        ink(self.c, P_ocurve([(x, y), (x + w * 0.5, y + h), (x + w, y - h * 0.3)]), 0.028)

    def _open(self, p, tx, ty, tr, extra=None):
        c = self.c
        fill(c, p, MOUTH_IN)
        def tongue():
            fill(c, P_ell(tx, ty, tr, tr * 0.6), TONGUE)
            if extra:
                extra()
        clip_do(c, p, tongue)
        ink(c, p, 0.030)

    # ---- bec
    def beak(self, x, y, w, h, col=(0.96, 0.62, 0.18), down=True):
        """Bec centre en (x, y) (racine), largeur w, longueur h (vers le bas si down)."""
        c, e = self.c, self.expr
        sg = 1 if down else -1
        op = {"crying": 0.55, "fierce": 0.65, "scared": 0.30}.get(e, 0.0)
        bc = mix(col, PAPER, 0.15)
        up = P_rpoly([(x - w / 2, y), (x + w / 2, y), (x, y + sg * h)], w * 0.08)
        if op:
            lo = P_rpoly([(x - w * 0.38, y + sg * h * 0.25), (x + w * 0.38, y + sg * h * 0.25),
                          (x, y + sg * h * (0.75 + op))], w * 0.08)
            fill(c, P_poly([(x - w * 0.4, y + sg * h * 0.2), (x + w * 0.4, y + sg * h * 0.2),
                            (x, y + sg * h * (0.7 + op))]), MOUTH_IN)
            hatch(c, lo, mix(bc, (0, 0, 0), 0.25), bc, 0.6); ink(c, lo, 0.03)
        hatch(c, up, mix(bc, (0, 0, 0), 0.25), bc, 0.6); ink(c, up, 0.032)
        if e == "serene" or e == "sad_smile":
            pass

# ---------------------------------------------------------------- briques communes
def nose_tri(c, x, y, w, pink=False):
    p = P_rpoly([(x - w / 2, y - w * 0.3), (x + w / 2, y - w * 0.3), (x, y + w * 0.35)], w * 0.12)
    if pink:
        fill(c, p, (0.93, 0.48, 0.52)); ink(c, p, 0.014); return
    fill(c, p, INK)
    c.arc(x - w * 0.15, y - w * 0.12, w * 0.08, 0, 2 * math.pi); c.set_source_rgb(1, 1, 1); c.fill()

def nose_oval(c, x, y, rx, ry=None):
    ry = ry or rx * 0.65
    fill(c, P_ell(x, y, rx, ry), INK)
    c.arc(x - rx * 0.35, y - ry * 0.35, rx * 0.22, 0, 2 * math.pi); c.set_source_rgb(1, 1, 1); c.fill()

def muzzle(c, P, x, y, rx, ry, kind="white"):
    p = P_ell(x, y, rx, ry)
    if kind == "white":
        fill(c, p, WHITE)
    else:
        part(c, p, P, kind, 0)
    ink(c, p, 0.030)
    return p

def whiskers(c, x, y, L, n=3):
    for s in (-1, 1):
        for i in range(n):
            a = (i - (n - 1) / 2) * 0.22
            ink(c, P_open([(x + s * L * 0.25, y + i * 0.02), (x + s * (L * 0.25 + L * math.cos(a)), y + L * math.sin(a) * 0.7 + i * 0.02)]), 0.012)

def head_shadow(c, P, head):
    shade(c, head, P, P_ell(0.75, 0.75, 0.95, 0.75, 0.5), 0.55)

def ear(c, P, x, y, r, inner=True, kind="col", ry=None):
    ry = ry or r
    p = P_ell(x, y, r, ry)
    part(c, p, P, kind)
    if inner:
        q = P_ell(x, y + ry * 0.08, r * 0.58, ry * 0.58)
        part(c, q, P, "light", 0.022)

def pointy_ear(c, P, x, y, w, h, tilt, inner=True, kind="col"):
    ca, sa = math.cos(tilt), math.sin(tilt)
    def T(px, py):
        return (x + px * ca - py * sa, y + px * sa + py * ca)
    p = P_rpoly([T(-w / 2, 0), T(0, -h), T(w / 2, 0)], 0.05)
    part(c, p, P, kind)
    if inner:
        q = P_rpoly([T(-w * 0.27, -h * 0.08), T(0, -h * 0.72), T(w * 0.27, -h * 0.08)], 0.03)
        part(c, q, P, "light", 0.02)

def spots(c, head, pts, P, kind="dot"):
    def f():
        for (x, y, r) in pts:
            if kind == "dot":
                p = P_ell(x, y, r, r * 0.85)
                fill(c, p, P.dark)
            elif kind == "rosette":
                for k in range(5):
                    a = k * 2 * math.pi / 5 + x * 3
                    fill(c, P_ell(x + r * math.cos(a), y + r * math.sin(a), r * 0.42, r * 0.30, a + 1.57), P.dark)
            elif kind == "jaguar":
                for k in range(5):
                    a = k * 2 * math.pi / 5 + y * 3
                    fill(c, P_ell(x + r * math.cos(a), y + r * math.sin(a), r * 0.42, r * 0.28, a + 1.57), P.dark)
                fill(c, P_ell(x, y, r * 0.22), P.dark)
    clip_do(c, head, f)

def stripes(c, head, P, lines, w=0.09):
    def f():
        for (x0, y0, x1, y1, x2, y2) in lines:
            ink(c, P_ocurve([(x0, y0), (x1, y1), (x2, y2)]), w, P.dark)
    clip_do(c, head, f)

# ---------------------------------------------------------------- animaux
def a_lion(c, P, F, female=False):
    head = P_form("diamond", 0.95)
    if not female:
        mane = P_poly(star(0, 0.05, 1.62, 1.18, 14, jitter=[1, 0.93, 1.04, 0.96]))
        part(c, mane, P, "cross", 0.05)
        for s in (-1, 1):
            ear(c, P, s * 0.50, -0.62, 0.22)
    else:
        for s in (-1, 1):
            ear(c, P, s * 0.55, -0.55, 0.24)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    m = muzzle(c, P, 0, 0.48, 0.34, 0.27)
    nose_tri(c, 0, 0.32, 0.18)
    F.eyes(0.36, -0.02, 0.17)
    F.blush(0.52, 0.26, 0.12)
    F.mouth(0, 0.55, 0.36)
    F.sweat(0.62, -0.4, 0.08)

def a_lionne(c, P, F):
    a_lion(c, P, F, female=True)

def a_tigre(c, P, F):
    head = P_form("diamond", 1.0, sx=1.08)
    for s in (-1, 1):
        ear(c, P, s * 0.58, -0.62, 0.24)
    for sd in (-1, 1):   # touffes de joues
        tuft = P_poly([(sd * 0.70, -0.32), (sd * 1.32, -0.05), (sd * 1.05, 0.05), (sd * 1.30, 0.22),
                       (sd * 0.95, 0.30), (sd * 1.12, 0.48), (sd * 0.55, 0.45)])
        part(c, tuft, P, "col", 0.04)
    part(c, head, P, "col", 0.05)
    stripes(c, head, P, [(-0.1, -0.95, -0.05, -0.75, -0.1, -0.55), (0.1, -0.95, 0.05, -0.75, 0.1, -0.55),
                         (-1.1, -0.05, -0.85, -0.02, -0.68, 0.06), (1.1, -0.05, 0.85, -0.02, 0.68, 0.06),
                         (-1.0, 0.25, -0.8, 0.22, -0.62, 0.28), (1.0, 0.25, 0.8, 0.22, 0.62, 0.28),
                         (-0.6, -0.55, -0.45, -0.45, -0.38, -0.32), (0.6, -0.55, 0.45, -0.45, 0.38, -0.32)], 0.07)
    head_shadow(c, P, head)
    muzzle(c, P, 0, 0.50, 0.36, 0.27)
    nose_tri(c, 0, 0.34, 0.19)
    F.eyes(0.38, -0.02, 0.17)
    F.blush(0.55, 0.26, 0.12)
    F.mouth(0, 0.57, 0.38)
    F.sweat(0.66, -0.42, 0.08)

def _bigcat(c, P, F, pattern):
    head = P_form("diamond", 1.0, sx=1.0, sy=1.02)
    for s in (-1, 1):
        ear(c, P, s * 0.52, -0.62, 0.21)
    part(c, head, P, "col", 0.05)
    if pattern == "cheetah":
        spots(c, head, [(-0.35, -0.55, 0.05), (0.32, -0.6, 0.05), (0, -0.75, 0.05), (-0.65, 0.05, 0.05),
                        (0.65, 0.0, 0.05), (-0.55, -0.25, 0.04), (0.55, -0.28, 0.04), (0.15, -0.45, 0.04),
                        (-0.15, -0.42, 0.04), (-0.78, 0.2, 0.04), (0.78, 0.18, 0.04)], P, "dot")
    elif pattern == "leopard":
        spots(c, head, [(-0.3, -0.6, 0.09), (0.3, -0.62, 0.09), (0, -0.82, 0.08), (-0.7, 0.05, 0.08),
                        (0.7, 0.05, 0.08), (-0.6, -0.28, 0.07), (0.6, -0.3, 0.07)], P, "rosette")
    else:
        spots(c, head, [(-0.28, -0.6, 0.11), (0.3, -0.62, 0.11), (-0.7, 0.04, 0.10), (0.7, 0.04, 0.10),
                        (0, -0.86, 0.08), (-0.58, -0.3, 0.08), (0.58, -0.32, 0.08)], P, "jaguar")
    head_shadow(c, P, head)
    muzzle(c, P, 0, 0.50, 0.33, 0.26)
    nose_tri(c, 0, 0.35, 0.18)
    if pattern == "cheetah":   # traits de larmes noirs du guepard
        for s in (-1, 1):
            ink(c, P_ocurve([(s * 0.25, 0.10), (s * 0.30, 0.28), (s * 0.33, 0.45)]), 0.04, P.dark)
    F.eyes(0.36, -0.03, 0.165)
    F.blush(0.52, 0.25, 0.11)
    F.mouth(0, 0.56, 0.34)
    F.sweat(0.62, -0.42, 0.08)

def a_guepard(c, P, F): _bigcat(c, P, F, "cheetah")
def a_leopard(c, P, F): _bigcat(c, P, F, "leopard")
def a_jaguar(c, P, F): _bigcat(c, P, F, "jaguar")

def a_chat(c, P, F):
    head = P_form("circle", 1.0, sx=1.06, sy=0.94, dy=0.05)
    for s in (-1, 1):
        pointy_ear(c, P, s * 0.62, -0.50, 0.55, 0.62, s * 0.38)
    part(c, head, P, "col", 0.05)
    stripes(c, head, P, [(-0.15, -0.9, -0.12, -0.75, -0.1, -0.62), (0.15, -0.9, 0.12, -0.75, 0.1, -0.62),
                         (0, -0.95, 0, -0.8, 0, -0.66)], 0.05)
    head_shadow(c, P, head)
    F.eyes(0.40, 0.0, 0.19)
    nose_tri(c, 0, 0.30, 0.13, pink=True)
    whiskers(c, 0, 0.42, 0.55)
    F.blush(0.58, 0.30, 0.11)
    F.mouth(0, 0.46, 0.32)
    F.sweat(0.66, -0.38, 0.08)

def a_souris(c, P, F):
    head = P_form("triangle", 0.92, sy=0.95, dy=0.05)
    for s in (-1, 1):
        ear(c, P, s * 0.78, -0.62, 0.42)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    F.eyes(0.32, -0.18, 0.16)
    nose_oval(c, 0, 0.72, 0.09)
    whiskers(c, 0, 0.66, 0.45)
    F.blush(0.45, 0.12, 0.09)
    F.mouth(0, 0.42, 0.26, "small")
    F.sweat(0.6, -0.5, 0.07)

def a_panda(c, P, F):
    head = P_form("square", 1.0, sx=1.05, dy=0.04, r=0.30)
    for s in (-1, 1):
        ear(c, P, s * 0.72, -0.78, 0.26, inner=False, kind="dark")
    part(c, head, P, "col", 0.05)
    for s in (-1, 1):
        part(c, P_ell(s * 0.40, 0.0, 0.27, 0.33, s * -0.5), P, "dark", 0.025)
    head_shadow(c, P, head)
    muzzle(c, P, 0, 0.48, 0.32, 0.24)
    nose_oval(c, 0, 0.36, 0.10)
    F.eyes(0.40, 0.0, 0.16)
    F.blush(0.62, 0.32, 0.10)
    F.mouth(0, 0.54, 0.30)
    F.sweat(0.7, -0.45, 0.08)


def forelock(c, P, x, y, sc=1.0):
    """Meche de poils (3 pointes) sur le front."""
    p = P_curve([(x - 0.24 * sc, y + 0.10 * sc), (x - 0.20 * sc, y - 0.18 * sc), (x - 0.12 * sc, y - 0.02 * sc),
                 (x - 0.02 * sc, y - 0.30 * sc), (x + 0.08 * sc, y - 0.04 * sc), (x + 0.20 * sc, y - 0.22 * sc),
                 (x + 0.24 * sc, y + 0.10 * sc), (x, y + 0.20 * sc)])
    part(c, p, P, "dark", 0.03)

# ================================================================ CARRES
def a_renard(c, P, F):
    head = P_form("square", 0.95, r=0.10)
    for s in (-1, 1):
        pointy_ear(c, P, s * 0.55, -0.78, 0.62, 0.70, s * 0.12, kind="cross")
    part(c, head, P, "col", 0.05)
    cheeks = P_poly([(-0.82, 0.10), (-0.55, 0.32), (-0.35, 0.22), (0, 0.42), (0.35, 0.22), (0.55, 0.32), (0.82, 0.10),
                     (0.82, 0.82), (-0.82, 0.82)])
    clip_do(c, head, lambda: (fill(c, cheeks, WHITE), ink(c, P_open([(-0.9, 0.10 * 0.9), (-0.55, 0.32), (-0.35, 0.22),
            (0, 0.42), (0.35, 0.22), (0.55, 0.32), (0.9, 0.09)]), 0.025)))
    head_shadow(c, P, head)
    ink(c, head, 0.05)
    F.eyes(0.40, -0.18, 0.15)
    nose_tri(c, 0, 0.58, 0.13)
    F.blush(0.58, 0.10, 0.10)
    F.mouth(0, 0.70, 0.26, "small")
    F.sweat(0.66, -0.55, 0.08)

def a_koala(c, P, F):
    head = P_form("square", 0.95, sx=1.02, r=0.34)
    for s in (-1, 1):
        e = P_poly(star(s * 0.88, -0.52, 0.50, 0.44, 14))
        part(c, e, P, "col", 0.04)
        part(c, P_ell(s * 0.88, -0.50, 0.26, 0.24), P, "light", 0.02)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    F.eyes(0.44, -0.18, 0.13)
    nose = P_rpoly([(-0.16, 0.0), (0.16, 0.0), (0.20, 0.30), (0.10, 0.46), (-0.10, 0.46), (-0.20, 0.30)], 0.12)
    fill(c, nose, INK)
    c.arc(-0.06, 0.12, 0.04, 0, 2 * math.pi); c.set_source_rgb(1, 1, 1); c.fill()
    F.blush(0.55, 0.22, 0.10)
    F.mouth(0, 0.62, 0.30, "small")
    F.sweat(0.66, -0.6, 0.08)

def a_ours(c, P, F):
    head = P_form("square", 0.96, r=0.30)
    for s in (-1, 1):
        ear(c, P, s * 0.66, -0.78, 0.25)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    muzzle(c, P, 0, 0.42, 0.40, 0.30, "light")
    nose_oval(c, 0, 0.28, 0.13)
    ink(c, P_open([(0, 0.34), (0, 0.46)]), 0.022)
    F.eyes(0.40, -0.14, 0.14)
    F.blush(0.60, 0.20, 0.10)
    F.mouth(0, 0.54, 0.34)
    F.sweat(0.66, -0.55, 0.08)

def a_chien(c, P, F):
    head = P_form("square", 0.92, r=0.28)
    part(c, head, P, "col", 0.05)
    clip_do(c, head, lambda: fill(c, P_ell(0.42, -0.32, 0.36, 0.30, 0.3), P.dark, 0.55))
    head_shadow(c, P, head)
    ink(c, head, 0.05)
    for s in (-1, 1):   # oreilles tombantes
        e = P_curve([(s * 0.55, -0.80), (s * 1.05, -0.70), (s * 1.18, -0.10), (s * 1.08, 0.38), (s * 0.85, 0.30),
                     (s * 0.80, -0.30)])
        part(c, e, P, "cross", 0.04)
    muzzle(c, P, 0, 0.44, 0.40, 0.30)
    nose_oval(c, 0, 0.28, 0.14)
    F.eyes(0.38, -0.14, 0.145)
    F.blush(0.60, 0.22, 0.10)
    F.mouth(0, 0.52, 0.32)
    if F.expr == "serene":
        t = P_rpoly([(-0.08, 0.60), (0.08, 0.60), (0.08, 0.78), (-0.08, 0.78)], 0.07)
        fill(c, t, TONGUE); ink(c, t, 0.018)
    F.sweat(0.64, -0.55, 0.08)

def a_panda2(c, P, F):
    a_panda(c, P, F)

def a_elephant(c, P, F):
    head = P_form("square", 0.86, r=0.30)
    for s in (-1, 1):
        e = P_curve([(s * 0.55, -0.70), (s * 1.30, -0.80), (s * 1.50, -0.10), (s * 1.30, 0.50), (s * 0.70, 0.40)])
        part(c, e, P, "col", 0.045)
        part(c, P_curve([(s * 0.75, -0.55), (s * 1.22, -0.62), (s * 1.34, -0.10), (s * 1.20, 0.32), (s * 0.80, 0.25)]),
             P, "light", 0.02)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    for s in (-1, 1):   # defenses
        t = P_curve([(s * 0.30, 0.55), (s * 0.40, 0.80), (s * 0.48, 0.95), (s * 0.36, 0.86), (s * 0.20, 0.66)])
        fill(c, t, WHITE); ink(c, t, 0.022)
    F.mouth(0, 0.62, 0.40, "small")
    trunk = P_curve([(-0.17, 0.05), (0.17, 0.05), (0.15, 0.55), (0.14, 0.95), (0.30, 1.12), (0.36, 1.25), (0.18, 1.30),
                     (0.0, 1.18), (-0.12, 0.95), (-0.15, 0.55)])
    part(c, trunk, P, "col", 0.04)
    for y in (0.40, 0.55, 0.70, 0.85):
        ink(c, P_ocurve([(-0.10, y), (0, y + 0.03), (0.10, y)]), 0.014)
    F.eyes(0.40, -0.18, 0.13)
    F.blush(0.55, 0.18, 0.10)
    F.sweat(0.62, -0.6, 0.08)

def a_gorille(c, P, F):
    head = P_rpoly([(-0.86, -0.55), (-0.35, -0.95), (0, -1.08), (0.35, -0.95), (0.86, -0.55), (0.86, 0.86),
                    (-0.86, 0.86)], 0.18)
    for s in (-1, 1):
        ear(c, P, s * 0.92, 0.0, 0.17, kind="dark")
    part(c, head, P, "dark", 0.05)
    mask = P_curve([(0, -0.40), (0.45, -0.52), (0.72, -0.25), (0.62, 0.18), (0.62, 0.62), (0.30, 0.82),
                    (-0.30, 0.82), (-0.62, 0.62), (-0.62, 0.18), (-0.72, -0.25), (-0.45, -0.52)])
    part(c, mask, P, "col", 0.035)
    shade(c, mask, P, P_ell(0.6, 0.6, 0.6, 0.5), 0.5)
    ink(c, P_ocurve([(-0.62, -0.40), (-0.30, -0.50), (0, -0.38), (0.30, -0.50), (0.62, -0.40)]), 0.05)  # arcade
    for s in (-1, 1):
        fill(c, P_ell(s * 0.10, 0.25, 0.08, 0.06, s * 0.5), INK)
    ink(c, P_ocurve([(-0.20, 0.12), (0, 0.04), (0.20, 0.12)]), 0.022)
    F.eyes(0.34, -0.18, 0.13, brow_dy=0.06)
    F.blush(0.48, 0.18, 0.10)
    F.mouth(0, 0.52, 0.40)
    F.sweat(0.62, -0.55, 0.08)

def a_hippopotame(c, P, F):
    head = P_form("square", 0.92, sx=1.08, r=0.32)
    for s in (-1, 1):
        ear(c, P, s * 0.62, -0.86, 0.17)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    mz = muzzle(c, P, 0, 0.42, 0.88, 0.46, "light")
    for s in (-1, 1):
        fill(c, P_ell(s * 0.28, 0.18, 0.09, 0.06, s * 0.4), INK)
    F.eyes(0.42, -0.40, 0.125, brow_dy=0.04)
    F.blush(0.66, -0.12, 0.10)
    F.mouth(0, 0.52, 0.55, "wide")
    F.sweat(0.70, -0.7, 0.08)

def a_cochon(c, P, F):
    head = P_form("square", 0.92, r=0.32)
    for s in (-1, 1):
        pointy_ear(c, P, s * 0.62, -0.72, 0.48, 0.40, s * 0.55)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    sn = P_ell(0, 0.28, 0.30, 0.21)
    part(c, sn, P, "light", 0.032)
    for s in (-1, 1):
        fill(c, P_ell(s * 0.10, 0.28, 0.05, 0.08), INK)
    F.eyes(0.40, -0.20, 0.14)
    F.blush(0.58, 0.18, 0.10)
    F.mouth(0, 0.62, 0.30, "small")
    F.sweat(0.66, -0.58, 0.08)

def a_rhinoceros(c, P, F):
    head = P_form("square", 0.92, r=0.28)
    for s in (-1, 1):
        pointy_ear(c, P, s * 0.66, -0.80, 0.30, 0.34, s * 0.35)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    muzzle(c, P, 0, 0.55, 0.62, 0.32, "light")
    for s in (-1, 1):
        fill(c, P_ell(s * 0.22, 0.45, 0.06, 0.04, s * 0.4), INK)
    F.mouth(0, 0.66, 0.36, "wide")
    horn = P_rpoly([(-0.16, 0.36), (0.16, 0.36), (0.05, -0.12), (0, -0.18)], 0.04)
    fill(c, horn, WHITE); hatch(c, horn, mix(P.light, INK, 0.2), None, 0.5, 0.05, 0.006); ink(c, horn, 0.03)
    small = P_rpoly([(-0.08, -0.22), (0.08, -0.22), (0, -0.42)], 0.03)
    fill(c, small, WHITE); ink(c, small, 0.025)
    F.eyes(0.42, -0.08, 0.12)
    F.blush(0.60, 0.22, 0.10)
    F.sweat(0.66, -0.58, 0.08)

def a_vache(c, P, F):
    head = P_form("square", 0.90, r=0.26)
    for s in (-1, 1):
        horn = P_curve([(s * 0.40, -0.70), (s * 0.62, -1.05), (s * 0.80, -1.18), (s * 0.68, -0.98), (s * 0.58, -0.72)])
        fill(c, horn, WHITE); ink(c, horn, 0.025)
        e = P_ell(s * 1.00, -0.42, 0.30, 0.15, s * 0.3)
        part(c, e, P, "col", 0.035)
    part(c, head, P, "col", 0.05)
    clip_do(c, head, lambda: fill(c, P_curve([(-0.9, -0.9), (-0.25, -0.85), (-0.35, -0.45), (-0.70, -0.20),
                                              (-0.95, -0.40)]), P.dark, 0.6))
    head_shadow(c, P, head)
    ink(c, head, 0.05)
    muzzle(c, P, 0, 0.50, 0.58, 0.32, "light")
    for s in (-1, 1):
        fill(c, P_ell(s * 0.22, 0.42, 0.07, 0.05, s * 0.4), INK)
    F.eyes(0.40, -0.18, 0.13)
    F.blush(0.62, 0.15, 0.10)
    F.mouth(0, 0.64, 0.34, "wide")
    F.sweat(0.66, -0.58, 0.08)

# ================================================================ RONDS
def a_baleine(c, P, F):
    if F.expr in ("serene", "sad_smile", "determined"):   # jet d'eau
        for k, (dx, dy, r) in enumerate([(0, -1.05, 0.10), (-0.18, -1.25, 0.08), (0.18, -1.25, 0.08), (0, -1.38, 0.07)]):
            p = P_ell(dx, dy, r, r * 1.2)
            fill(c, p, TEAR); ink(c, p, 0.015, TEAR_K)
    for s in (-1, 1):   # nageoires laterales
        fin = P_curve([(s * 0.95, 0.20), (s * 1.38, 0.38), (s * 1.30, 0.62), (s * 0.90, 0.48)])
        part(c, fin, P, "col", 0.035)
    head = P_ell(0, 0.05, 1.12, 0.88)
    part(c, head, P, "col", 0.05)
    belly = P_ell(0, 0.78, 0.95, 0.42)
    def b():
        fill(c, belly, WHITE)
        for k in range(-3, 4):
            ink(c, P_open([(k * 0.16, 0.48), (k * 0.17, 0.98)]), 0.012)
        ink(c, belly, 0.025)
    clip_do(c, head, b)
    head_shadow(c, P, head)
    ink(c, head, 0.05)
    F.eyes(0.48, -0.12, 0.14)
    F.blush(0.70, 0.18, 0.10)
    F.mouth(0, 0.30, 0.44, "wide")
    F.sweat(0.75, -0.55, 0.08)

def a_dauphin(c, P, F):
    fin = P_curve([(-0.25, -0.80), (0.10, -1.30), (0.30, -1.32), (0.20, -1.10), (0.30, -0.80)])
    part(c, fin, P, "cross", 0.04)
    head = P_ell(0, -0.05, 0.98, 0.88)
    part(c, head, P, "col", 0.05)
    clip_do(c, head, lambda: fill(c, P_ell(0, 0.62, 0.70, 0.40), WHITE))
    head_shadow(c, P, head)
    ink(c, head, 0.05)
    snout = P_ell(0, 0.62, 0.36, 0.24)
    fill(c, snout, WHITE); hatch(c, snout, P.light, None); ink(c, snout, 0.04)
    c.arc(0.0, -0.80, 0.05, 0, 2 * math.pi); fill(c, P_ell(0, -0.78, 0.07, 0.04), INK)   # event
    F.eyes(0.42, -0.10, 0.15)
    F.blush(0.62, 0.22, 0.10)
    F.mouth(0, 0.66, 0.30, "small")
    F.sweat(0.70, -0.55, 0.08)

def a_poulet(c, P, F):
    comb = P_curve([(-0.32, -0.80), (-0.36, -1.08), (-0.18, -1.12), (-0.10, -1.30), (0.10, -1.32), (0.18, -1.15),
                    (0.36, -1.12), (0.34, -0.80)])
    part(c, comb, P, "dark", 0.04)
    head = P_ell(0, 0.0, 0.95, 0.95)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    w = P_curve([(-0.10, 0.52), (0.10, 0.52), (0.14, 0.80), (0, 0.92), (-0.14, 0.80)])
    part(c, w, P, "dark", 0.03)
    F.beak(0, 0.22, 0.42, 0.34)
    F.eyes(0.42, -0.18, 0.15)
    F.blush(0.62, 0.20, 0.10)
    F.sweat(0.68, -0.55, 0.08)

def a_hibou(c, P, F):
    for s in (-1, 1):
        t = P_rpoly([(s * 0.30, -0.70), (s * 0.95, -1.15), (s * 0.80, -0.45)], 0.04)
        part(c, t, P, "cross", 0.04)
    head = P_ell(0, 0.0, 1.0, 0.95)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    for s in (-1, 1):
        d = P_ell(s * 0.42, -0.05, 0.42, 0.40)
        part(c, d, P, "light", 0.03)
    for k in range(3):
        ink(c, P_open([(-0.12 - k * 0.1, -0.70 + k * 0.05), (0, -0.60 + k * 0.05), (0.12 + k * 0.1, -0.70 + k * 0.05)]),
            0.016, P.dark)
    F.eyes(0.42, -0.05, 0.17, brow_dy=0.02)
    F.beak(0, 0.20, 0.22, 0.30)
    for y in (0.60, 0.75):
        for x in (-0.3, 0, 0.3):
            ink(c, P_ocurve([(x - 0.08, y), (x, y + 0.05), (x + 0.08, y)]), 0.014, P.dark)
    F.sweat(0.72, -0.55, 0.08)

def a_grenouille(c, P, F):
    head = P_ell(0, 0.18, 1.12, 0.80)
    for s in (-1, 1):
        part(c, P_ell(s * 0.48, -0.52, 0.38, 0.36), P, "col", 0.045)
    part(c, head, P, "col", 0.05)
    for s in (-1, 1):
        clip_do(c, P_ell(s * 0.48, -0.52, 0.38, 0.36), lambda: None)
    fill(c, P_ell(-0.48, -0.42, 0.33, 0.26), P.base); fill(c, P_ell(0.48, -0.42, 0.33, 0.26), P.base)
    head_shadow(c, P, head)
    F.eyes(0.48, -0.52, 0.17, brow_dy=0.06)
    for s in (-1, 1):
        fill(c, P_ell(s * 0.10, 0.12, 0.035, 0.025), INK)
    F.blush(0.66, 0.30, 0.11)
    F.mouth(0, 0.40, 0.70, "wide", 0.8)
    if F.expr in ("serene", "sad_smile"):
        ink(c, P_ocurve([(-0.75, 0.30), (0, 0.55), (0.75, 0.30)]), 0.028)
    F.sweat(0.80, -0.75, 0.08)

def a_pingouin(c, P, F):
    head = P_ell(0, 0.0, 0.98, 0.98)
    part(c, head, P, "dark", 0.05)
    mask = P_curve([(0, -0.30), (0.40, -0.62), (0.80, -0.30), (0.72, 0.30), (0.40, 0.80), (0, 0.92), (-0.40, 0.80),
                    (-0.72, 0.30), (-0.80, -0.30), (-0.40, -0.62)])
    clip_do(c, head, lambda: (fill(c, mask, WHITE), hatch(c, mask, P.light, None, -0.785, 0.06, 0.006)))
    ink(c, mask, 0.03)
    ink(c, head, 0.05)
    F.eyes(0.36, -0.08, 0.15)
    F.beak(0, 0.22, 0.30, 0.28)
    F.blush(0.55, 0.22, 0.10)
    F.sweat(0.68, -0.58, 0.08)

def a_pieuvre(c, P, F):
    for k in range(5):   # bouts de tentacules (courts, pas de corps)
        x = -0.80 + k * 0.40
        t = P_curve([(x - 0.16, 0.55), (x + 0.16, 0.55), (x + 0.14, 0.95), (x + 0.24, 1.10), (x + 0.06, 1.16),
                     (x - 0.12, 1.00)])
        part(c, t, P, "col", 0.035)
        for j in range(2):
            ink(c, P_ell(x + 0.02, 0.78 + j * 0.14, 0.035), 0.012)
    head = P_curve([(0, -1.05), (0.75, -0.80), (1.00, -0.10), (0.85, 0.55), (0.30, 0.75), (-0.30, 0.75),
                    (-0.85, 0.55), (-1.00, -0.10), (-0.75, -0.80)])
    part(c, head, P, "col", 0.05)
    spots(c, head, [(-0.35, -0.72, 0.07), (0.30, -0.78, 0.06), (0.05, -0.55, 0.05), (0.62, -0.42, 0.05),
                    (-0.62, -0.40, 0.06)], P)
    head_shadow(c, P, head)
    ink(c, head, 0.05)
    F.eyes(0.40, -0.05, 0.17)
    F.blush(0.60, 0.28, 0.10)
    F.mouth(0, 0.42, 0.28, "small")
    F.sweat(0.70, -0.55, 0.08)

def a_chimpanze(c, P, F):
    for s in (-1, 1):
        ear(c, P, s * 1.00, -0.05, 0.28)
    head = P_ell(0, 0.0, 0.95, 0.95)
    part(c, head, P, "cross", 0.05)
    mask = P_curve([(0, -0.35), (0.40, -0.62), (0.75, -0.30), (0.70, 0.15), (0.60, 0.65), (0, 0.88), (-0.60, 0.65),
                    (-0.70, 0.15), (-0.75, -0.30), (-0.40, -0.62)])
    part(c, mask, P, "light", 0.035)
    muzzle(c, P, 0, 0.45, 0.46, 0.34, "light")
    for s in (-1, 1):
        fill(c, P_ell(s * 0.07, 0.25, 0.04, 0.03), INK)
    F.eyes(0.36, -0.20, 0.15)
    F.blush(0.58, 0.12, 0.10)
    F.mouth(0, 0.52, 0.42)
    F.sweat(0.68, -0.6, 0.08)

def a_mouton(c, P, F):
    pts = []
    n = 14
    for i in range(n):
        a0, a1 = i * 2 * math.pi / n, (i + 1) * 2 * math.pi / n
        for k in range(7):
            t = k / 6
            a = a0 + (a1 - a0) * t
            r = 1.0 + 0.12 * math.sin(t * math.pi)
            pts.append((math.cos(a) * r, math.sin(a) * r * 0.95))
    wool = P_poly(pts)
    hatch(c, wool, P.light, mix(P.base, PAPER, 0.4), 0.0, 0.05, 0.007)
    ink(c, wool, 0.045)
    for s in (-1, 1):
        e = P_ell(s * 0.82, -0.05, 0.30, 0.14, s * 0.35)
        part(c, e, P, "dark", 0.035)
    face = P_ell(0, 0.18, 0.62, 0.78)
    part(c, face, P, "col", 0.045)
    shade(c, face, P, P_ell(0.5, 0.6, 0.5, 0.5), 0.5)
    tuft = P_curve([(-0.40, -0.55), (-0.25, -0.80), (0, -0.70), (0.25, -0.82), (0.42, -0.55), (0, -0.45)])
    hatch(c, tuft, P.light, mix(P.base, PAPER, 0.4)); ink(c, tuft, 0.035)
    F.eyes(0.30, 0.0, 0.14)
    nose_tri(c, 0, 0.52, 0.12)
    F.blush(0.42, 0.32, 0.08)
    F.mouth(0, 0.68, 0.24, "small")
    F.sweat(0.55, -0.35, 0.07)

def a_tortue(c, P, F):
    shell = P_ell(0, -0.25, 1.25, 0.85)
    part(c, shell, P, "dark", 0.05)
    def hexes():
        for (x, y) in [(0, -0.75), (-0.55, -0.55), (0.55, -0.55), (-0.95, -0.15), (0.95, -0.15), (0, -0.25)]:
            ink(c, P_poly([(x + 0.26 * math.cos(a), y + 0.22 * math.sin(a)) for a in
                           [k * math.pi / 3 for k in range(6)]]), 0.025, PAPER)
    clip_do(c, shell, hexes)
    head = P_ell(0, 0.30, 0.82, 0.72)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    F.eyes(0.34, 0.20, 0.14)
    for s in (-1, 1):
        fill(c, P_ell(s * 0.07, 0.52, 0.03, 0.02), INK)
    F.blush(0.52, 0.48, 0.09)
    F.mouth(0, 0.70, 0.36, "wide")
    F.sweat(0.62, -0.05, 0.08)

def a_escargot(c, P, F):
    shell = P_ell(0, -0.22, 0.98, 0.86)
    part(c, shell, P, "col", 0.05)
    sp = []
    for i in range(70):
        t = i / 69 * 2.7 * math.pi
        r = 0.06 + t * 0.090
        sp.append((0.02 + r * math.cos(t), -0.25 + r * math.sin(t) * 0.88))
    clip_do(c, shell, lambda: (shade(c, shell, P, P_ell(0.6, 0.3, 0.7, 0.7), 0.6),
                               ink(c, P_ocurve(sp), 0.07, P.dark)))
    ink(c, shell, 0.05)
    for s in (-1, 1):   # antennes portant les yeux, au-dessus de la coquille
        ink(c, P_ocurve([(s * 0.20, 0.30), (s * 0.40, -0.30), (s * 0.50, -0.95)]), 0.05)
        ink(c, P_ocurve([(s * 0.20, 0.30), (s * 0.40, -0.30), (s * 0.50, -0.95)]), 0.022, P.base)
    head = P_ell(0, 0.55, 0.72, 0.45)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    F.eyes(0.50, -1.05, 0.13, brow_dy=0.02)
    F.blush(0.42, 0.62, 0.08)
    F.mouth(0, 0.62, 0.30, "small")
    F.sweat(0.80, -1.10, 0.07)

# ================================================================ TRIANGLES
def a_girafe(c, P, F):
    for s in (-1, 1):
        ink(c, P_open([(s * 0.22, -0.65), (s * 0.30, -1.10)]), 0.09)
        ink(c, P_open([(s * 0.22, -0.65), (s * 0.30, -1.10)]), 0.05, P.base)
        part(c, P_ell(s * 0.31, -1.15, 0.11), P, "dark", 0.03)
        e = P_ell(s * 0.95, -0.70, 0.30, 0.13, -s * 0.35)
        part(c, e, P, "col", 0.035)
    head = P_form("triangle", 0.88, sy=1.05)
    part(c, head, P, "col", 0.05)
    patches = [(-0.55, -0.50), (0.0, -0.50), (0.55, -0.48), (-0.25, -0.25), (0.28, -0.22), (0, 0.10)]
    def pf():
        for (x, y) in patches:
            fill(c, P_rpoly([(x - 0.13, y - 0.08), (x + 0.10, y - 0.11), (x + 0.14, y + 0.06), (x - 0.02, y + 0.12),
                             (x - 0.15, y + 0.05)], 0.03), P.dark, 0.85)
    clip_do(c, head, pf)
    head_shadow(c, P, head)
    ink(c, head, 0.05)
    muzzle(c, P, 0, 0.62, 0.30, 0.25, "light")
    for s in (-1, 1):
        fill(c, P_ell(s * 0.09, 0.54, 0.035, 0.025), INK)
    F.eyes(0.32, -0.22, 0.13)
    F.blush(0.42, 0.10, 0.08)
    F.mouth(0, 0.72, 0.22, "small")
    F.sweat(0.62, -0.55, 0.07)

def a_kangourou(c, P, F):
    for s in (-1, 1):
        pointy_ear(c, P, s * 0.45, -0.55, 0.36, 0.85, s * 0.22)
    head = P_form("triangle", 0.88)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    muzzle(c, P, 0, 0.55, 0.32, 0.28, "light")
    nose_oval(c, 0, 0.48, 0.10)
    F.eyes(0.33, -0.22, 0.14)
    F.blush(0.45, 0.08, 0.08)
    F.mouth(0, 0.66, 0.22, "small")
    F.sweat(0.65, -0.52, 0.07)

def a_requin(c, P, F):
    fin = P_rpoly([(-0.30, -0.55), (0.25, -1.30), (0.35, -0.55)], 0.05)
    part(c, fin, P, "cross", 0.045)
    head = P_form("triangle", 0.95)
    part(c, head, P, "col", 0.05)
    clip_do(c, head, lambda: (fill(c, P_poly([(-1.2, 0.15), (1.2, 0.15), (0, 1.3)]), WHITE),
                              ink(c, P_open([(-1.2, 0.15), (1.2, 0.15)]), 0.02)))
    for s in (-1, 1):
        for k in range(3):
            ink(c, P_ocurve([(s * (0.55 + k * 0.08), -0.25), (s * (0.58 + k * 0.08), -0.12),
                             (s * (0.55 + k * 0.08), 0.0)]), 0.018)
    head_shadow(c, P, head)
    ink(c, head, 0.05)
    F.eyes(0.30, -0.32, 0.13)
    F.mouth(0, 0.38, 0.48, "wide")
    if F.expr in ("serene", "sad_smile"):
        for k in range(-2, 3):
            fill(c, P_poly([(k * 0.08 - 0.03, 0.42), (k * 0.08 + 0.03, 0.42), (k * 0.08, 0.47)]), INK)
    F.sweat(0.62, -0.60, 0.07)

def a_faon(c, P, F):
    for s in (-1, 1):
        e = P_ell(s * 0.98, -0.55, 0.38, 0.18, -s * 0.30)
        part(c, e, P, "col", 0.035)
        part(c, P_ell(s * 1.00, -0.55, 0.24, 0.09, -s * 0.30), P, "light", 0.018)
    head = P_form("triangle", 0.90)
    part(c, head, P, "col", 0.05)
    for (x, y, r) in [(-0.12, -0.55, 0.05), (0.15, -0.58, 0.045), (0.0, -0.40, 0.04), (-0.35, -0.55, 0.035),
                      (0.38, -0.52, 0.035)]:
        fill(c, P_ell(x, y, r), WHITE); ink(c, P_ell(x, y, r), 0.01)
    head_shadow(c, P, head)
    ink(c, head, 0.05)
    muzzle(c, P, 0, 0.62, 0.22, 0.20, "light")
    nose_oval(c, 0, 0.66, 0.09)
    F.eyes(0.30, -0.18, 0.15)
    F.blush(0.42, 0.12, 0.08)
    F.mouth(0, 0.48, 0.20, "small")
    F.sweat(0.62, -0.55, 0.07)

def a_crocodile(c, P, F):
    head = P_form("triangle", 0.92, sx=0.95, sy=1.12)
    part(c, head, P, "col", 0.05)
    def scales():
        for (x, y) in [(0, -0.30), (-0.22, -0.05), (0.22, -0.05), (0, 0.20)]:
            fill(c, P_rpoly([(x - 0.08, y), (x, y - 0.07), (x + 0.08, y), (x, y + 0.07)], 0.02), P.dark, 0.7)
    clip_do(c, head, scales)
    head_shadow(c, P, head)
    ink(c, head, 0.05)
    for s in (-1, 1):   # bosses des yeux par-dessus le bord
        part(c, P_ell(s * 0.46, -0.72, 0.34, 0.30), P, "col", 0.045)
    for s in (-1, 1):   # dents le long du museau
        for k in range(3):
            y = 0.42 + k * 0.17
            x = s * (1.03 * 0.95 * (1 - (y + 0.71) / 1.86) - 0.04)
            tri = P_poly([(x, y), (x - s * 0.08, y + 0.02), (x - s * 0.03, y + 0.11)])
            fill(c, tri, WHITE); ink(c, tri, 0.012)
        fill(c, P_ell(s * 0.08, 0.95, 0.035, 0.025), INK)
    F.eyes(0.46, -0.76, 0.14, brow_dy=0.04)
    F.mouth(0, 0.45, 0.42, "wide")
    F.sweat(0.82, -0.95, 0.07)

def a_loup(c, P, F):
    for s in (-1, 1):
        pointy_ear(c, P, s * 0.62, -0.62, 0.50, 0.72, s * 0.18, kind="cross")
    head = P_form("triangle", 0.95)
    part(c, head, P, "col", 0.05)
    for s in (-1, 1):
        fl = P_poly([(s * 0.25, 0.05), (s * 0.75, -0.15), (s * 0.62, 0.02), (s * 0.82, 0.10), (s * 0.55, 0.18),
                     (s * 0.62, 0.32), (s * 0.20, 0.55)])
        clip_do(c, head, lambda: fill(c, fl, WHITE))
        ink(c, fl, 0.022)
    clip_do(c, head, lambda: fill(c, P_poly([(-0.10, -0.70), (0.10, -0.70), (0.05, -0.20), (-0.05, -0.20)]),
                                  P.dark, 0.5))
    head_shadow(c, P, head)
    ink(c, head, 0.05)
    nose_oval(c, 0, 0.72, 0.10)
    F.eyes(0.34, -0.25, 0.14)
    F.mouth(0, 0.50, 0.24, "small")
    F.sweat(0.66, -0.58, 0.07)

def a_lapin(c, P, F):
    for s in (-1, 1):
        e = P_ell(s * 0.36, -1.05, 0.20, 0.55, s * 0.12)
        part(c, e, P, "col", 0.04)
        part(c, P_ell(s * 0.37, -1.02, 0.10, 0.40, s * 0.12), P, "light", 0.02)
    head = P_form("triangle", 0.92, sy=0.95)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    nose_tri(c, 0, 0.40, 0.10, pink=True)
    whiskers(c, 0, 0.48, 0.40)
    if F.expr in ("serene", "sad_smile", "determined"):
        t = P_rpoly([(-0.08, 0.56), (0.08, 0.56), (0.08, 0.70), (-0.08, 0.70)], 0.02)
        fill(c, t, WHITE); ink(c, t, 0.016); ink(c, P_open([(0, 0.56), (0, 0.70)]), 0.01)
    else:
        F.mouth(0, 0.56, 0.22, "small")
    F.eyes(0.32, -0.20, 0.15)
    F.blush(0.45, 0.12, 0.08)
    F.sweat(0.64, -0.55, 0.07)

def a_ane(c, P, F):
    for s in (-1, 1):
        e = P_ell(s * 0.72, -0.98, 0.17, 0.48, s * 0.55)
        part(c, e, P, "col", 0.04)
        part(c, P_ell(s * 0.72, -0.98, 0.08, 0.34, s * 0.55), P, "dark", 0.0)
    head = P_form("triangle", 0.90, sy=1.10)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    forelock(c, P, 0, -0.66, 1.0)
    muzzle(c, P, 0, 0.66, 0.32, 0.30, "light")
    for s in (-1, 1):
        fill(c, P_ell(s * 0.12, 0.60, 0.04, 0.06), INK)
    F.eyes(0.32, -0.20, 0.14)
    F.blush(0.45, 0.12, 0.08)
    F.mouth(0, 0.80, 0.22, "small")
    F.sweat(0.64, -0.55, 0.07)

# ================================================================ LOSANGES
def a_antilope(c, P, F):
    for s in (-1, 1):
        horn = P_curve([(s * 0.10, -0.80), (s * 0.30, -1.30), (s * 0.48, -1.62), (s * 0.40, -1.30), (s * 0.24, -0.80)])
        fill(c, horn, P.darkbase); hatch(c, horn, P.dark, None, 0.0, 0.08, 0.02); ink(c, horn, 0.035)
        e = P_ell(s * 0.85, -0.45, 0.32, 0.13, -s * 0.4)
        part(c, e, P, "col", 0.035)
    head = P_form("diamond", 0.95, sy=1.15)
    part(c, head, P, "col", 0.05)
    head_shadow(c, P, head)
    muzzle(c, P, 0, 0.70, 0.24, 0.22, "light")
    nose_oval(c, 0, 0.66, 0.08)
    F.eyes(0.36, -0.12, 0.14)
    F.blush(0.48, 0.15, 0.08)
    F.mouth(0, 0.84, 0.18, "small")
    F.sweat(0.60, -0.55, 0.07)

def a_panda_roux(c, P, F):
    for s in (-1, 1):
        pointy_ear(c, P, s * 0.60, -0.55, 0.50, 0.50, s * 0.45, kind="dark")
    head = P_form("diamond", 1.0, sx=1.15)
    part(c, head, P, "col", 0.05)
    def marks():
        for s in (-1, 1):
            fill(c, P_ell(s * 0.70, 0.30, 0.42, 0.30), WHITE)
            fill(c, P_ell(s * 0.30, -0.42, 0.10, 0.07), WHITE)
    clip_do(c, head, marks)
    head_shadow(c, P, head)
    ink(c, head, 0.05)
    muzzle(c, P, 0, 0.55, 0.28, 0.24)
    nose_oval(c, 0, 0.42, 0.10)
    F.eyes(0.40, -0.08, 0.15)
    F.blush(0.58, 0.20, 0.10)
    F.mouth(0, 0.62, 0.26, "small")
    F.sweat(0.66, -0.50, 0.08)

def a_cheval(c, P, F):
    for s in (-1, 1):
        pointy_ear(c, P, s * 0.30, -1.00, 0.30, 0.42, s * 0.25)
    head = P_form("diamond", 0.95, sy=1.20)
    part(c, head, P, "col", 0.05)
    clip_do(c, head, lambda: fill(c, P_poly([(-0.08, -0.65), (0.08, -0.65), (0.12, 0.40), (-0.12, 0.40)]), WHITE))
    head_shadow(c, P, head)
    ink(c, head, 0.05)
    forelock(c, P, 0, -0.92, 1.1)
    muzzle(c, P, 0, 0.72, 0.34, 0.30, "light")
    for s in (-1, 1):
        fill(c, P_ell(s * 0.13, 0.66, 0.05, 0.07), INK)
    F.eyes(0.40, -0.15, 0.14)
    F.blush(0.52, 0.18, 0.09)
    F.mouth(0, 0.88, 0.22, "small")
    F.sweat(0.62, -0.60, 0.07)

def a_zebre(c, P, F):
    mane = P_poly([(-0.22, -0.95)] + [(0.0 + (i - 3) * 0.08, -1.30 if i % 2 else -1.10) for i in range(7)] + [(0.22, -0.95)])
    part(c, mane, P, "dark", 0.035)
    for s in (-1, 1):
        pointy_ear(c, P, s * 0.42, -0.85, 0.32, 0.45, s * 0.35)
    head = P_form("diamond", 0.95, sy=1.15)
    part(c, head, P, "col", 0.05)
    stripes(c, head, P, [(-0.9, -0.2, -0.5, -0.35, -0.25, -0.70), (0.9, -0.2, 0.5, -0.35, 0.25, -0.70),
                         (-0.9, 0.05, -0.55, -0.05, -0.30, -0.35), (0.9, 0.05, 0.55, -0.05, 0.30, -0.35),
                         (-0.8, 0.30, -0.5, 0.20, -0.25, 0.25), (0.8, 0.30, 0.5, 0.20, 0.25, 0.25),
                         (-0.15, -0.95, 0, -0.80, 0.15, -0.95)], 0.08)
    head_shadow(c, P, head)
    ink(c, head, 0.05)
    muzzle(c, P, 0, 0.70, 0.32, 0.28, "dark")
    for s in (-1, 1):
        fill(c, P_ell(s * 0.12, 0.64, 0.05, 0.06), INK)
    F.eyes(0.38, -0.10, 0.14)
    F.blush(0.50, 0.20, 0.09)
    F.mouth(0, 0.85, 0.22, "small")
    F.sweat(0.62, -0.55, 0.07)

# ================================================================ REGISTRE
INFO = {  # nom -> (nom_en, forme, remarques)
    # carres
    "panda": ("panda", "square", "taches = version sombre de la couleur"),
    "koala": ("koala", "square", "oreilles duveteuses, gros nez"),
    "elephant": ("elephant", "square", "trompe + defenses + grandes oreilles"),
    "gorille": ("gorilla", "square", "tete sombre, masque clair, arcade"),
    "chien": ("dog", "square", "oreilles tombantes, tache sur l'oeil"),
    "renard": ("fox", "square", "joues blanches en zigzag (comme le renard d'origine)"),
    "ours": ("bear", "square", ""),
    "hippopotame": ("hippo", "square", "large museau"),
    "cochon": ("pig", "square", "groin"),
    "rhinoceros": ("rhino", "square", "corne blanche"),
    "vache": ("cow", "square", "cornes + tache"),
    # ronds
    "chat": ("cat", "circle", ""),
    "baleine": ("whale", "circle", "jet d'eau sur serene/sad_smile/determined"),
    "dauphin": ("dolphin", "circle", "rostre + aileron"),
    "poulet": ("chicken", "circle", "crete et barbillon sombres, bec orange fixe"),
    "hibou": ("owl", "circle", "aigrettes, disques faciaux, bec"),
    "grenouille": ("frog", "circle", "yeux sur le dessus"),
    "pingouin": ("penguin", "circle", "tete sombre + masque blanc"),
    "pieuvre": ("octopus", "circle", "bouts de tentacules courts sous la tete"),
    "chimpanze": ("chimpanzee", "circle", "grandes oreilles, masque clair"),
    "mouton": ("sheep", "circle", "laine festonnee"),
    "tortue": ("turtle", "circle", "carapace derriere la tete"),
    "escargot": ("snail", "circle", "coquille spirale, yeux au bout des antennes"),
    # triangles
    "souris": ("mouse", "triangle", "grandes oreilles rondes"),
    "girafe": ("giraffe", "triangle", "ossicones + plaques"),
    "kangourou": ("kangaroo", "triangle", "grandes oreilles dressees"),
    "requin": ("shark", "triangle", "aileron, ventre blanc, branchies"),
    "faon": ("fawn", "triangle", "points blancs"),
    "crocodile": ("crocodile", "triangle", "yeux en bosses, dents"),
    "loup": ("wolf", "triangle", "joues blanches"),
    "lapin": ("rabbit", "triangle", "longues oreilles, dents"),
    "ane": ("donkey", "triangle", "longues oreilles, toupet"),
    # losanges
    "lion": ("lion", "diamond", "criniere en etoile contre-hachuree"),
    "lionne": ("lioness", "diamond", "comme le lion, sans criniere"),
    "tigre": ("tiger", "diamond", "rayures sombres + touffes de joues"),
    "guepard": ("cheetah", "diamond", "points + traits de larmes"),
    "leopard": ("leopard", "diamond", "rosettes"),
    "jaguar": ("jaguar", "diamond", "rosettes a point central"),
    "antilope": ("antelope", "diamond", "cornes annelees"),
    "panda_roux": ("red panda", "diamond", "joues blanches, traits sous les yeux"),
    "cheval": ("horse", "diamond", "liste blanche, toupet"),
    "zebre": ("zebra", "diamond", "rayures + criniere"),
}

DRAW = {k: globals()["a_" + k] for k in INFO}
ANIMAUX = {k: dict(nom_en=v[0], forme=v[1], expressions=list(EXPRESSIONS), remarques=v[2]) for k, v in INFO.items()}

def dessiner(nom, c, cx, cy, S, rot, expr, col, look=(0, 0), tear_len=0):
    """Trace la tete de l'animal `nom` centree en (cx, cy), taille S (S=760 gros plan, S=560 plan moyen),
    rotation rot (radians), expression expr, couleur col=(r,g,b) 0..1.
    look=(dx,dy) direction du regard (-1..1), tear_len = longueur des larmes (px a S=760). Aucun retour."""
    if nom not in DRAW:
        raise KeyError(f"animal inconnu: {nom}")
    if expr not in EXPRESSIONS:
        raise ValueError(f"expression inconnue: {expr}")
    c.save()
    c.translate(cx, cy); c.rotate(rot); c.scale(S * 0.40, S * 0.40)
    P = Pal(tuple(col))
    F = Face(c, P, expr, look, tear_len)
    DRAW[nom](c, P, F)
    c.restore()
    c.new_path()
