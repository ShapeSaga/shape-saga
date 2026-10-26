"""Niveaux de jeu : 6 architectures différentes, générées à partir d'une graine.
Un niveau = liste de rectangles (x0, y0, x1, y1). Cadre extérieur + plafond avec une sortie (trou) en haut.
Les formes naissent en bas (y 1580-1830) : rien ne doit y être posé."""
import random

W, H = 1080, 1920
E = 36                                   # épaisseur des planchers


def _cadre(rr, largeur=None):
    larg = largeur or rr.choice([180, 200, 230])
    cx = rr.uniform(230, 850)
    g0, g1 = int(cx - larg / 2), int(cx + larg / 2)
    return [(0, 0, 40, H), (1040, 0, W, H), (0, 1880, W, H), (0, 120, g0, 156), (g1, 120, W, 156)], (g0, g1)


def _sol(y, trous, x0=40, x1=1040):
    """Plancher à l'altitude y avec des trous [(a, b), ...]."""
    out, x = [], x0
    for a, b in sorted(trous):
        if a - x > 20:
            out.append((x, y, a, y + E))
        x = b
    if x1 - x > 20:
        out.append((x, y, x1, y + E))
    return out


def etages(rr):
    mur, (g0, g1) = _cadre(rr)
    n = rr.choice([3, 4, 4, 5])
    ys = [1500 - i * (1500 - 360) / (n - 1) for i in range(n)]
    for i, y in enumerate(ys):
        w = rr.uniform(280, 400)
        cote = (i % 2 == 0)
        a = rr.uniform(700, 1040 - w) if cote else rr.uniform(40, 360)
        mur += _sol(int(y), [(int(a), int(a + w))])
    for _ in range(rr.randint(3, 6)):                                # petits blocs en l'air
        x, y = rr.uniform(120, 920), rr.uniform(260, 1420)
        if all(abs(y - yy) > 90 for yy in ys):
            mur.append((int(x), int(y), int(x) + rr.choice([40, 60, 80]), int(y) + rr.choice([40, 60])))
    return mur


def cheminee(rr):
    mur, (g0, g1) = _cadre(rr, 200)
    w = rr.uniform(340, 430); x0 = rr.uniform(240, 1040 - w - 240); x1 = x0 + w
    mur += _sol(1500, [(int(x0), int(x1))])
    mur += [(int(x0) - E, 300, int(x0), 1500), (int(x1), 300, int(x1) + E, 1500)]
    mur += _sol(300, [(int(x0), int(x1))], 40, 1040)[:0]
    k = rr.choice([4, 5])
    for i in range(k):
        y = 1370 - i * (1070 / (k - 1))
        lg = w * rr.uniform(.35, .5)
        if i % 2 == 0:
            mur.append((int(x0), int(y), int(x0 + lg), int(y) + 30))
        else:
            mur.append((int(x1 - lg), int(y), int(x1), int(y) + 30))
    # le plafond doit s'ouvrir au-dessus de la cheminée
    mur = [r for r in mur if not (r[1] == 120 and r[3] == 156)]
    gx = rr.uniform(x0 + 20, x1 - 220)
    mur += [(0, 120, int(gx), 156), (int(gx + 200), 120, W, 156)]
    return mur


def plinko(rr):
    mur, _ = _cadre(rr)
    x = int(rr.uniform(120, 640))
    mur += _sol(1500, [(x, x + 300)])
    pas = rr.uniform(150, 185)
    y, row = 1380, 0
    while y > 300:
        for i in range(7):
            x = 100 + i * 150 + (75 if row % 2 else 0)
            if x < 1000 and rr.random() > .13:
                s = rr.choice([44, 52, 60])
                mur.append((int(x), int(y), int(x) + s, int(y) + s))
        y -= pas; row += 1
    return mur


def labyrinthe(rr):
    mur, _ = _cadre(rr)
    n = rr.choice([3, 4])
    ys = [1500 - i * (1500 - 380) / (n - 1) for i in range(n)]
    for i, y in enumerate(ys):
        w = rr.uniform(300, 400)
        a = rr.uniform(720, 1040 - w) if i % 2 == 0 else rr.uniform(40, 320)
        mur += _sol(int(y), [(int(a), int(a + w))])
        if i:
            h = (ys[i - 1] - y) * rr.uniform(.35, .5)
            for xd in rr.sample([260, 460, 640, 800], 1):
                mur.append((xd, int(y + E), xd + 36, int(y + E + h)))
    return mur


def escaliers(rr):
    mur, _ = _cadre(rr)
    k = rr.choice([6, 7, 8]); sens = rr.choice([1, -1])
    for i in range(k):
        y = 1500 - i * (1140 / (k - 1))
        x = 50 + i * ((1040 - 50 - 300) / (k - 1)) if sens > 0 else 1040 - 300 - i * ((1040 - 50 - 300) / (k - 1))
        mur.append((int(x), int(y), int(x) + 300, int(y) + E))
    for _ in range(rr.randint(2, 4)):
        x, y = rr.uniform(100, 900), rr.uniform(300, 1400)
        mur.append((int(x), int(y), int(x) + 60, int(y) + 60))
    return mur


def piliers(rr):
    mur, _ = _cadre(rr)
    ys = [1500, 1090, 680]
    for i, y in enumerate(ys):
        ga = rr.uniform(120, 400); gb = rr.uniform(640, 900)
        mur += _sol(y, [(int(ga), int(ga) + 190), (int(gb), int(gb) + 190)])
        for _ in range(2):
            x = rr.uniform(120, 940)
            mur.append((int(x), int(y - rr.uniform(160, 260)), int(x) + 56, int(y)))
    return mur


ARCHI = dict(etages=etages, cheminee=cheminee, plinko=plinko, labyrinthe=labyrinthe, escaliers=escaliers, piliers=piliers)


def generer(nom, graine):
    return ARCHI[nom](random.Random(graine))
