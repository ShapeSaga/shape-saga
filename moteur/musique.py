"""Compositeur d'épisodes. Chaque épisode reçoit un STYLE (mode, tempo, instruments, rythmique) et un ARC émotionnel défini par son scénario.
Le suspense est piloté par la course réelle : plus le liquide approche des formes, plus des couches s'ajoutent.
Avant le sommet : un crescendo, puis un court silence, puis le coup final."""
import numpy as np
from scipy.signal import fftconvolve
from scipy.io import wavfile
from son import SR, rng, mf, tt, filt, adsr, kick, snare, hat, taiko, crash, heartbeat, piano, strings, choir, pluck, Mix
from son2 import brass, braam, dbass, ostinato, roll

MODES = dict(mineur=[0, 2, 3, 5, 7, 8, 10], dorien=[0, 2, 3, 5, 7, 9, 10], phrygien=[0, 1, 3, 5, 7, 8, 10],
             harmonique=[0, 2, 3, 5, 7, 8, 11], majeur=[0, 2, 4, 5, 7, 9, 11], lydien=[0, 2, 4, 6, 7, 9, 11])
PROGS = [[0, 5, 3, 4], [0, 3, 5, 4], [0, 6, 5, 4], [0, 2, 5, 4], [0, 5, 6, 3], [0, 3, 0, 4], [0, 4, 5, 3], [0, 2, 3, 6]]

STYLES = dict(
    orchestral=dict(mode="mineur", bpm=(140, 156), basse="dbass", rythme="orch", lead="piano", nappe="strings", arpege="ost", tick=False),
    thriller=dict(mode="phrygien", bpm=(112, 128), basse="pulse", rythme="march", lead="musicbox", nappe="pad", arpege="stacc", tick=True),
    guerre=dict(mode="dorien", bpm=(146, 160), basse="dbass", rythme="taiko", lead="brass", nappe="choir", arpege="ost", tick=False),
    melancolie=dict(mode="mineur", bpm=(84, 104), basse="sub", rythme="doux", lead="piano", nappe="strings", arpege="harpe", tick=False),
    electro=dict(mode="harmonique", bpm=(126, 140), basse="pulse", rythme="four", lead="pluck", nappe="pad", arpege="saw", tick=False),
    espoir=dict(mode="lydien", bpm=(118, 134), basse="sub", rythme="clap", lead="musicbox", nappe="strings", arpege="harpe", tick=False),
)


# ------------------------------------------------------------------ instruments supplémentaires
def musicbox(m, d=1.2):
    t = tt(d); f = mf(m)
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * k) for r, a, k in ((1, 1, 3.2), (2.76, .35, 6), (5.4, .15, 9)))
    return x * .5


def pad(ms, d):
    t = tt(d); x = np.zeros_like(t)
    for m in ms:
        for det in (-.07, 0, .07):
            f = mf(m + det); x += 2 * ((f * t) % 1) - 1
    x = filt(x, 1300) * adsr(len(t), min(.8, d / 3), min(.8, d / 3)) * .09
    return x


def sub(m, d):
    t = tt(d); return np.sin(2 * np.pi * mf(m) * t) * adsr(len(t), .02, .25) * .9


def pulse(m, d):
    t = tt(d); f = mf(m); sq = np.sign(np.sin(2 * np.pi * f * t))
    return filt(sq, 700) * adsr(len(t), .005, .08) * .55


def tictac(pitch=1900):
    t = tt(.05); return np.sin(2 * np.pi * pitch * t) * np.exp(-t * 120) * .8 + filt(rng.normal(0, 1, len(t)), 5000, "high") * np.exp(-t * 400) * .3


def riser_suspens(d):
    t = tt(d); p = t / d
    f = 180 * (2 ** (3.2 * p))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * p ** 2 * .55
    x += filt(rng.normal(0, 1, len(t)), 2500, "high") * p ** 2.4 * .35
    return x


def sting(root):
    """Accord dissonant et sec : le coup du destin."""
    t = tt(1.6); x = np.zeros_like(t)
    for m in (root, root + 1, root + 6, root + 12):
        x += np.sin(2 * np.pi * mf(m) * t) * np.exp(-t * 3.5) * .3
    return x + filt(rng.normal(0, 1, len(t)), 1200) * np.exp(-t * 14) * .5


# ------------------------------------------------------------------ théorie
def degre(tonique, mode, d):
    g = MODES[mode]
    return tonique + g[d % 7] + 12 * (d // 7)


def accord(tonique, mode, d):
    return [degre(tonique, mode, d + k) for k in (0, 2, 4)]


# ------------------------------------------------------------------ composition
def _couches(X, t, b, ms, racine, style, I, mood, motif, gain=1.0):
    """Une mesure de 4 temps : les couches présentes dépendent de l'intensité I (0..1) tirée de la course réelle."""
    S = STYLES[style]
    d = 4 * b
    g = lambda x: x * gain
    nappe = S["nappe"]
    if nappe == "strings":
        X.add(t, strings(ms + [ms[0] + 12], d + .2, 2200), g(.26), .5)
    elif nappe == "choir":
        X.add(t, choir([m + 12 for m in ms], d + .2), g(.30), .6)
    else:
        X.add(t, pad([m + 12 for m in ms], d + .3), g(1.0), .5)
    if mood == "sad":
        for i, n in enumerate(motif * 2):
            X.add(t + i * b / 2, piano(n + 12, 1.6), g(.40), .7)
        return
    if I > .12 and S["tick"]:
        for i in range(8):
            X.add(t + i * b / 2, tictac(1900 if i % 2 == 0 else 1500), g(.22 + .25 * I))
    if I > .15:
        for i in range(16):
            if i % 2 == 0 or I > .6:
                X.add(t + i * b / 4, hat(), g(.07 + .08 * I))
    if I > .3:
        bs = S["basse"]
        for i in range(8):
            nb = racine + (12 if i % 4 == 2 else 0)
            if bs == "dbass":
                X.add(t + i * b / 2, dbass(nb, b / 2 * .9), g(.30))
            elif bs == "pulse":
                X.add(t + i * b / 2, pulse(nb, b / 2 * .8), g(.24))
            else:
                if i % 4 == 0:
                    X.add(t + i * b / 2, sub(nb, b * 1.8), g(.38))
    if I > .42:
        ar = S["arpege"]
        for i in range(16):
            n = ms[i % 3] + (12 if i % 7 == 5 else 0)
            tb = t + i * b / 4
            if ar == "ost":
                X.add(tb, ostinato(n, b / 4 * .95), g(.15), .2)
            elif ar == "saw":
                X.add(tb, pluck(n + 12, b / 4 * .9), g(.15), .2)
            elif ar == "stacc" and i % 2 == 0:
                X.add(tb, musicbox(n + 12, .5), g(.18), .3)
            elif ar == "harpe" and i % 2 == 0:
                X.add(tb, pluck(n + 12, .6), g(.13), .5)
    if I > .5:
        rt = S["rythme"]
        for bt in ((0, 1, 2, 3) if rt in ("four", "taiko") else (0, 1.5, 2, 3.5)):
            if rt != "doux":
                X.add(t + bt * b, kick(), g(.7 + .25 * I))
        if rt in ("orch", "march", "clap", "four"):
            for bt in (1, 3):
                X.add(t + bt * b, snare(), g(.45), .2)
    if I > .66 and S["rythme"] in ("orch", "taiko", "march"):
        for bt in (0, 2, 2.75):
            X.add(t + bt * b, taiko(), g(.8), .25)
    if I > .74 and S["lead"] == "brass":
        for bt, dd in ((0, 1.2), (1.5, .4), (2, .4), (3, .9)):
            X.add(t + bt * b, brass(ms, dd * b * 1.6), g(.2), .3)
    if I > .74 and S["lead"] in ("piano", "musicbox", "pluck"):
        for i, n in enumerate(motif):
            X.add(t + i * b, (piano if S["lead"] == "piano" else musicbox)(n + 12, 1.0), g(.3), .5)
    if I > .85:
        X.add(t, choir([m + 12 for m in ms], d + .2), g(.28), .6)


GAIN_HUMEUR = {"calme": .55, "tendu": .7, "sombre": .62, "puissance": 1.0, "triomphe": 1.0, "sad": .5}


def _relief(arc, climax, n):
    """Enveloppe de volume par section (fondus de 0,4 s) : la montée garde de la réserve pour que le sommet frappe."""
    g = np.full(n, .62)
    for t0, t1, mood in arc:
        g[int(t0 * SR):int(t1 * SR)] = GAIN_HUMEUR.get(mood, .62)
    if climax:                                                   # crescendo sur les 3 s qui précèdent le sommet
        a, b = int(max(0, climax - 3) * SR), int(climax * SR)
        g[a:b] = np.maximum(g[a:b], np.linspace(g[a] if a < n else .62, .95, max(b - a, 0))[:len(g[a:b])])
    k = int(.4 * SR)
    return np.convolve(g, np.ones(k) / k, mode="same")


def composer(marks, sfx, total, out, style, arc, tension, hits, climax, graine, drame=False):
    """arc : [(t0, t1, mood)] ; tension(t) -> 0..1 ; hits : [(t, kind)] ; climax : instant du sommet (silence juste avant)."""
    rr = np.random.default_rng(graine)
    S = STYLES[style]
    tonique = int(rr.integers(43, 51))
    mode = S["mode"]
    bpm = float(rr.integers(S["bpm"][0], S["bpm"][1] + 1))
    prog = PROGS[int(rr.integers(len(PROGS)))]
    b = 60 / bpm
    motif = [degre(tonique + 24, mode, int(x)) for x in rr.choice([0, 1, 2, 3, 4, 5, 6], 4, replace=False)]
    X = Mix(total)
    for (t0, t1, mood) in arc:
        k, t = 0, t0
        while t < t1 - .05:
            m_mode = "majeur" if mood == "triomphe" else mode
            deg = prog[k % 4]
            ms = [m + 12 for m in accord(tonique + (2 if mood == "triomphe" else 0), m_mode, deg)]
            racine = degre(tonique - 12 + (2 if mood == "triomphe" else 0), m_mode, deg)
            I = {"calme": .1, "tendu": tension(t), "sombre": .35 + .3 * tension(t), "puissance": .7 + .3 * tension(t), "triomphe": .95, "sad": 0}.get(mood, tension(t))
            _couches(X, t, b, ms, racine, style, I, mood, motif, 1.0)
            t += 4 * b; k += 1
    # points d'orgue : coups, impacts, silences
    for t, kind in hits:
        if kind == "braam":
            X.add(t, braam(tonique, 2.6), .85, .4); X.add(t, crash(2.4), .5, .3)
        elif kind == "sting":
            X.add(t, sting(tonique + 12), .9, .5)
        elif kind == "choeur":
            X.add(t, choir([m + 12 for m in accord(tonique, mode, 0)], 2.4), .5, .6)
        elif kind == "piano":
            for i, n in enumerate(motif):
                X.add(t + i * .55, piano(n + 12, 2.2), .5, .7)
    for t in marks.get("_risers", []):
        X.add(max(0, t - 1.4), riser_suspens(1.4), .8)
    # silence juste avant le sommet, puis coup final
    if climax:
        n0, n1 = int((climax - .45) * SR), int((climax - .03) * SR)
        env = np.ones(len(X.dry)); env[n0:n1] = np.linspace(.12, .0, n1 - n0)
        X.dry *= env; X.wet *= env
        X.add(climax - 1.95, riser_suspens(1.5), .7)
        if drame:                                                    # la chute : coup dissonant, grave, sans lumière
            X.add(climax, sting(tonique + 12), 1.0, .6); X.add(climax, braam(tonique, 3.4), .9, .5); X.add(climax, taiko(), 1.0, .3)
        else:
            X.add(climax, braam(tonique + 2, 3.2), 1.0, .5); X.add(climax, crash(3.2), .8, .4); X.add(climax, taiko(), 1.0, .3)
            X.add(climax, strings([m + 12 for m in accord(tonique + 2, "majeur", 0)] + [tonique + 26], 3.6, 3000), .5, .6)
    scale = [degre(tonique + 24, mode, d) for d in (0, 2, 4)]
    for t, kind in sfx:
        X.add(t, pluck(int(rr.choice(scale)) + 12, .12), .035)
    ir_t = tt(2.4)
    ir = rng.normal(0, 1, len(ir_t)) * np.exp(-ir_t * 2.6)
    y = X.dry + fftconvolve(X.wet, ir)[:len(X.dry)] * .02
    y = y * _relief(arc, climax, len(y))                         # contraste : couplets retenus, sommet à pleine puissance
    if climax and not drame:
        n = int(1.8 * SR); tt_ = np.arange(n) / SR               # « sub drop » : grave qui tombe sous le coup final
        sd = np.sin(2 * np.pi * np.cumsum(35 + 40 * np.exp(-tt_ * 3)) / SR) * np.exp(-tt_ * 1.6)
        i0 = int(climax * SR); y[i0:i0 + n] += .55 * sd[:max(0, len(y) - i0)] * np.percentile(np.abs(y), 99)
    y = y[:int((total + .2) * SR)]
    y[-int(.2 * SR):] *= np.linspace(1, 0, int(.2 * SR))
    y = y / (np.percentile(np.abs(y), 99.5) + 1e-9)
    y = np.tanh(y * 1.1) * .92
    wavfile.write(out, SR, (y * 32767).astype(np.int16))
    return dict(style=style, mode=mode, bpm=bpm, tonique=tonique, progression=prog)
