"""Planches manga génériques : le héros peut être n'importe quel animal du pack, le liquide prend la couleur du décor.
Mêmes règles que la recette v6 : traits de couleur, pas de mains, pas de titres, texte en anglais."""
import math
import random
import animaux, effets
from dessin import (W, H, INK, WHITE, R, poly, ink, hatch, halftone, focus, text, bubble_oval, bubble_burst,
                    frame, page, layer, FR)


def _mix(a, b, k):
    return tuple(a[i] * (1 - k) + b[i] * k for i in range(3))


def liquide(c, top, th, amp=16):
    base = _mix(th["liqtop"], (1, 1, 1), .75)
    dark = tuple(q * .5 for q in th["liq"])
    wave = [(x, top + amp * math.sin(x / 50) + amp * .4 * math.sin(x / 15)) for x in range(0, W + 1, 10)]
    mk = lambda: poly(c, wave + [(W, H), (0, H)])
    mk(); c.set_source_rgb(*base); c.fill()
    hatch(c, mk, math.radians(-15), 9, 3.6, th["liq"])
    hatch(c, mk, math.radians(65), 15, 2.8, dark, .8)
    poly(c, wave, False); ink(c, 8); c.stroke()
    for _ in range(12):
        bx, by, r = R.uniform(80, W - 80), R.uniform(top + 30, top + 240), R.uniform(6, 18)
        c.new_path(); c.arc(bx, by, r, 0, 6.3); ink(c, 4, _mix(th["liqtop"], (1, 1, 1), .5)); c.stroke()


def fantome(c, kind, x, y, s, col):
    """Un ami disparu, en fantôme lumineux dans le ciel."""
    c.save(); c.translate(x, y)
    if kind == "square":
        mk = lambda: c.rectangle(-s, -s, 2 * s, 2 * s)
    elif kind == "circle":
        mk = lambda: (c.new_path(), c.arc(0, 0, s, 0, 6.3))
    elif kind == "diamond":
        mk = lambda: poly(c, [(0, -s * 1.2), (s, 0), (0, s * 1.2), (-s, 0)])
    else:
        mk = lambda: poly(c, [(0, -s * 1.15), (s * 1.1, s * .8), (-s * 1.1, s * .8)])
    for r in range(4, 0, -1):
        c.save(); c.scale(1 + r * .12, 1 + r * .12); mk(); c.set_source_rgba(1, 1, .85, .12); c.fill(); c.restore()
    mk(); c.set_source_rgb(*WHITE); c.fill()
    hatch(c, mk, math.radians(40), 8, 2.8, col, .55)
    mk(); ink(c, 4, INK, .5); c.stroke()
    for sx in (-1, 1):
        c.new_path(); c.arc(sx * s * .35, -s * .1, s * .18, math.radians(200), math.radians(340)); ink(c, 3.5, INK, .7); c.stroke()
    c.restore()


def _couper(rep, seuil=11):
    """Une seule longue ligne est coupée en deux lignes équilibrées, pour garder un gros lettrage."""
    lines = rep.split("\n")
    if len(lines) == 1 and len(rep) > seuil and " " in rep:
        mots, best = rep.split(" "), None
        for k in range(1, len(mots)):
            a, b = " ".join(mots[:k]), " ".join(mots[k:])
            if best is None or max(len(a), len(b)) < max(len(x) for x in best):
                best = (a, b)
        lines = list(best)
    return lines


def _lignes(rep, base, rx):
    """Découpe une réplique en lignes et choisit une taille de police qui tient dans la bulle."""
    lines = _couper(rep)
    n = max(len(l) for l in lines)
    size = int(min(base, 2 * rx * .80 / (.52 * max(n, 1))))
    return [(l.upper(), size) for l in lines]


def _bulle_oval_lignes(rep, rx):
    lines = _couper(rep, 20)
    n = max(len(l) for l in lines)
    return lines, int(min(74, 2 * rx * .80 / (.5 * max(n, 1))))


def p_notyou(heros, col, th, rep, fond="pluie", graine=1):
    s, c = page()
    c.save(); poly(c, FR); c.clip()
    effets.FONDS[fond](c, col, random.Random(graine))
    animaux.dessiner(heros, c, 540, 1120, 760, math.radians(4), "crying", col, look=(0, .3), tear_len=330)
    onomatopee_fond(c, fond, graine, 1680)
    c.restore(); frame(c, FR)
    b, cb = layer()
    bubble_burst(cb, 540, 300, 400, 150, _lignes(rep, 120, 400), 120)
    return s, [(b, .2, (540, 300))]


def p_notdone(heros, col, th, rep, fond="aura", graine=2, larmes=120):
    s, c = page()
    c.save(); poly(c, FR); c.clip()
    effets.FONDS[fond](c, col, random.Random(graine))
    animaux.dessiner(heros, c, 540, 1000, 780, math.radians(-4), "fierce", col, tear_len=larmes)
    onomatopee_fond(c, fond, graine, 1700)
    c.restore(); frame(c, FR)
    b, cb = layer()
    bubble_burst(cb, 540, 280, 420, 150, _lignes(rep, 140, 420), 140, (.85, .1, .05))
    return s, [(b, .12, (540, 280))]


def p_forall(heros, col, th, rep, amis, fond="aube", graine=3):
    """amis : liste de trois (forme, couleur) des formes tombées."""
    s, c = page()
    c.save(); poly(c, FR); c.clip()
    effets.FONDS[fond](c, col, random.Random(graine))
    for (nom_a, fc), (gx, gy) in zip(amis, ((230, 340), (540, 240), (850, 340))):
        fantome_animal(c, nom_a, gx, gy, 190, fc)
    if fond not in ("plumes", "etoiles") and "liqtop" in th:
        liquide(c, 1640, th)
    animaux.dessiner(heros, c, 540, 1000, 560, 0, "sad_smile", col)
    c.restore(); frame(c, FR)
    b, cb = layer()
    lines, size = _bulle_oval_lignes(rep, 330)
    bubble_oval(cb, 540, 1430, 330, 95, (560, 1290), lines, size)
    return s, [(b, .5, (540, 1430))]


def _coupe(phrase, maxc=20):
    mots, lignes, cur = phrase.split(), [], ""
    for m in mots:
        if cur and len(cur) + 1 + len(m) > maxc:
            lignes.append(cur); cur = m
        else:
            cur = (cur + " " + m).strip()
    lignes.append(cur)
    return lignes


def p_card(morale, fond="aube", graine=4):
    s, c = page()
    t, ct = layer()
    effets.FONDS[fond](ct, (.9, .3, .3), random.Random(graine))
    c.set_source_surface(t); c.paint_with_alpha(.20)
    lignes = _coupe(morale.upper(), 18)
    size = 112 if len(lignes) <= 3 else 92
    y0 = 760 - (len(lignes) - 1) * size * .55
    for i, l in enumerate(lignes):
        text(c, l, "Bangers", size, 540, y0 + i * size * 1.1)
    text(c, "EVERY SHAPE HAS A STORY.", "Comic Neue", 54, 540, 1130)
    b, cb = layer()
    text(cb, "FOLLOW  >", "Bangers", 130, 540, 1330, (.85, .1, .1), INK, 9)
    return s, [(b, .25, (540, 1330))]


# ------------------------------------------------------------------ lettrage à la main, cases, nouvelles planches
SFX = dict(vitre=["KRAAAK!", "CRASH!"], eclair=["ZZZAKK!", "KRA-KOOM!"], aura=["GOOOOO!", "FWOOOSH!"], onde=["DOOOON!", "BADOOM!"],
           explosion=["BOOOOM!", "KABOOM!"], vitesse=["ZOOOOM!", "DOOO!"], pluie=["...", "DRIP...", "PLIP..."])
COUL_SFX = dict(vitre=(.75, .9, 1), eclair=(1, .95, .4), aura=(1, .85, .2), onde=(1, 1, .9), explosion=(1, .95, .4), vitesse=(.95, .15, .15), pluie=(.85, .92, 1))


def onomatopee(c, txt, x, y, size, rot, col, graine):
    """Lettrage « fait main » : chaque lettre est un peu décalée, penchée, et de taille différente."""
    rr = random.Random(graine)
    c.save(); c.translate(x, y); c.rotate(rot)
    c.select_font_face("Bangers")
    c.set_font_size(size)
    largeur = sum(c.text_extents(ch).x_advance for ch in txt)
    xx = -largeur / 2
    for ch in txt:
        c.set_font_size(size * rr.uniform(.88, 1.14))
        e = c.text_extents(ch)
        c.save(); c.translate(xx + e.x_advance / 2, rr.uniform(-.08, .08) * size); c.rotate(rr.uniform(-.14, .14))
        c.move_to(-e.width / 2 - e.x_bearing, e.height / 2); c.text_path(ch)
        c.set_source_rgb(*INK); c.set_line_width(size * .16); c.set_line_join(1); c.stroke_preserve()
        c.set_source_rgb(*col); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(2.5); c.stroke()
        c.restore(); xx += e.x_advance * 1.02
    c.restore()


def onomatopee_fond(c, fond, graine, y):
    if fond in SFX:
        rr = random.Random(graine + 5)
        onomatopee(c, rr.choice(SFX[fond]), 540 + rr.uniform(-90, 90), y, rr.uniform(150, 190), rr.uniform(-.12, .12), COUL_SFX[fond], graine)


def case_legende(c, txt, x, y, largeur=720, taille=50, rot=-.03):
    """Case de narration jaune (comme un récitatif de manga)."""
    mots, lignes, cur = txt.split(), [], ""
    for m in mots:
        if cur and len(cur) + 1 + len(m) > int(largeur / (taille * .52)):
            lignes.append(cur); cur = m
        else:
            cur = (cur + " " + m).strip()
    lignes.append(cur)
    h = len(lignes) * taille * 1.25 + 40
    c.save(); c.translate(x, y); c.rotate(rot)
    c.rectangle(-largeur / 2 + 8, -h / 2 + 8, largeur, h); c.set_source_rgba(0, 0, 0, .35); c.fill()
    c.rectangle(-largeur / 2, -h / 2, largeur, h); c.set_source_rgb(1, .94, .62); c.fill_preserve(); ink(c, 6); c.stroke()
    for i, l in enumerate(lignes):
        text(c, l, "Comic Neue", taille, 0, -h / 2 + 20 + taille * .65 + i * taille * 1.25)
    c.restore()


def fantome_animal(c, nom, x, y, s, col):
    """Un ami disparu : son animal, translucide, auréolé de lumière."""
    _glow_c = lambda r, a: None
    c.push_group()
    animaux.dessiner(nom, c, x, y, s, 0, "serene", col)
    c.pop_group_to_source(); c.paint_with_alpha(.62)


def _case(c, pts, fn, dy=0):
    c.save(); poly(c, pts); c.clip(); c.translate(0, dy); fn(); c.restore(); frame(c, pts)


def p_intro(noms, cols, th, cadre, fond="aube", graine=1):
    """Ouverture : les quatre amis, côte à côte, avant que le liquide ne monte."""
    s, c = page()
    rr = random.Random(graine)
    c.save(); poly(c, FR); c.clip()
    effets.FONDS[fond](c, cols[0], random.Random(graine))
    pos = [(310, 720), (770, 660), (310, 1290), (770, 1230)]
    for (nom, col, (x, y)) in zip(noms, cols, pos):
        animaux.dessiner(nom, c, x, y, 400, math.radians(rr.uniform(-7, 7)), "determined", col, look=(rr.uniform(-.3, .3), -.2))
    c.restore(); frame(c, FR)
    case_legende(c, cadre, 540, 245, 760, 56)
    return s, []


def p_espoir(heros, col, th, rep, fond="aube", graine=2):
    s, c = page()
    c.save(); poly(c, FR); c.clip()
    effets.FONDS[fond](c, col, random.Random(graine))
    animaux.dessiner(heros, c, 540, 1120, 700, math.radians(-3), "determined", col, look=(0, -.9))
    c.restore(); frame(c, FR)
    b, cb = layer()
    lines, size = _bulle_oval_lignes(rep, 360)
    bubble_oval(cb, 540, 310, 360, 120, (540, 640), lines, size)
    return s, [(b, .25, (540, 310))]


def p_presque(heros, col, th, rep, fond="vitre", graine=3):
    s, c = page()
    c.save(); poly(c, FR); c.clip()
    effets.FONDS[fond](c, col, random.Random(graine))
    animaux.dessiner(heros, c, 540, 1100, 780, math.radians(5), "crying", col, look=(0, -.6), tear_len=360)
    onomatopee_fond(c, fond, graine, 1700)
    c.restore(); frame(c, FR)
    b, cb = layer()
    bubble_burst(cb, 540, 300, 420, 150, _lignes(rep, 125, 420), 125)
    return s, [(b, .2, (540, 300))]


def p_adieu(heros, col, th, rep, amis, fond="coucher", graine=4):
    s, c = page()
    c.save(); poly(c, FR); c.clip()
    effets.FONDS[fond](c, col, random.Random(graine))
    for (nom_a, fc), (gx, gy) in zip(amis, ((230, 340), (540, 240), (850, 340))):
        fantome_animal(c, nom_a, gx, gy, 190, fc)
    animaux.dessiner(heros, c, 540, 1060, 600, 0, "sad_smile", col)
    c.restore(); frame(c, FR)
    b, cb = layer()
    lines, size = _bulle_oval_lignes(rep, 340)
    bubble_oval(cb, 540, 1470, 340, 100, (560, 1330), lines, size)
    return s, [(b, .5, (540, 1470))]


def p_duel(heros, hcol, rival, rcol, th, rep_h, rep_r, fond="eclair", graine=5, eh="fierce", er="fierce"):
    """Page coupée en diagonale : le rival en haut, le héros en bas."""
    s, c = page()
    haut = [(40, 60), (1040, 60), (1040, 800), (40, 1010)]
    bas = [(40, 1050), (1040, 840), (1040, 1860), (40, 1860)]
    _case(c, haut, lambda: (effets.FONDS[fond](c, rcol, random.Random(graine)),
                            animaux.dessiner(rival, c, 560, 800, 600, math.radians(7), er, rcol)), -300)
    _case(c, bas, lambda: (effets.FONDS[fond](c, hcol, random.Random(graine + 1)),
                           animaux.dessiner(heros, c, 520, 960, 640, math.radians(-7), eh, hcol)), 380)
    b, cb = layer()
    bubble_burst(cb, 650, 230, 300, 130, _lignes(rep_r, 110, 300), 110, (.8, .1, .1))
    bubble_burst(cb, 430, 1060, 300, 130, _lignes(rep_h, 110, 300), 110, (.1, .35, .85))
    return s, [(b, .3, (540, 600))]


def p_perdant(rival, rcol, th, rep, fond="pluie", graine=6):
    s, c = page()
    c.save(); poly(c, FR); c.clip()
    effets.FONDS[fond](c, rcol, random.Random(graine))
    animaux.dessiner(rival, c, 540, 1060, 640, math.radians(-4), "sad_smile", rcol, tear_len=260)
    c.restore(); frame(c, FR)
    b, cb = layer()
    lines, size = _bulle_oval_lignes(rep, 350)
    bubble_oval(cb, 540, 1480, 350, 100, (560, 1340), lines, size)
    return s, [(b, .45, (540, 1480))]


def p_union(noms, cols, th, rep, fond="soleil", graine=7):
    """Portrait de groupe : ceux qui sont sortis ensemble."""
    s, c = page()
    rr = random.Random(graine)
    c.save(); poly(c, FR); c.clip()
    effets.FONDS[fond](c, cols[0], random.Random(graine))
    n = len(noms)
    pos = {1: [(540, 1000)], 2: [(310, 1000), (770, 960)], 3: [(540, 620), (300, 1240), (780, 1240)],
           4: [(310, 700), (770, 660), (310, 1290), (770, 1250)]}[n]
    S = {1: 620, 2: 500, 3: 460, 4: 400}[n]
    for nom, col, (x, y) in zip(noms, cols, pos):
        animaux.dessiner(nom, c, x, y, S, math.radians(rr.uniform(-6, 6)), rr.choice(["serene", "sad_smile"]), col)
    c.restore(); frame(c, FR)
    b, cb = layer()
    lines, size = _bulle_oval_lignes(rep, 360)
    bubble_oval(cb, 540, 1620, 360, 105, (540, 1480), lines, size)
    return s, [(b, .5, (540, 1620))]
