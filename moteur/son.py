"""Musique épique et émotionnelle 100 % synthétisée, calée sur le minutage de l'histoire."""
import numpy as np
from scipy.signal import butter, lfilter, fftconvolve
from scipy.io import wavfile

SR = 44100
rng = np.random.default_rng(9)


def mf(m):
    return 440 * 2 ** ((m - 69) / 12)


def tt(d):
    return np.arange(int(d * SR)) / SR


def filt(x, fc, kind="low", order=2):
    b, a = butter(order, np.clip(np.array(fc) / (SR / 2), 1e-4, .999), kind)
    return lfilter(b, a, x)


def saw(f, t, ph=0):
    return 2 * ((f * t + ph) % 1) - 1


def adsr(n, a=.01, r=.1):
    e = np.ones(n)
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


# ---- instruments ----
def kick():
    t = tt(.45)
    f = 45 + 120 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) + .3 * filt(rng.normal(0, 1, len(t)), 3000) * np.exp(-t * 200)


def snare():
    t = tt(.25)
    return filt(rng.normal(0, 1, len(t)), [1200, 7000], "band") * np.exp(-t * 16) * .8 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25) * .6


def hat():
    t = tt(.06)
    return filt(rng.normal(0, 1, len(t)), 7000, "high") * np.exp(-t * 70)


def taiko():
    t = tt(1.0)
    f = 42 + 40 * np.exp(-t * 12)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.5) + .4 * filt(rng.normal(0, 1, len(t)), 400) * np.exp(-t * 14)


def crash(d=2.8):
    t = tt(d)
    return filt(rng.normal(0, 1, len(t)), 3500, "high") * np.exp(-t * 1.6) * .6


def impact():
    t = tt(3)
    sub = np.sin(2 * np.pi * 38 * t) * np.exp(-t * 1.5)
    x = sub * 1.1 + crash(3) * .8
    x[:SR] += taiko() * 1.3
    return x


def riser(d=1.3):
    t = tt(d)
    n = filt(rng.normal(0, 1, len(t)), 1500, "high") * (t / d) ** 2.5
    s = np.sin(2 * np.pi * np.cumsum(200 + 900 * (t / d) ** 2) / SR) * (t / d) ** 2 * .3
    return (n * .5 + s)


def heartbeat():
    t = tt(.5)
    b = lambda: np.sin(2 * np.pi * 52 * tt(.2)) * np.exp(-tt(.2) * 18)
    x = np.zeros(len(t))
    x[:len(b())] += b()
    x[int(.22 * SR):int(.22 * SR) + len(b())] += b() * .8
    return filt(x, 200) * 2.2


def piano(m, d):
    t = tt(d)
    f = mf(m)
    x = sum(np.sin(2 * np.pi * f * h * (1 + .0004 * h * h) * t) * (.6 / h ** 1.2) * np.exp(-t * (1.1 + h * .7)) for h in range(1, 8))
    return x * adsr(len(t), .004, .3)


def strings(ms, d, bright=1800):
    t = tt(d)
    vib = 1 + .004 * np.sin(2 * np.pi * 5 * t)
    x = sum(saw(mf(m) * vib * (1 + dd), t, rng.random()) for m in ms for dd in (-.006, 0, .006))
    return filt(x / (3 * len(ms)), bright) * adsr(len(t), .45, .6)


def choir(ms, d):
    t = tt(d)
    x = 0
    for m in ms:
        f = mf(m) * (1 + .005 * np.sin(2 * np.pi * 5.5 * t + rng.random() * 6))
        x = x + np.sin(2 * np.pi * f * t) + .45 * np.sin(4 * np.pi * f * t) + .2 * np.sin(6 * np.pi * f * t)
    x = filt(x / len(ms), [300, 1400], "band") * 2.5
    return x * adsr(len(t), .6, .8)


def pluck(m, d=.25):
    t = tt(d)
    return filt(saw(mf(m), t), 2500) * np.exp(-t * 14)


def bassnote(m, d):
    t = tt(d)
    x = filt(saw(mf(m), t) + saw(mf(m) * 1.004, t, .3), 500) * .6 + np.sin(2 * np.pi * mf(m) * t) * .6
    return x * adsr(len(t), .005, .05)


CH = {"Am": ([57, 60, 64], 45), "F": ([57, 60, 65], 41), "C": ([55, 60, 64], 48), "G": ([55, 59, 62], 43), "Em": ([55, 59, 64], 40)}


class Mix:
    def __init__(self, total):
        self.dry = np.zeros(int((total + 4) * SR))
        self.wet = np.zeros_like(self.dry)

    def add(self, t, x, g=1., rev=0.):
        i = int(t * SR)
        if i < 0:
            x, i = x[-i:], 0
        n = min(len(x), len(self.dry) - i)
        if n <= 0:
            return
        self.dry[i:i + n] += x[:n] * g
        if rev:
            self.wet[i:i + n] += x[:n] * g * rev

    def section(self, t0, t1, prog, bpm, L, cut=None):
        b = 60 / bpm
        bar = 4 * b
        t, k = t0, 0
        while t < t1 - 1e-3:
            ms, root = CH[prog[k % len(prog)]]
            ev = lambda tt_, x, g, rev=0.: self.add(tt_, x, g, rev) if tt_ < t1 - .02 else None
            if "strings" in L:
                ev(t, strings(ms, min(bar, t1 - t) + .3), .30 * L["strings"], .5)
            if "choir" in L:
                ev(t, choir([m + 12 for m in ms[:2]], min(bar, t1 - t) + .3), .28 * L["choir"], .6)
            for i in range(8):
                tb = t + i * b / 2
                if "bass" in L:
                    ev(tb, bassnote(root + (12 if i % 2 else 0), b / 2 * .9), .35 * L["bass"])
                if "hat" in L:
                    ev(tb, hat(), .12 * L["hat"])
            for bt in (0, 2, 2.5):
                if "kick" in L:
                    ev(t + bt * b, kick(), .9 * L["kick"])
            for bt in (1, 3):
                if "snare" in L:
                    ev(t + bt * b, snare(), .45 * L["snare"], .15)
            for bt in range(4):
                if "taiko" in L:
                    ev(t + bt * b, taiko(), (.9 if bt == 0 else .55) * L["taiko"], .2)
            if "arp" in L:
                pat = [ms[0], ms[1], ms[2], ms[0] + 12, ms[2], ms[1], ms[0] + 12, ms[2]]
                for i in range(16):
                    ev(t + i * b / 4, pluck(pat[i % 8] + 12), .14 * L["arp"], .35)
            t += bar
            k += 1


def build(m, sfx, total, out):
    """m : repères (secondes vidéo). sfx : [(t, 'bounce'|'liq')]."""
    X = Mix(total)
    BPM = 140
    # A : action (jeu) jusqu'au héros
    X.add(m["danger"] - 1.3, riser(1.3), .5)
    X.add(m["danger"], impact(), .8, .2)
    X.section(0, m["danger"], ["Am", "Am", "F", "G"], BPM, dict(bass=.8, hat=1, arp=.8, kick=.6))
    X.section(m["danger"], m["go"], ["Am", "F", "G", "Em"], BPM, dict(bass=1, hat=1, arp=1, kick=1, snare=1, strings=.7))
    # B : le héros fonce
    X.add(m["go"] - 1.3, riser(1.3), .6)
    X.add(m["go"], impact(), 1.0, .3)
    X.section(m["go"], m["catch"], ["Am", "F", "C", "G"], BPM, dict(bass=1, hat=1, arp=1, kick=1, snare=1, taiko=1, strings=1, choir=1))
    # C : silence, cœur, piano triste
    X.add(m["catch"] + .45, heartbeat(), .9)
    X.add(m["catch"] + 1.25, heartbeat(), .9)
    mel = [(76, 1), (74, .5), (72, .5), (71, 1), (72, .5), (69, 1.5)]
    t = m["sink"] + .5
    X.add(t, strings([57, 60, 64], m["cry"] - t + .5, 1100), .18, .6)
    for note, d in mel:
        if t < m["cry"] - .1:
            X.add(t, piano(note, d * .8 + 1), .55, .5)
            X.add(t, piano(note - 24, d * .8 + 1), .2, .5)
        t += d * .8
    # cri
    X.add(m["cry"], impact(), 1.0, .4)
    X.add(m["cry"], strings([57, 60, 64, 69], 1.6, 2600), .5, .6)
    X.add(m["cry"], choir([69, 72, 76], 1.6), .45, .6)
    X.add(m["cry"] + 1.5, strings([57, 60, 65, 69], m["resolve"] - m["cry"] - 1.2, 2600), .45, .6)
    X.add(m["cry"] + 1.5, choir([69, 72, 77], m["resolve"] - m["cry"] - 1.2), .4, .6)
    # D : la volonté, course finale
    X.add(m["resolve"] - 1.0, riser(1.0), .5)
    X.add(m["resolve"], impact(), .9, .3)
    X.section(m["resolve"], m["escape"], ["F", "G", "Am", "C"], BPM, dict(bass=1, hat=1, arp=1, kick=1, snare=1, taiko=.8, strings=1, choir=.8))
    X.add(m["escape"] - 1.2, riser(1.2), .6)
    X.add(m["escape"], crash(3), .7, .3)
    X.add(m["escape"], strings([60, 64, 67, 72], 2.5, 2400), .45, .6)
    X.add(m["escape"], choir([72, 76, 79], 2.5), .4, .6)
    # E : fin douce
    t = m["end"] + .2
    for ch, d in (("F", 1.6), ("G", 1.6), ("C", 3.5)):
        ms, root = CH[ch]
        X.add(t, strings(ms, d + .4, 1200), .22, .7)
        X.add(t, piano(root + 12, d + 1), .35, .5)
        for i, note in enumerate(ms):
            X.add(t + .12 * i, piano(note + 12, d + 1), .3, .5)
        t += d
    X.add(m["end"] + .2, piano(76, 1.5), .4, .5)
    X.add(m["end"] + 1.0, piano(74, 1.5), .4, .5)
    X.add(m["end"] + 1.8, piano(72, 1.5), .4, .5)
    X.add(m["end"] + 3.2, piano(79, 3), .4, .5)
    # bruitages du jeu (discrets)
    for t, kind in sfx:
        if kind == "bounce":
            X.add(t, pluck(rng.choice([69, 72, 74, 76, 79, 81]) + 12, .15), .05)
    # réverbe
    ir_t = tt(2.6)
    ir = rng.normal(0, 1, len(ir_t)) * np.exp(-ir_t * 2.4)
    wet = fftconvolve(X.wet, ir)[:len(X.dry)] * .02
    y = X.dry + wet
    y = y[:int((total + .3) * SR)]
    y[-int(.3 * SR):] *= np.linspace(1, 0, int(.3 * SR))
    y = np.tanh(y / (np.abs(y).max() + 1e-9) * 1.4) * .9
    wavfile.write(out, SR, (y * 32767).astype(np.int16))
