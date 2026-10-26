"""Musique « bande-annonce » : plus de puissance, d'adrénaline et d'émotion, sommet dans les 8 dernières secondes."""
import numpy as np
from scipy.signal import fftconvolve
from scipy.io import wavfile
from son import (SR, rng, mf, tt, filt, saw, adsr, kick, snare, hat, taiko, crash, riser, heartbeat, piano, strings, choir, pluck, Mix)


def brass(ms, d, g=1.0):
    t = tt(d)
    x = sum(saw(mf(m) * (1 + dd), t, rng.random()) for m in ms for dd in (-.004, 0, .004))
    x = x / (3 * len(ms))
    env = np.minimum(1, t / .05) * np.exp(-t * .8)
    x = filt(x, 700) * (1 - env) + filt(x, 3200) * env          # le filtre s'ouvre à l'attaque : cuivres
    return np.tanh(x * 2.5 * g) * adsr(len(t), .02, .25)


def braam(root, d=2.6):
    t = tt(d)
    x = brass([root, root + 7, root + 12], d, 1.6) * 1.2 + np.sin(2 * np.pi * mf(root - 12) * t) * np.exp(-t * .6) * .8
    return x * np.exp(-t * .5)


def dbass(m, d):
    t = tt(d)
    x = saw(mf(m), t) + saw(mf(m) * 1.006, t, .4) + np.sin(2 * np.pi * mf(m) * t) * 1.5
    return np.tanh(filt(x, 900) * 2.2) * adsr(len(t), .004, .04)


def ostinato(m, d):
    t = tt(d)
    x = saw(mf(m), t) + saw(mf(m) * 1.005, t, .3)
    return filt(x, 2600) * np.exp(-t * 9) * adsr(len(t), .003, .02)


def roll(d):
    """Roulement de caisse claire qui accélère et monte."""
    x, t = np.zeros(int(d * SR) + SR), 0.0
    while t < d:
        p = t / d
        i = int(t * SR)
        s = snare() * (.25 + .75 * p)
        x[i:i + len(s)] += s[:len(x) - i]
        t += .11 - .07 * p
    return x[:int(d * SR)]


CH = {"Am": ([57, 60, 64], 45), "F": ([57, 60, 65], 41), "C": ([55, 60, 64], 48), "G": ([55, 59, 62], 43),
      "Dm": ([57, 62, 65], 38), "E": ([56, 59, 64], 40), "Bm": ([59, 62, 66], 47), "G2": ([59, 62, 67], 43),
      "D": ([57, 62, 66], 38), "A": ([57, 61, 64], 45)}


def section(X, t0, t1, prog, bpm, L):
    b = 60 / bpm
    bar = 4 * b
    t, k = t0, 0
    while t < t1 - 1e-3:
        ms, root = CH[prog[k % len(prog)]]
        ev = lambda tt_, x, g, rev=0.: X.add(tt_, x, g, rev) if tt_ < t1 - .01 else None
        d = min(bar, t1 - t)
        if "strings" in L:
            ev(t, strings(ms + [ms[0] + 12], d + .2, 2600), .30 * L["strings"], .5)
        if "choir" in L:
            ev(t, choir([m + 12 for m in ms], d + .2), .34 * L["choir"], .6)
        for i in range(16):
            tb = t + i * b / 4
            if "ost" in L:
                pat = [ms[0], ms[0], ms[2], ms[0], ms[1], ms[0], ms[2], ms[1]]
                ev(tb, ostinato(pat[i % 8], b / 4 * .95), .16 * L["ost"], .2)
            if "hat" in L and i % 2 == 0:
                ev(tb, hat(), .12 * L["hat"])
            if "bass" in L and i % 2 == 0:
                ev(tb, dbass(root + (12 if i % 4 == 2 else 0), b / 2 * .9), .30 * L["bass"])
        kicks = (0, 1, 2, 3) if L.get("double") else (0, 1.5, 2, 3.5)
        for bt in kicks:
            if "kick" in L:
                ev(t + bt * b, kick(), .95 * L["kick"])
        for bt in (1, 3):
            if "snare" in L:
                ev(t + bt * b, snare(), .55 * L["snare"], .2)
        for bt in (0, 1, 2, 3, 3.5) if L.get("double") else (0, 2, 2.75):
            if "taiko" in L:
                ev(t + bt * b, taiko(), (1 if bt == 0 else .6) * L["taiko"], .25)
        if "brass" in L:
            for bt, dd in ((0, 1.2), (1.5, .4), (2, .4), (3, .9)):
                ev(t + bt * b, brass(ms, dd * b * 1.6), .22 * L["brass"], .3)
        t += bar
        k += 1


def build(m, sfx, total, out, BPM=150):
    X = Mix(total)
    b = 60 / BPM
    # 0 → 1re planche : tension immédiate (accroche)
    X.add(0, braam(45, 2.5), .55, .3)
    section(X, 0, m["notyou"], ["Am", "F", "Dm", "E"], BPM, dict(ost=1, bass=.8, taiko=.7, hat=.6, kick=.7))
    X.add(m["notyou"] - 1.0, riser(1.0), .5)
    # la chute de Rouge : impact, chœur sombre
    X.add(m["notyou"], braam(45, 2.6), .8, .4)
    X.add(m["notyou"], crash(2.5), .5, .3)
    X.add(m["notyou"], choir([69, 72, 76], 2.0), .5, .6)
    # course du milieu : ça monte
    section(X, m["notyou"] + 2.0, m["notdone"], ["Am", "F", "C", "E"], BPM, dict(ost=1, bass=1, taiko=1, hat=1, kick=1, snare=1, strings=.8, brass=.6))
    X.add(m["notdone"] - 1.6, roll(1.6), .7, .2)
    X.add(m["notdone"] - 1.4, riser(1.4), .6)
    # SOMMET (8 dernières secondes) : on monte d'un ton, double tempo, tout le monde
    X.add(m["notdone"], braam(47, 3), 1.0, .4)
    X.add(m["notdone"], crash(3), .7, .3)
    for i in range(4):
        X.add(m["notdone"] + i * b, taiko(), 1.0, .3)
    section(X, m["notdone"] + 4 * b, m["escape"], ["Bm", "G2", "D", "A"], BPM, dict(ost=1.2, bass=1.2, taiko=1.2, hat=1.2, kick=1.2, snare=1.2, strings=1.2, choir=1.2, brass=1.2, double=1))
    X.add(m["escape"] - 1.3, roll(1.3), .8, .2)
    # LA SORTIE : coup final triomphal
    X.add(m["escape"], braam(50, 3.5), 1.0, .5)
    X.add(m["escape"], crash(3.5), .8, .4)
    X.add(m["escape"], strings([62, 66, 69, 74], 3.8, 3000), .55, .6)
    X.add(m["escape"], choir([74, 78, 81], 3.8), .55, .6)
    X.add(m["escape"], brass([62, 66, 69], 2.0), .4, .5)
    # planche finale : émotion
    t = m["forall"] + .3
    for note, d in ((78, .5), (76, .5), (74, 1.0), (73, .6)):
        X.add(t, piano(note, 2), .5, .6)
        t += d
    X.add(m["forall"], strings([62, 66, 69], m["card"] - m["forall"] + 1.2, 1600), .3, .7)
    X.add(m["card"], taiko(), .9, .4)
    X.add(m["card"], piano(62, 3), .45, .6)
    X.add(m["card"], piano(74, 3), .35, .6)
    for t, kind in sfx:
        X.add(t, pluck(int(rng.choice([69, 72, 74, 76, 79])) + 12, .12), .04)
    ir_t = tt(2.4)
    ir = rng.normal(0, 1, len(ir_t)) * np.exp(-ir_t * 2.6)
    y = X.dry + fftconvolve(X.wet, ir)[:len(X.dry)] * .02
    y = y[:int((total + .2) * SR)]
    y[-int(.2 * SR):] *= np.linspace(1, 0, int(.2 * SR))
    y = y / (np.percentile(np.abs(y), 99.5) + 1e-9)
    y = np.tanh(y * 1.1) * .92                          # compression « bande-annonce »
    wavfile.write(out, SR, (y * 32767).astype(np.int16))
