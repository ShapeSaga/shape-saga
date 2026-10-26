"""Décors de jeu de qualité : fond illustré (dégradés, éléments lointains), murs en vrais matériaux (briques, glace, bois…),
liquide lumineux animé (dégradé, écume, bulles, lueur) et particules. Le fond fixe est dessiné une seule fois par thème."""
import math, random, zlib, cairo

W, H = 1080, 1920

# ------------------------------------------------------------------ palettes
DECOR = {
    "lave": dict(top=(.99, .76, .50), bot=(.99, .92, .80), deco="volcans", mur="brique", mc=(.42, .25, .21), mh=(.66, .42, .31),
                 liq=dict(deep=(.50, .05, .04), mid=(.95, .30, .07), top=(1, .80, .28), glow=(1, .55, .15)), part="braises", crust=True),
    "eau": dict(top=(.50, .80, .98), bot=(.88, .97, 1), deco="nuages", mur="pierre", mc=(.33, .45, .58), mh=(.58, .72, .84),
                liq=dict(deep=(.04, .22, .52), mid=(.12, .52, .84), top=(.70, .94, 1), glow=(.40, .80, 1)), part="bulles"),
    "slime": dict(top=(.78, .92, .58), bot=(.94, .99, .84), deco="marais", mur="mousse", mc=(.32, .38, .24), mh=(.52, .62, .36),
                  liq=dict(deep=(.08, .32, .04), mid=(.38, .76, .12), top=(.82, 1, .36), glow=(.60, .95, .20)), part="bulles"),
    "glace": dict(top=(.66, .83, .98), bot=(.96, .98, 1), deco="montagnes", mur="glace", mc=(.50, .72, .90), mh=(.88, .96, 1),
                  liq=dict(deep=(.04, .18, .42), mid=(.18, .48, .80), top=(.78, .94, 1), glow=(.60, .90, 1)), part="neige"),
    "nuit": dict(top=(.04, .05, .17), bot=(.19, .16, .38), deco="lune", mur="pierre", mc=(.24, .26, .46), mh=(.46, .50, .74),
                 liq=dict(deep=(.18, .04, .32), mid=(.55, .24, .85), top=(.88, .68, 1), glow=(.70, .40, 1)), part="lucioles"),
    "desert": dict(top=(.99, .74, .42), bot=(.99, .91, .72), deco="dunes", mur="gres", mc=(.56, .36, .21), mh=(.84, .62, .38),
                   liq=dict(deep=(.50, .26, .08), mid=(.84, .52, .18), top=(1, .86, .46), glow=(1, .72, .30)), part="poussiere"),
    "bonbons": dict(top=(1, .74, .88), bot=(1, .93, .97), deco="bonbons", mur="rayures", mc=(.94, .42, .60), mh=(1, .82, .90),
                    liq=dict(deep=(.60, .08, .32), mid=(.94, .34, .60), top=(1, .72, .86), glow=(1, .56, .80)), part="etincelles"),
    "foret": dict(top=(.50, .76, .52), bot=(.86, .96, .76), deco="arbres", mur="bois", mc=(.44, .29, .17), mh=(.66, .48, .28),
                  liq=dict(deep=(.04, .22, .18), mid=(.10, .54, .44), top=(.56, .96, .82), glow=(.40, .90, .70)), part="lucioles"),
    "cosmos": dict(top=(.03, .02, .12), bot=(.24, .08, .38), deco="nebuleuse", mur="cristal", mc=(.20, .22, .46), mh=(.52, .72, 1),
                   liq=dict(deep=(.32, .02, .34), mid=(.84, .14, .64), top=(1, .62, .92), glow=(1, .30, .80)), part="etincelles"),
    "prison": dict(top=(.10, .10, .15), bot=(.28, .26, .31), deco="cellules", mur="pierre", mc=(.24, .24, .30), mh=(.42, .42, .52),
                   liq=dict(deep=(.1, .1, .1), mid=(.3, .3, .3), top=(.6, .6, .6), glow=(.5, .5, .5)), part="poussiere"),
    "rouille": dict(top=(.52, .43, .39), bot=(.82, .72, .62), deco="engrenages", mur="metal", mc=(.36, .29, .27), mh=(.62, .50, .44),
                    liq=dict(deep=(.34, .14, .02), mid=(.86, .44, .05), top=(1, .86, .22), glow=(1, .60, .10)), part="braises", crust=True),
}


def _mix(a, b, k):
    return tuple(a[i] * (1 - k) + b[i] * k for i in range(3))


def _shade(a, k):
    return tuple(max(0, min(1, q * k)) for q in a)


_OFF = [0]


def _R(seed):
    """Générateur aléatoire dont la graine dépend de l'épisode : même thème, éléments placés autrement."""
    return random.Random(int(seed) + _OFF[0] * 7919)


# ------------------------------------------------------------------ outils de dessin
def vgrad(c, x0, y0, x1, y1, stops, horizontal=False):
    g = cairo.LinearGradient(x0, y0, x1 if horizontal else x0, y1 if not horizontal else y0)
    for o, col, a in stops:
        g.add_color_stop_rgba(o, *col, a)
    return g


def disque(c, x, y, r, col, a0=1.0, a1=0.0, core=0.0):
    """Disque lumineux à bord doux (dégradé radial)."""
    g = cairo.RadialGradient(x, y, r * core, x, y, r)
    g.add_color_stop_rgba(0, *col, a0)
    g.add_color_stop_rgba(1, *col, a1)
    c.set_source(g)
    c.new_path(); c.arc(x, y, r, 0, 6.2832); c.fill()


def crete(c, ybase, amp, col_top, col_bot, seed, a=1.0, freq=1.0, y_end=None):
    """Chaîne de collines/montagnes : silhouette dégradée."""
    rr = _R(seed)
    ph = [rr.uniform(0, 6.28) for _ in range(4)]
    pts = []
    for x in range(0, W + 1, 8):
        y = ybase - amp * (.5 * math.sin(x / 190 * freq + ph[0]) + .3 * math.sin(x / 83 * freq + ph[1]) + .2 * math.sin(x / 41 * freq + ph[2]))
        pts.append((x, y))
    c.new_path(); c.move_to(0, H)
    for p in pts:
        c.line_to(*p)
    c.line_to(W, H); c.close_path()
    c.set_source(vgrad(c, 0, ybase - amp, 0, y_end or ybase + 500, [(0, col_top, a), (1, col_bot, a)]))
    c.fill()


def pics(c, ybase, hauteur, col_top, col_bot, seed, neige=None):
    """Montagnes pointues (avec calotte neigeuse en option)."""
    rr = _R(seed)
    x = -80
    while x < W + 80:
        w = rr.uniform(260, 420); h = rr.uniform(.6, 1) * hauteur
        c.new_path(); c.move_to(x, ybase + 400); c.line_to(x + w * .5, ybase - h); c.line_to(x + w, ybase + 400); c.close_path()
        c.set_source(vgrad(c, 0, ybase - h, 0, ybase + 300, [(0, col_top, 1), (1, col_bot, 1)])); c.fill()
        if neige:
            c.new_path(); c.move_to(x + w * .5, ybase - h)
            c.line_to(x + w * .5 - w * .17, ybase - h + h * .30); c.line_to(x + w * .5 - w * .06, ybase - h + h * .24)
            c.line_to(x + w * .5 + w * .03, ybase - h + h * .34); c.line_to(x + w * .5 + w * .17, ybase - h + h * .30); c.close_path()
            c.set_source_rgba(*neige, .95); c.fill()
        x += w * rr.uniform(.55, .8)


def nuage(c, x, y, s, col=(1, 1, 1), a=.9):
    for dx, dy, r in ((-1.0, .2, .75), (-.4, -.15, 1.0), (.35, -.05, .9), (1.0, .22, .7), (0, .3, 1.1)):
        disque(c, x + dx * s, y + dy * s, r * s, col, a, 0, .35)


def etoile4(c, x, y, r, col, a=1):
    c.new_path()
    for i in range(8):
        ang = i * math.pi / 4 - math.pi / 2
        rad = r if i % 2 == 0 else r * .22
        (c.move_to if i == 0 else c.line_to)(x + rad * math.cos(ang), y + rad * math.sin(ang))
    c.close_path(); c.set_source_rgba(*col, a); c.fill()


def engrenage(c, x, y, r, dents, col, a=.5, rot=0):
    c.new_path()
    for i in range(dents * 2):
        ang = rot + i * math.pi / dents
        rad = r if i % 2 == 0 else r * .82
        for da in (-.2, .2):
            ax = ang + da * math.pi / dents
            (c.move_to if (i == 0 and da == -.2) else c.line_to)(x + rad * math.cos(ax), y + rad * math.sin(ax))
    c.close_path()
    c.set_source_rgba(*col, a); c.fill()
    c.new_path(); c.arc(x, y, r * .45, 0, 6.2832); c.set_source_rgba(0, 0, 0, a * .5); c.fill()
    c.new_path(); c.arc(x, y, r * .2, 0, 6.2832); c.set_source_rgba(*col, a); c.fill()


# ------------------------------------------------------------------ éléments de fond par thème
def deco_volcans(c, P):
    crete(c, 1180, 160, (.80, .58, .50), (.95, .80, .68), 1, .9, .6)
    for vx, vh, s in ((250, 520, 1), (820, 640, 2)):
        yb = 1500
        c.new_path(); c.move_to(vx - 420, yb + 300); c.line_to(vx - 55, yb - vh); c.line_to(vx + 55, yb - vh); c.line_to(vx + 420, yb + 300); c.close_path()
        c.set_source(vgrad(c, 0, yb - vh, 0, yb + 300, [(0, (.42, .26, .24), 1), (1, (.74, .52, .42), 1)])); c.fill()
        disque(c, vx, yb - vh, 200, (1, .55, .15), .55, 0, .1)
        for k in range(6):                                           # fumée
            nuage(c, vx + 35 * k * (1 if s == 1 else -1), yb - vh - 110 - k * 120, 55 + k * 18, (.55, .43, .40), .30)
    crete(c, 1520, 120, (.55, .35, .30), (.80, .60, .50), 3, 1.1, .7)
    for i in range(24):                                              # cendres lumineuses
        disque(c, _R(i).uniform(60, 1020), _R(i + 99).uniform(250, 1400), _R(i + 7).uniform(10, 26), (1, .6, .2), .5, 0, .2)


def deco_nuages(c, P):
    for i, (x, y, s) in enumerate(((180, 330, 90), (820, 460, 120), (420, 760, 80), (900, 980, 100), (230, 1230, 110), (700, 1480, 90))):
        nuage(c, x, y, s, (1, 1, 1), .85)
    for i in range(7):                                               # mouettes
        x, y = 200 + i * 110, 230 + (i % 3) * 55
        c.move_to(x - 16, y); c.curve_to(x - 8, y - 10, x - 2, y - 8, x, y); c.curve_to(x + 2, y - 8, x + 8, y - 10, x + 16, y)
        c.set_source_rgba(.25, .35, .5, .55); c.set_line_width(3); c.stroke()
    crete(c, 1560, 90, (.55, .82, .96), (.75, .92, 1), 5, 1.3, .7, 1900)


def deco_marais(c, P):
    crete(c, 1000, 200, (.55, .75, .42), (.80, .92, .66), 11, .9, .6)
    crete(c, 1350, 160, (.42, .62, .30), (.74, .88, .56), 12, 1, .8)
    rr = _R(5)
    for i in range(9):                                               # champignons géants
        x, y, s = rr.uniform(100, 980), rr.uniform(700, 1500), rr.uniform(.8, 1.5)
        c.new_path(); c.rectangle(x - 10 * s, y, 20 * s, 90 * s); c.set_source_rgba(.95, .92, .78, .7); c.fill()
        c.new_path(); c.arc(x, y, 62 * s, math.pi, 0); c.close_path()
        c.set_source(vgrad(c, 0, y - 62 * s, 0, y, [(0, (.88, .35, .45), .75), (1, (.70, .22, .35), .75)])); c.fill()
        for dx, dy in ((-.35, -.4), (.25, -.55), (.4, -.2)):
            c.new_path(); c.arc(x + dx * 62 * s, y + dy * 62 * s, 9 * s, 0, 6.28); c.set_source_rgba(1, 1, .9, .85); c.fill()
    for i in range(10):                                              # lianes
        x = rr.uniform(60, 1020)
        c.move_to(x, 120); c.curve_to(x + 30, 300, x - 30, 460, x + 10, 640 + rr.uniform(0, 150))
        c.set_source_rgba(.25, .45, .22, .55); c.set_line_width(5); c.stroke()


def deco_montagnes(c, P):
    pics(c, 1050, 520, (.62, .76, .90), (.86, .93, .99), 2, (1, 1, 1))
    pics(c, 1350, 430, (.46, .62, .80), (.78, .88, .96), 4, (1, 1, 1))
    rr = _R(9)
    for i in range(26):                                              # sapins enneigés
        x, y, s = rr.uniform(40, 1040), rr.uniform(1250, 1800), rr.uniform(.8, 1.7)
        for k in range(3):
            c.new_path(); c.move_to(x, y - 90 * s + k * 38 * s); c.line_to(x - (34 + k * 12) * s, y - 40 * s + k * 38 * s); c.line_to(x + (34 + k * 12) * s, y - 40 * s + k * 38 * s)
            c.close_path(); c.set_source_rgba(.22, .45, .45, .75); c.fill()
            c.new_path(); c.move_to(x, y - 90 * s + k * 38 * s); c.line_to(x - 17 * s, y - 62 * s + k * 38 * s); c.line_to(x + 17 * s, y - 62 * s + k * 38 * s)
            c.close_path(); c.set_source_rgba(1, 1, 1, .85); c.fill()
    c.set_source(vgrad(c, 0, 120, 0, 700, [(0, (.55, .95, .85), .30), (1, (.55, .95, .85), 0)])); c.rectangle(0, 120, W, 600); c.fill()   # aurore


def deco_lune(c, P):
    rr = _R(21)
    for i in range(170):
        x, y, s = rr.uniform(0, W), rr.uniform(0, 1500), rr.uniform(.6, 2.6)
        disque(c, x, y, s * 4, (.85, .90, 1), .5 + .3 * rr.random(), 0, .1)
        if s > 2.1:
            etoile4(c, x, y, s * 6, (1, 1, 1), .9)
    disque(c, 800, 360, 330, (.7, .75, 1), .35, 0, .3)               # halo
    c.new_path(); c.arc(800, 360, 150, 0, 6.28)
    c.set_source(vgrad(c, 0, 210, 0, 510, [(0, (1, .98, .86), 1), (1, (.90, .86, .72), 1)])); c.fill()
    for dx, dy, r in ((-50, -30, 28), (35, 40, 22), (45, -55, 14), (-30, 62, 16)):   # cratères
        c.new_path(); c.arc(800 + dx, 360 + dy, r, 0, 6.28); c.set_source_rgba(.78, .74, .60, .6); c.fill()
    c.move_to(150, 260); c.line_to(420, 380); c.set_source_rgba(1, 1, 1, .8); c.set_line_width(4); c.stroke()      # étoile filante
    disque(c, 150, 260, 14, (1, 1, 1), 1, 0, .2)
    crete(c, 1500, 130, (.14, .13, .30), (.22, .20, .42), 7, 1, .8)
    crete(c, 1700, 100, (.10, .09, .22), (.18, .16, .34), 8, 1.2, .9)
    for i in range(5):                                               # nuages de nuit
        nuage(c, 150 + i * 220, 900 + (i % 2) * 380, 70, (.40, .38, .65), .28)


def deco_dunes(c, P):
    disque(c, 780, 320, 420, (1, .9, .55), .65, 0, .2)
    c.new_path(); c.arc(780, 320, 130, 0, 6.28); c.set_source(vgrad(c, 0, 190, 0, 450, [(0, (1, .96, .75), 1), (1, (1, .80, .40), 1)])); c.fill()
    crete(c, 1050, 170, (.95, .70, .40), (.98, .86, .62), 31, 1, .7)
    crete(c, 1320, 190, (.86, .58, .32), (.96, .80, .56), 32, 1, .8)
    crete(c, 1620, 150, (.78, .50, .27), (.92, .72, .48), 33, 1, 1)
    for x, y, s in ((140, 1220, 1.2), (900, 1500, 1.5), (480, 1700, 1)):    # cactus
        c.set_source_rgba(.28, .45, .25, .8); c.set_line_width(26 * s); c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.move_to(x, y); c.line_to(x, y - 150 * s); c.stroke()
        c.move_to(x - 55 * s, y - 60 * s); c.line_to(x - 55 * s, y - 100 * s); c.line_to(x, y - 85 * s); c.stroke()
        c.move_to(x + 55 * s, y - 80 * s); c.line_to(x + 55 * s, y - 120 * s); c.line_to(x, y - 105 * s); c.stroke()
    for k in range(5):                                               # mirage
        c.move_to(0, 1050 + k * 7); c.line_to(W, 1050 + k * 7); c.set_source_rgba(1, 1, 1, .10); c.set_line_width(2); c.stroke()


def deco_bonbons(c, P):
    rr = _R(41)
    for i in range(34):                                              # pois / bonbons
        x, y, r = rr.uniform(60, 1020), rr.uniform(160, 1840), rr.uniform(26, 92)
        col = rr.choice(((1, .60, .78), (.78, .62, 1), (.62, .86, 1), (1, .85, .55), (.7, 1, .8)))
        disque(c, x, y, r, col, .45, .25, .55)
    for i in range(6):                                               # sucettes géantes
        x, y = rr.uniform(120, 960), rr.uniform(300, 1500)
        c.set_source_rgba(1, 1, 1, .6); c.set_line_width(10); c.move_to(x, y + 70); c.line_to(x, y + 250); c.stroke()
        c.new_path(); c.arc(x, y, 70, 0, 6.28); c.set_source_rgba(1, .50, .72, .75); c.fill()
        c.set_source_rgba(1, 1, 1, .8); c.set_line_width(9)
        for k in range(36):
            a = k * .35; rad = 4 + k * 1.8
            (c.move_to if k == 0 else c.line_to)(x + rad * math.cos(a), y + rad * math.sin(a))
        c.stroke()
    for i in range(90):                                              # vermicelles
        x, y, a = rr.uniform(60, 1020), rr.uniform(160, 1840), rr.uniform(0, 3.14)
        c.set_source_rgba(*rr.choice(((1, .4, .6), (.5, .7, 1), (1, .85, .3), (.6, .9, .6))), .7)
        c.set_line_width(7); c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.move_to(x, y); c.line_to(x + 22 * math.cos(a), y + 22 * math.sin(a)); c.stroke()


def deco_arbres(c, P):
    crete(c, 900, 170, (.45, .68, .48), (.75, .90, .70), 51, 1, .7)
    rr = _R(52)
    for couche, (alpha, ybase) in enumerate(((.35, 1200), (.55, 1500), (.8, 1800))):
        for i in range(6):
            x = 90 + i * 190 + rr.uniform(-40, 40) + couche * 40
            h = rr.uniform(800, 1250); tw = 40 + couche * 20
            c.new_path(); c.rectangle(x - tw / 2, ybase - h, tw, h + 200)
            c.set_source(vgrad(c, x - tw / 2, 0, x + tw / 2, 0, [(0, (.30, .20, .12), alpha), (1, (.48, .34, .20), alpha)], True)); c.fill()
            for k in range(7):
                disque(c, x + rr.uniform(-110, 110), ybase - h + rr.uniform(-60, 140), rr.uniform(80, 150), (.22 + .12 * couche, .52 + .1 * couche, .26), alpha, alpha * .1, .5)
    for i in range(9):                                               # rayons de lumière
        x = 100 + i * 120
        c.new_path(); c.move_to(x, 120); c.line_to(x + 70, 120); c.line_to(x + 340, 1500); c.line_to(x + 180, 1500); c.close_path()
        c.set_source_rgba(1, 1, .75, .10); c.fill()


def deco_nebuleuse(c, P):
    rr = _R(61)
    for i in range(14):
        col = rr.choice(((.55, .15, .75), (.15, .35, .85), (.85, .2, .6), (.2, .7, .8)))
        disque(c, rr.uniform(0, W), rr.uniform(200, 1700), rr.uniform(260, 520), col, .34, 0, 0)
    for i in range(230):
        x, y, s = rr.uniform(0, W), rr.uniform(0, H), rr.uniform(.5, 2.4)
        disque(c, x, y, s * 3.5, (.9, .92, 1), .6, 0, .1)
        if s > 2:
            etoile4(c, x, y, s * 7, (1, 1, 1), .85)
    cx, cy = 280, 520                                                # planète à anneau
    c.save(); c.translate(cx, cy); c.rotate(-.35); c.scale(1, .28)
    c.new_path(); c.arc(0, 0, 230, 0, 6.28); c.set_source_rgba(.85, .7, 1, .5); c.set_line_width(26); c.stroke(); c.restore()
    disque(c, cx, cy, 130, (.95, .6, .85), 1, 1, 0)
    c.new_path(); c.arc(cx, cy, 130, 0, 6.28); c.set_source(vgrad(c, 0, cy - 130, 0, cy + 130, [(0, (.98, .72, .90), 1), (1, (.55, .20, .60), 1)])); c.fill()
    c.save(); c.translate(cx, cy); c.rotate(-.35); c.scale(1, .28)
    c.new_path(); c.arc(0, 0, 230, math.pi, 0); c.set_source_rgba(.9, .8, 1, .75); c.set_line_width(22); c.stroke(); c.restore()


def deco_engrenages(c, P):
    rr = _R(71)
    for i in range(13):
        x, y, r = rr.uniform(0, W), rr.uniform(160, 1800), rr.uniform(90, 260)
        engrenage(c, x, y, r, int(r / 11), (.30, .24, .22), .33, rr.uniform(0, 6))
    for i in range(7):                                               # tuyaux
        y = 260 + i * 240
        c.set_source_rgba(.28, .22, .20, .28); c.set_line_width(34); c.move_to(0, y); c.line_to(W, y + rr.uniform(-80, 80)); c.stroke()
    for i in range(30):                                              # fumées de vapeur
        disque(c, rr.uniform(60, 1020), rr.uniform(200, 1500), rr.uniform(40, 90), (1, 1, 1), .12, 0, .2)


def deco_cellules(c, P):
    rr = _R(81)
    y = 0
    while y < H:                                                     # mur de briques sombres
        x = -(60 if (y // 44) % 2 else 0)
        while x < W:
            t = rr.uniform(-.06, .07)
            c.rectangle(x + 3, y + 3, 114, 38); c.set_source_rgba(.52 + t, .50 + t, .56 + t, .20); c.fill()
            c.rectangle(x + 3, y + 3, 114, 38); c.set_source_rgba(0, 0, 0, .30); c.set_line_width(2); c.stroke()
            x += 120
        y += 44
    for fx in (190, 540, 890):                                       # fenêtres à barreaux et faisceaux de lumière
        c.new_path(); c.move_to(fx - 40, 330); c.line_to(fx + 40, 330); c.line_to(fx + 230, 1300); c.line_to(fx - 190, 1300); c.close_path()
        c.set_source(vgrad(c, 0, 330, 0, 1300, [(0, (1, .95, .7), .20), (1, (1, .95, .7), 0)])); c.fill()
        c.rectangle(fx - 62, 170, 124, 190); c.set_source_rgb(.05, .06, .12); c.fill_preserve(); c.set_source_rgb(.02, .02, .03); c.set_line_width(8); c.stroke()
        disque(c, fx, 265, 70, (1, .95, .7), .55, 0, .1)
        for bx in range(fx - 40, fx + 50, 26):
            c.move_to(bx, 170); c.line_to(bx, 360); c.set_source_rgb(.3, .3, .35); c.set_line_width(7); c.stroke()
    for tx, ty in ((70, 700), (1010, 700), (70, 1350), (1010, 1350)):   # torches
        disque(c, tx, ty - 20, 150, (1, .55, .15), .55, 0, .1)
        c.rectangle(tx - 6, ty, 12, 70); c.set_source_rgb(.2, .12, .08); c.fill()
        c.new_path(); c.move_to(tx - 16, ty); c.curve_to(tx - 10, ty - 30, tx, ty - 48, tx, ty - 60); c.curve_to(tx + 6, ty - 40, tx + 18, ty - 24, tx + 16, ty); c.close_path()
        c.set_source_rgb(1, .65, .15); c.fill()
    for i in range(9):                                               # chaînes
        x = rr.uniform(120, 960)
        for k in range(10):
            c.save(); c.translate(x, 130 + k * 22); c.scale(1, 1.5); c.new_path(); c.arc(0, 0, 8, 0, 6.28)
            c.restore(); c.set_source_rgba(.5, .5, .55, .6); c.set_line_width(3); c.stroke()


DECOS = dict(cellules=deco_cellules, volcans=deco_volcans, nuages=deco_nuages, marais=deco_marais, montagnes=deco_montagnes, lune=deco_lune,
             dunes=deco_dunes, bonbons=deco_bonbons, arbres=deco_arbres, nebuleuse=deco_nebuleuse, engrenages=deco_engrenages)


# ------------------------------------------------------------------ murs
def mur(c, r, P, rr):
    x0, y0, x1, y1 = r
    w, h = x1 - x0, y1 - y0
    mc, mh, mat = P["mc"], P["mh"], P["mur"]
    horiz = h <= 60 and w > h
    if horiz:                                                        # ombre portée sous la plateforme
        c.rectangle(x0 + 4, y1, w, 26); c.set_source(vgrad(c, 0, y1, 0, y1 + 26, [(0, (0, 0, 0), .30), (1, (0, 0, 0), 0)])); c.fill()
    c.save(); c.rectangle(x0, y0, w, h); c.clip()
    c.set_source(vgrad(c, 0, y0, 0, y1, [(0, mh, 1), (.25, _mix(mh, mc, .6), 1), (1, _shade(mc, .78), 1)])) if horiz else c.set_source_rgb(*mc)
    c.paint()
    if mat in ("brique", "mousse", "pierre"):
        bh = 18 if mat == "brique" else 22
        ww = (46, 70) if mat != "pierre" else (38, 90)
        y, row = y0, 0
        while y < y1:
            x = x0 - (row % 2) * 24 - rr.uniform(0, 20)
            while x < x1:
                bw = rr.uniform(*ww)
                tone = rr.uniform(-.10, .12)
                c.rectangle(x, y, bw, bh); c.set_source_rgba(*((1, 1, 1) if tone > 0 else (0, 0, 0)), abs(tone)); c.fill()
                c.rectangle(x, y, bw, bh); c.set_source_rgba(0, 0, 0, .35); c.set_line_width(1.6); c.stroke()
                c.move_to(x + 2, y + 1.5); c.line_to(x + bw - 2, y + 1.5); c.set_source_rgba(1, 1, 1, .18); c.set_line_width(1.5); c.stroke()
                x += bw
            y += bh; row += 1
        if mat == "mousse":
            for i in range(int(w / 16) + 1):
                disque(c, x0 + i * 16 + rr.uniform(0, 10), y0 + rr.uniform(-2, 6), rr.uniform(9, 17), (.45, .75, .25), .95, .6, .5)
    elif mat == "glace":
        for i in range(int(w / 26) + 1):
            c.move_to(x0 + i * 26, y1); c.line_to(x0 + i * 26 + 60, y0); c.set_source_rgba(1, 1, 1, .30); c.set_line_width(rr.uniform(2, 6)); c.stroke()
        for i in range(int(w * h / 900) + 2):
            etoile4(c, rr.uniform(x0, x1), rr.uniform(y0, y1), rr.uniform(2.5, 6), (1, 1, 1), .85)
    elif mat == "gres":
        for k in range(int(h / 9) + 1):
            yy = y0 + k * 9
            c.move_to(x0, yy)
            for x in range(int(x0), int(x1) + 12, 12):
                c.line_to(x, yy + 2.2 * math.sin(x / 17 + k))
            c.set_source_rgba(0, 0, 0, .14); c.set_line_width(1.6); c.stroke()
        for i in range(int(w * h / 500) + 4):
            c.rectangle(rr.uniform(x0, x1), rr.uniform(y0, y1), 2, 2); c.set_source_rgba(1, .95, .8, .5); c.fill()
    elif mat == "rayures":
        k = -h
        while k < w + h:
            c.move_to(x0 + k, y1); c.line_to(x0 + k + 15, y1); c.line_to(x0 + k + 15 + h, y0); c.line_to(x0 + k + h, y0); c.close_path()
            c.set_source_rgba(1, 1, 1, .55); c.fill(); k += 30
        c.rectangle(x0, y0, w, max(4, h * .28)); c.set_source_rgba(1, 1, 1, .30); c.fill()
    elif mat == "bois":
        for k in range(int(h / 14) + 1):
            c.move_to(x0, y0 + k * 14); c.line_to(x1, y0 + k * 14); c.set_source_rgba(0, 0, 0, .30); c.set_line_width(1.6); c.stroke()
        for i in range(int(w * h / 2400) + 3):
            gx, gy = rr.uniform(x0, x1), rr.uniform(y0, y1)
            c.move_to(gx, gy); c.curve_to(gx + 18, gy - 3, gx + 36, gy + 3, gx + 56, gy); c.set_source_rgba(0, 0, 0, .18); c.set_line_width(1.4); c.stroke()
        if horiz:
            for nx in (x0 + 9, x1 - 9):
                disque(c, nx, y0 + h / 2, 3.4, (.2, .15, .1), 1, 1, 0)
    elif mat == "cristal":
        for i in range(int(w * h / 1400) + 4):
            px, py = rr.uniform(x0, x1), rr.uniform(y0, y1)
            c.move_to(px, py); c.line_to(px + rr.uniform(-40, 40), py + rr.uniform(-18, 18)); c.line_to(px + rr.uniform(-40, 40), py + rr.uniform(-18, 18)); c.close_path()
            c.set_source_rgba(*((.8, .9, 1) if rr.random() > .5 else (.1, .1, .35)), rr.uniform(.12, .32)); c.fill()
        c.rectangle(x0, y0, w, 3); c.set_source_rgba(.7, .9, 1, .9); c.fill()
    elif mat == "metal":
        step = 64
        for xx in range(int(x0), int(x1), step):
            c.move_to(xx, y0); c.line_to(xx, y1); c.set_source_rgba(0, 0, 0, .35); c.set_line_width(2); c.stroke()
            for ry in ((y0 + 7, y1 - 7) if horiz else range(int(y0) + 10, int(y1), 90)):
                for rx in (xx + 8, xx + step - 8):
                    disque(c, rx, ry, 3.6, (.75, .65, .6), 1, .7, .2)
        for i in range(int(w * h / 3000) + 2):
            sx, sy = rr.uniform(x0, x1), rr.uniform(y0, y1)
            c.move_to(sx, sy); c.line_to(sx + rr.uniform(6, 24), sy + rr.uniform(-3, 3)); c.set_source_rgba(1, 1, 1, .25); c.set_line_width(1); c.stroke()
    c.restore()
    c.rectangle(x0, y0, w, h); c.set_source_rgba(0, 0, 0, .55); c.set_line_width(3); c.stroke()
    c.move_to(x0 + 1.5, y0 + 1.5); c.line_to(x1 - 1.5, y0 + 1.5); c.set_source_rgba(1, 1, 1, .45); c.set_line_width(2.4); c.stroke()
    if mat == "glace" and horiz:                                     # stalactites
        for i in range(int(w / 34)):
            gx = x0 + 14 + i * 34 + rr.uniform(-6, 6); gl = rr.uniform(10, 26)
            c.move_to(gx - 7, y1); c.line_to(gx, y1 + gl); c.line_to(gx + 7, y1); c.close_path(); c.set_source_rgba(.85, .95, 1, .95); c.fill()


# ------------------------------------------------------------------ fond fixe (mis en cache)
_CACHE = {}


def _variante(P, rr):
    """Décale légèrement les couleurs : le même thème n'a jamais exactement la même ambiance."""
    Q = dict(P)
    k = rr.uniform(-.07, .07)
    for cle in ("top", "bot"):
        Q[cle] = tuple(max(0, min(1, q + k + rr.uniform(-.03, .03))) for q in P[cle])
    return Q


def fond(nom, walls, graine=0):
    cle = (nom, graine, len(walls), sum(r[0] + r[1] * 3 + r[2] * 5 + r[3] * 7 for r in walls))
    if cle in _CACHE:
        return _CACHE[cle]
    _OFF[0] = graine
    rr = _R(zlib.crc32(nom.encode()) % 9973)
    P = _variante(DECOR[nom], rr)
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    c.set_source(vgrad(c, 0, 0, 0, H, [(0, P["top"], 1), (1, P["bot"], 1)])); c.paint()
    DECOS[P["deco"]](c, P)
    g = cairo.RadialGradient(W / 2, H / 2, 500, W / 2, H / 2, 1250)  # vignette
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, .38)
    c.set_source(g); c.paint()
    for r in walls:
        mur(c, r, P, rr)
    _CACHE.clear()
    _CACHE[cle] = s
    return s


# ------------------------------------------------------------------ éléments animés
_PART = {}


def _particules(nom):
    if nom not in _PART:
        rr = _R(zlib.crc32(nom.encode()) % 7919 + _OFF[0])
        _PART[nom] = [(rr.uniform(60, 1020), rr.uniform(0, 1), rr.uniform(.4, 1.3), rr.uniform(2.5, 7), rr.uniform(0, 6.28)) for _ in range(34)]
    return _PART[nom]


def particules(c, nom, gt, ly):
    P = DECOR[nom]; kind = P["part"]; g = P["liq"]["glow"]
    for x0, y0, sp, sz, ph in _particules(nom):
        if kind == "braises":
            y = ly - ((y0 * 1500 + gt * sp * 140) % 1500)
            x = x0 + 30 * math.sin(gt * sp * 1.7 + ph)
            if y < 130: continue
            disque(c, x, y, sz * 2.2, (1, .62, .2), .55 + .35 * math.sin(gt * 7 + ph), 0, .2)
        elif kind == "neige":
            y = (y0 * H + gt * sp * 120) % H; x = x0 + 40 * math.sin(gt * sp + ph)
            disque(c, x, y, sz * 1.5, (1, 1, 1), .85, .3, .2)
        elif kind == "lucioles":
            x = x0 + 60 * math.sin(gt * .6 * sp + ph); y = 250 + y0 * 1300 + 50 * math.cos(gt * .5 * sp + ph)
            disque(c, x, y, sz * 3, (1, .95, .5), max(0, .25 + .7 * math.sin(gt * 2.2 * sp + ph)), 0, .1)
        elif kind == "poussiere":
            x = (x0 + gt * sp * 70) % W; y = 200 + y0 * 1500 + 15 * math.sin(gt + ph)
            disque(c, x, y, sz * 1.1, (1, .9, .65), .45, 0, .2)
        elif kind == "etincelles":
            a = max(0, math.sin(gt * 2.5 * sp + ph)); y = 160 + y0 * 1650
            if a > .05: etoile4(c, x0, y, sz * 2.4 * a + 1, (1, 1, 1), .95 * a)
        elif kind == "bulles":
            y = ly + 140 - ((y0 * 1500 + gt * sp * 90) % 1500); x = x0 + 22 * math.sin(gt * sp + ph)
            if y < 130 or y > ly - 10: continue
            c.new_path(); c.arc(x, y, sz * 1.6, 0, 6.28); c.set_source_rgba(1, 1, 1, .55); c.set_line_width(1.8); c.stroke()


def liquide(c, nom, ly, gt, P_=None):
    P = DECOR[nom]; L = P["liq"]
    wave = lambda x, ph=0: ly + 7 * math.sin(x / 40 + gt * 5 + ph) + 3 * math.sin(x / 13 - gt * 7 + ph)
    pts = [(x, wave(x)) for x in range(0, W + 1, 12)]
    # lueur qui déborde sur la scène
    c.new_path(); c.move_to(0, ly - 230)
    for p in pts: c.line_to(p[0], p[1] - 230 + 230 * 0)
    for p in reversed(pts): c.line_to(*p)
    c.close_path()
    c.set_source(vgrad(c, 0, ly - 230, 0, ly, [(0, L["glow"], 0), (1, L["glow"], .42)])); c.fill()
    # vague arrière (plus claire)
    back = [(x, wave(x, 1.7) - 12) for x in range(0, W + 1, 12)]
    c.new_path(); c.move_to(*back[0])
    for p in back[1:]: c.line_to(*p)
    c.line_to(W, H); c.line_to(0, H); c.close_path()
    c.set_source_rgba(*L["top"], .55); c.fill()
    # corps
    c.new_path(); c.move_to(*pts[0])
    for p in pts[1:]: c.line_to(*p)
    c.line_to(W, H); c.line_to(0, H); c.close_path()
    c.set_source(vgrad(c, 0, ly - 8, 0, H, [(0, L["top"], .96), (.07, L["mid"], .94), (.45, L["mid"], .93), (1, L["deep"], .96)])); c.fill_preserve()
    c.save(); c.clip()
    for k in range(5):                                               # caustiques : bandes de lumière qui glissent
        cx = (k * 260 + gt * 38) % (W + 400) - 200
        c.save(); c.translate(cx, ly + 90 + 40 * math.sin(gt + k)); c.rotate(-.5); c.scale(1, .14)
        c.new_path(); c.arc(0, 0, 210, 0, 6.28); c.restore()
        c.set_source_rgba(*L["top"], .20); c.fill()
    if P.get("crust"):                                               # croûte sombre qui flotte (lave, métal en fusion)
        for k in range(9):
            cx = (k * 150 + gt * 14) % (W + 260) - 130; cy = ly + 30 + (k % 3) * 46
            c.save(); c.translate(cx, cy); c.scale(1, .32); c.new_path(); c.arc(0, 0, 58 + (k % 4) * 14, 0, 6.28); c.restore()
            c.set_source_rgba(*_shade(L["deep"], .55), .78); c.fill()
    c.restore()
    for k in range(12):                                              # bulles dans le liquide
        bx = (k * 91 + 37) % (W - 80) + 40
        by = H - ((k * 211 + gt * (50 + k * 9)) % max(H - ly, 1))
        if by < ly + 14: continue
        c.new_path(); c.arc(bx + 8 * math.sin(gt * 2 + k), by, 5 + (k % 4) * 3, 0, 6.28)
        c.set_source_rgba(*L["top"], .55); c.set_line_width(2.2); c.stroke()
    c.new_path(); c.move_to(*pts[0])                                 # écume
    for p in pts[1:]: c.line_to(*p)
    c.set_source_rgba(1, 1, 1, .85); c.set_line_width(11); c.stroke_preserve()
    c.set_source_rgba(*L["top"], 1); c.set_line_width(7); c.stroke()
    for k in range(22):
        x = (k * 53 + 17) % W
        disque(c, x, wave(x) - 6 + 4 * math.sin(gt * 3 + k), 5 + k % 3 * 2, (1, 1, 1), .9, .3, .3)


def dessiner_jeu(c, nom, walls, ly, gt, graine=0):
    c.set_source_surface(fond(nom, walls, graine)); c.paint()
    particules(c, nom, gt, ly or 1880)
