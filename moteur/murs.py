"""Mode « Duel de murs » — un vrai jeu de plateau à deux, joué par deux IA, jamais truqué (tout dépend de la graine).
Règles : grille de 7 × 9 cases. A part du bas et doit atteindre la rangée du haut ; B part du haut et doit atteindre le bas.
À son tour, chacun AVANCE d'une case (saut par-dessus l'autre s'il est collé) OU POSE un mur de sa couleur (2 cases de long).
Un mur ne peut ni chevaucher ni croiser un autre mur, et il doit toujours rester un chemin à chacun. 4 murs par joueur.
Histoires repérées dans les vraies parties : photo (gagné d'un seul pas), retournement (le perdant menait), piege (un mur
rallonge le chemin de l'autre d'au moins 4 cases), domination (le perdant est enfermé sous les murs)."""
import math, random
from collections import deque

COLS, ROWS, MURS = 7, 9, 4
CELL = 132
BX, BY = (1080 - COLS * CELL) // 2, 520            # coin haut-gauche du plateau à l'écran
T_PAS, T_MUR = .30, .45                             # durée d'un coup (vitesse réelle du jeu : jamais de ralenti)
BUT = (0, ROWS - 1)                                 # rangée à atteindre pour A (0) et B (1)
DEPART = ((COLS // 2, ROWS - 1), (COLS // 2, 0))
HISTOIRES = ("photo", "retournement", "piege", "domination")


# ------------------------------------------------------------------ plateau
def bloque(murs):
    """Ensemble des passages fermés entre deux cases voisines."""
    b = set()
    for o, x, y in murs:
        if o == "H":
            for xx in (x, x + 1):
                b.add(((xx, y - 1), (xx, y))); b.add(((xx, y), (xx, y - 1)))
        else:
            for yy in (y, y + 1):
                b.add(((x - 1, yy), (x, yy))); b.add(((x, yy), (x - 1, yy)))
    return b


def voisins(c, fermes):
    x, y = c
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        n = (x + dx, y + dy)
        if 0 <= n[0] < COLS and 0 <= n[1] < ROWS and (c, n) not in fermes:
            yield n


def distance(c, but, fermes):
    """Plus court chemin (en coups) jusqu'à la rangée du but ; None si enfermé."""
    vu, f = {c: 0}, deque([c])
    while f:
        a = f.popleft()
        if a[1] == but:
            return vu[a]
        for n in voisins(a, fermes):
            if n not in vu:
                vu[n] = vu[a] + 1; f.append(n)
    return None


def chemin(c, but, fermes):
    prec, f = {c: None}, deque([c])
    while f:
        a = f.popleft()
        if a[1] == but:
            out = []
            while a is not None:
                out.append(a); a = prec[a]
            return out[::-1]
        for n in voisins(a, fermes):
            if n not in prec:
                prec[n] = a; f.append(n)
    return [c]


def mur_valide(m, murs):
    o, x, y = m
    if o == "H" and not (0 <= x <= COLS - 2 and 1 <= y <= ROWS - 1):
        return False
    if o == "V" and not (1 <= x <= COLS - 1 and 0 <= y <= ROWS - 2):
        return False
    if m in murs:
        return False
    if o == "H":
        conflits = {("H", x - 1, y), ("H", x + 1, y), ("V", x + 1, y - 1)}
    else:
        conflits = {("V", x, y - 1), ("V", x, y + 1), ("H", x - 1, y + 1)}
    return not (conflits & murs)


def murs_sur_chemin(path):
    """Murs candidats : ceux qui coupent les premiers pas du plus court chemin de l'adversaire."""
    out = []
    for a, b in list(zip(path, path[1:]))[:5]:
        if a[0] == b[0]:                                   # pas vertical -> mur horizontal
            y = max(a[1], b[1])
            out += [("H", a[0], y), ("H", a[0] - 1, y)]
        else:                                              # pas horizontal -> mur vertical
            x = max(a[0], b[0])
            out += [("V", x, a[1]), ("V", x, a[1] - 1)]
    return out


# ------------------------------------------------------------------ IA
def coups(pions, murs, reste, j):
    """Tous les coups utiles du joueur j : déplacements + murs qui gênent l'autre."""
    fermes, moi, lui = bloque(murs), pions[j], pions[1 - j]
    out = []
    for n in voisins(moi, fermes):
        if n == lui:                                       # saut par-dessus l'adversaire, tout droit
            s = (2 * n[0] - moi[0], 2 * n[1] - moi[1])
            if 0 <= s[0] < COLS and 0 <= s[1] < ROWS and (n, s) not in fermes:
                out.append(("pas", s))
            else:                                          # saut bloqué : on passe en diagonale à côté de l'autre
                out += [("pas", d) for d in voisins(n, fermes) if d != moi and d != s]
        else:
            out.append(("pas", n))
    if reste[j] > 0:
        for m in murs_sur_chemin(chemin(lui, BUT[1 - j], fermes)):
            if mur_valide(m, murs):
                f2 = bloque(murs | {m})
                if distance(moi, BUT[j], f2) is not None and distance(lui, BUT[1 - j], f2) is not None:
                    out.append(("mur", m))
    return out


def choisir(pions, murs, reste, j, rnd, talent):
    """Coup d'une IA de niveau `talent` (0..1) : écart de chemins, coût d'un mur, un peu d'imprévu (bruit)."""
    meilleurs, bruit = [], .25 + (1 - talent) * 1.1
    for k, a in coups(pions, murs, reste, j):
        p2, m2 = list(pions), set(murs)
        if k == "pas":
            p2[j] = a
        else:
            m2.add(a)
        f2 = bloque(m2)
        dm, dl = distance(p2[j], BUT[j], f2), distance(p2[1 - j], BUT[1 - j], f2)
        if dm == 0:
            return k, a                                    # victoire immédiate
        score = dl - dm
        if k == "mur":
            d0 = distance(pions[1 - j], BUT[1 - j], bloque(murs))
            gain = dl - d0
            if gain < 1:
                continue                                   # un mur qui ne gêne pas ne sert à rien
            score += .15 - (MURS - reste[j]) * .08         # un mur coûte un tour ; les derniers sont un peu plus précieux
            if dm >= d0:
                score += .7                                # on est derrière ou à égalité : c'est le moment de bloquer
            if dl <= 3:
                score += 1.2                               # l'autre est presque arrivé
        meilleurs.append((score + rnd.gauss(0, bruit if k == "mur" else bruit * .35), k, a))
    meilleurs.sort(key=lambda s: -s[0])
    return meilleurs[0][1], meilleurs[0][2]


# ------------------------------------------------------------------ partie
def simulate(seed, max_coups=64):
    rnd = random.Random(seed)
    talents = (rnd.uniform(.35, 1.0), rnd.uniform(.35, 1.0))
    pions, murs, reste = list(DEPART), set(), [MURS, MURS]
    j, t, plis, gagnant = rnd.randrange(2), 0.0, [], None
    for _ in range(max_coups):
        avant = list(pions)
        k, a = choisir(pions, murs, reste, j, rnd, talents[j])
        d_av = distance(pions[1 - j], BUT[1 - j], bloque(murs))
        if k == "pas":
            pions[j] = a
        else:
            murs.add(a); reste[j] -= 1
        f = bloque(murs)
        d = (distance(pions[0], BUT[0], f), distance(pions[1], BUT[1], f))
        dur = T_PAS if k == "pas" else T_MUR
        plis.append(dict(t=t, dur=dur, j=j, k=k, a=a, avant=avant, apres=list(pions), murs=sorted(murs),
                         reste=list(reste), d=d, gain=(d[1 - j] - d_av) if k == "mur" else 0))
        t += dur
        if pions[j][1] == BUT[j]:
            gagnant = j
            break
        j = 1 - j
    hits = [(p["t"] + (p["dur"] * .8 if p["k"] == "pas" else p["dur"] * .7), p["j"], p["k"]) for p in plis]
    return dict(mode="murs", seed=seed, plis=plis, gagnant=gagnant, talents=talents, t_fin=t, hits=hits, frames=None)


def detecter(S, histoire):
    """Renvoie l'événement si la partie raconte vraiment `histoire` (et tient dans le temps), sinon None."""
    g, P = S["gagnant"], S["plis"]
    if g is None or not (10 <= S["t_fin"] <= 19) or len(P) < 14:
        return None
    p = 1 - g
    d_fin_perdant = P[-1]["d"][p]
    murs_g = [x for x in P if x["j"] == g and x["k"] == "mur"]
    gros = max(murs_g, key=lambda x: x["gain"], default=None)
    # moment clé : le plus gros mur du gagnant (sinon les 2/3 de la partie)
    t_cle = gros["t"] + gros["dur"] if gros and gros["gain"] >= 3 else P[len(P) * 2 // 3]["t"]
    ev = dict(hero=g, rival=p, histoire=histoire, t_cle=t_cle, t_fin=S["t_fin"], d_perdant=d_fin_perdant,
              murs=len([x for x in P if x["k"] == "mur"]))
    if histoire == "photo":
        return ev if d_fin_perdant == 1 and ev["murs"] >= 3 else None
    if histoire == "retournement":
        menait = [x for x in P[6:-4] if x["d"][p] + 2 <= x["d"][g]]
        return ev if menait and d_fin_perdant <= 3 else None
    if histoire == "piege":
        return ev if gros and gros["gain"] >= 4 and d_fin_perdant >= 2 else None
    if histoire == "domination":
        recu = sum(x["gain"] for x in murs_g)
        menait = any(x["d"][p] < x["d"][g] for x in P[4:])
        return ev if recu >= 9 and not menait and d_fin_perdant >= 4 else None
    return None


def tension(S, t):
    """0..1 : la course est-elle serrée et proche de l'arrivée ?"""
    P = S["plis"]
    x = next((q for q in reversed(P) if q["t"] <= t), P[0])
    da, db = x["d"]
    return max(0.0, min(1.0, .55 * (1 - min(da, db) / 8) + .45 * (1 - min(abs(da - db), 6) / 6)))


# ------------------------------------------------------------------ rendu
LOOKS = dict(
    nuit=dict(fond=((.03, .04, .09), (.07, .08, .17)), plateau=(.10, .13, .25), grille=(.20, .25, .42), bord=(.30, .36, .58)),
    papier=dict(fond=((.90, .92, .96), (.80, .84, .91)), plateau=(.97, .98, 1.0), grille=(.82, .86, .92), bord=(.66, .72, .82)),
    ardoise=dict(fond=((.05, .10, .08), (.10, .18, .15)), plateau=(.13, .22, .19), grille=(.22, .34, .30), bord=(.40, .52, .46)),
    sable=dict(fond=((.95, .89, .78), (.86, .76, .60)), plateau=(.99, .95, .87), grille=(.88, .80, .66), bord=(.72, .60, .42)),
)


def _xy(c):
    return BX + (c[0] + .5) * CELL, BY + (c[1] + .5) * CELL


def _ease(u):
    return u * u * (3 - 2 * u)


def _rrect(c, x, y, w, h, r):
    c.new_sub_path()
    for cx, cy, a in ((x + w - r, y + r, -math.pi / 2), (x + w - r, y + h - r, 0), (x + r, y + h - r, math.pi / 2), (x + r, y + r, math.pi)):
        c.arc(cx, cy, r, a, a + math.pi / 2)
    c.close_path()


def _mur(c, m, col, p=1.0):
    o, x, y = m
    if o == "H":
        x0, y0, x1, y1 = BX + x * CELL + 8, BY + y * CELL, BX + (x + 2) * CELL - 8, BY + y * CELL
    else:
        x0, y0, x1, y1 = BX + x * CELL, BY + y * CELL + 8, BX + x * CELL, BY + (y + 2) * CELL - 8
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    x0, y0, x1, y1 = mx + (x0 - mx) * p, my + (y0 - my) * p, mx + (x1 - mx) * p, my + (y1 - my) * p
    c.set_line_cap(1)
    for w, a in ((34, .18), (22, .35)):                   # lueur
        c.set_source_rgba(*col, a); c.set_line_width(w); c.move_to(x0, y0); c.line_to(x1, y1); c.stroke()
    c.set_source_rgb(*col); c.set_line_width(13); c.move_to(x0, y0); c.line_to(x1, y1); c.stroke()
    c.set_source_rgba(1, 1, 1, .45); c.set_line_width(4); c.move_to(x0, y0 - 2); c.line_to(x1, y1 - 2); c.stroke()


def _pion(c, kind, col, x, y, s=40, ang=0.0, verts=None):
    c.save(); c.translate(x, y + 7); c.rotate(ang)
    c.set_source_rgba(0, 0, 0, .25)
    _forme(c, kind, s, verts); c.fill()
    c.restore()
    c.save(); c.translate(x, y); c.rotate(ang)
    _forme(c, kind, s, verts)
    c.set_source_rgb(*col); c.fill_preserve()
    c.set_source_rgba(0, 0, 0, .35); c.set_line_width(4); c.stroke()
    c.restore()


def _forme(c, kind, s, verts):
    if kind == "circle":
        c.arc(0, 0, s, 0, 2 * math.pi)
        return
    vs = verts(kind, s)
    c.move_to(*vs[0])
    for v in vs[1:]:
        c.line_to(*v)
    c.close_path()


def dessiner(c, S, gt, look, joueurs, verts):
    """joueurs : ((forme, couleur), (forme, couleur)) pour A et B. Le plateau ne porte aucun texte ni visage (jeu neutre)."""
    L = LOOKS[look]
    W, H = 1080, 1920
    import cairo
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *L["fond"][0]); g.add_color_stop_rgb(1, *L["fond"][1])
    c.set_source(g); c.paint()
    bw, bh = COLS * CELL, ROWS * CELL
    _rrect(c, BX - 26, BY - 26, bw + 52, bh + 52, 34)
    c.set_source_rgb(*L["bord"]); c.fill()
    _rrect(c, BX - 12, BY - 12, bw + 24, bh + 24, 24)
    c.set_source_rgb(*L["plateau"]); c.fill()
    for j, ligne in ((0, 0), (1, ROWS - 1)):              # rangées d'arrivée teintées de la couleur de celui qui doit les atteindre
        col = joueurs[j][1]
        c.set_source_rgba(*col, .16); c.rectangle(BX, BY + ligne * CELL, bw, CELL); c.fill()
        yb = BY - 50 if ligne == 0 else BY + bh + 50
        c.set_source_rgba(*col, .9); c.set_line_width(8); c.set_line_cap(1)
        c.move_to(BX + bw * .25, yb); c.line_to(BX + bw * .75, yb); c.stroke()
    c.set_source_rgb(*L["grille"]); c.set_line_width(2)
    for i in range(1, COLS):
        c.move_to(BX + i * CELL, BY); c.line_to(BX + i * CELL, BY + bh)
    for i in range(1, ROWS):
        c.move_to(BX, BY + i * CELL); c.line_to(BX + bw, BY + i * CELL)
    c.stroke()
    P = S["plis"]
    k = 0
    while k + 1 < len(P) and P[k + 1]["t"] <= gt:
        k += 1
    q = P[k]
    u = max(0.0, min(1.0, (gt - q["t"]) / q["dur"])) if gt >= q["t"] else 0.0
    murs_avant = set(P[k - 1]["murs"]) if k > 0 else set()
    proprio = {x["a"]: x["j"] for x in P if x["k"] == "mur"}
    for m in sorted(murs_avant):                          # ordre fixe : même numéro = même vidéo, au pixel près
        _mur(c, m, joueurs[proprio[m]][1])
    if q["k"] == "mur" and gt >= q["t"]:
        _mur(c, q["a"], joueurs[q["j"]][1], _ease(min(1, u / .6)))
        if .55 < u < .8:                                   # petit éclair à la pose
            c.set_source_rgba(1, 1, 1, .25 * (1 - abs(u - .67) / .13)); c.paint()
    # murs restants : petits traits sous chaque camp
    reste = P[k - 1]["reste"] if k > 0 else [MURS, MURS]
    for j in (0, 1):
        y = BY + bh + 95 if j == 0 else BY - 95
        for i in range(reste[j]):
            x = 540 + (i - (MURS - 1) / 2) * 56
            c.set_source_rgb(*joueurs[j][1]); c.set_line_width(10); c.set_line_cap(1)
            c.move_to(x - 18, y); c.line_to(x + 18, y); c.stroke()
    for j in (0, 1):
        a, b = q["avant"][j], q["apres"][j]
        if gt < q["t"]:
            b = a
        ax, ay = _xy(a); bx, by = _xy(b)
        e = _ease(u) if q["k"] == "pas" and q["j"] == j else (1.0 if b != a else 0.0)
        x, y = ax + (bx - ax) * e, ay + (by - ay) * e
        hop = math.sin(math.pi * e) * 26 if q["k"] == "pas" and q["j"] == j else 0
        s = 40 * (1 + .12 * math.sin(math.pi * e))
        fini = S["gagnant"] == j and gt >= S["t_fin"]
        if fini:                                           # le gagnant brille sur la ligne d'arrivée
            r = 60 + 40 * ((gt - S["t_fin"]) * 2 % 1)
            c.set_source_rgba(*joueurs[j][1], .35 * (1 - (gt - S["t_fin"]) * 2 % 1)); c.arc(x, y, r, 0, 2 * math.pi); c.fill()
        _pion(c, joueurs[j][0], joueurs[j][1], x, y - hop, s, 0.0, verts)
