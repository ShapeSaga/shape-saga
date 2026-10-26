"""Les trois histoires que le programme sait repérer dans une vraie course."""
import math
import sim

FPS = sim.FPS


def metriques(S):
    """Pour chaque forme : état, instant de fin, point le plus haut atteint, et sa position à chaque image."""
    fr = S["frames"]
    out = []
    for i in range(4):
        ys = [f[2][i][1] for f in fr if f[2][i][4] == "alive"]
        out.append(dict(etat=S["state"][i], t=S["t_end"][i], ymin=min(ys) if ys else 9999))
    return out


def _pos(S, i, t):
    fr = S["frames"][min(int(t * FPS), len(S["frames"]) - 1)]
    return fr[2][i][0], fr[2][i][1]


def dernier(S, tmax):
    st, te = S["state"], S["t_end"]
    esc = [i for i in range(4) if st[i] == "escaped"]
    if len(esc) != 1:
        return None
    h = esc[0]; tE = te[h]
    if any(st[i] != "caught" for i in range(4) if i != h) or tE < max(te) or tE > tmax:
        return None
    falls = sorted((te[i], i) for i in range(4) if i != h)
    if falls[0][0] < 2.5 or falls[1][0] - falls[0][0] < .4 or falls[2][0] - falls[1][0] < .4 or tE - falls[2][0] < .8:
        return None
    return dict(type="dernier", hero=h, t_fin=tE, falls=falls)


def presque(S, tmax):
    """Personne ne s'échappe. Le dernier à tomber avait presque atteint la sortie."""
    st, te = S["state"], S["t_end"]
    if any(s != "caught" for s in st):
        return None
    ordre = sorted((te[i], i) for i in range(4))
    t_h, h = ordre[-1]
    if t_h > tmax or t_h - ordre[-2][0] < .8 or ordre[0][0] < 2.5:
        return None
    m = metriques(S)[h]
    if m["ymin"] > 330:
        return None
    # instant où il a été le plus haut
    fr = S["frames"]
    t_top = min((f[0] for f in fr if f[2][h][4] == "alive" and abs(f[2][h][1] - m["ymin"]) < 1), default=t_h - 2)
    return dict(type="presque", hero=h, t_fin=t_h, t_top=t_top, ymin=m["ymin"], falls=ordre[:3])


def duel(S, tmax):
    """Photo-finish : un héros s'échappe, un rival qui le poursuivait de près tombe ou échoue juste derrière lui."""
    st, te = S["state"], S["t_end"]
    esc = [i for i in range(4) if st[i] == "escaped"]
    if not esc:
        return None
    h = min(esc, key=lambda i: te[i]); tE = te[h]
    if tE > tmax or tE < 8:
        return None
    for r in range(4):
        if r == h or st[r] != "caught" or te[r] - tE > 6:
            continue
        xh, yh = _pos(S, h, tE - .05)
        xr, yr = _pos(S, r, tE - .05)
        if yr - yh > 520:
            continue
        dmin = min(math.dist(_pos(S, h, t), _pos(S, r, t)) for t in [tE - 2.0 + .25 * k for k in range(9)])
        if dmin > 560:
            continue
        return dict(type="duel", hero=h, rival=r, t_fin=tE, t_rival=max(te[r], tE + .6), t_approche=max(2.5, tE - 4.0))
    return None


def _ly(S, t):
    return S["frames"][min(int(t * FPS), len(S["frames"]) - 1)][1]


def _vy(S, i, t):
    return S["frames"][min(int(t * FPS), len(S["frames"]) - 1)][2][i][3]


def sacrifice(S, tmax):
    """Un choc près du liquide propulse un ami vers le haut : il s'échappe, celui qui l'a aidé est englouti."""
    st, te = S["state"], S["t_end"]
    for t, a, b in S["hits"]:
        if a < 0 or b < 0 or t < 4:
            continue
        for g, r in ((a, b), (b, a)):
            if st[g] != "caught" or st[r] != "escaped" or te[r] > tmax:
                continue
            if not (.2 < te[g] - t <= 5) or te[r] < t or te[r] - t > 9:
                continue
            if _vy(S, r, t + .1) >= 0:
                continue
            ly = _ly(S, t)
            if ly is None or ly - _pos(S, g, t)[1] > 420:
                continue
            return dict(type="sacrifice", hero=g, ben=r, t_hit=t, t_fin=te[r], t_chute=te[g])
    return None


def trahison(S, tmax):
    """Un choc près du liquide pousse un ami vers le bas : lui s'échappe, l'autre est englouti."""
    st, te = S["state"], S["t_end"]
    for t, a, b in S["hits"]:
        if a < 0 or b < 0 or t < 4:
            continue
        for tr, vi in ((a, b), (b, a)):
            if st[tr] != "escaped" or st[vi] != "caught" or te[tr] > tmax:
                continue
            if not (.2 < te[vi] - t <= 3) or te[tr] < te[vi] - .5:
                continue
            if _vy(S, vi, t + .1) <= 0:
                continue
            ly = _ly(S, t)
            if ly is None or ly - _pos(S, vi, t)[1] > 320:
                continue
            return dict(type="trahison", hero=tr, rival=vi, t_hit=t, t_fin=te[tr])
    return None


def ensemble(S, tmax):
    """Au moins deux formes s'échappent à quelques secondes d'écart : la réussite est collective."""
    st, te = S["state"], S["t_end"]
    esc = sorted((te[i], i) for i in range(4) if st[i] == "escaped")
    if len(esc) < 2 or esc[-1][0] > tmax or esc[-1][0] - esc[0][0] > 8 or esc[0][0] < 6:
        return None
    return dict(type="ensemble", heros=[i for _, i in esc], hero=esc[0][1], t_premier=esc[0][0], t_fin=esc[-1][0])


def prison(S, tmax):
    """Un seul prisonnier sort : le dernier debout."""
    if S.get("mode") != "prison":
        return None
    st, te = S["state"], S["t_end"]
    esc = [i for i in range(4) if st[i] == "escaped"]
    if len(esc) != 1 or any(st[i] != "caught" for i in range(4) if i != esc[0]) or te[esc[0]] > tmax:
        return None
    h = esc[0]
    kills = sorted((te[i], i) for i in range(4) if i != h)
    if kills[0][0] < 2.5 or kills[-1][0] > te[h] - .6:
        return None
    return dict(type="prison", hero=h, rival=kills[-1][1], t_dernier=kills[-1][0], t_fin=te[h], morts=[i for _, i in kills])


DETECTEURS = dict(dernier=dernier, presque=presque, duel=duel, sacrifice=sacrifice, trahison=trahison, ensemble=ensemble, prison=prison)
