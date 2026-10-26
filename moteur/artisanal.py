"""Rendu « fait main » appliqué aux planches : le trait tremble légèrement, l'encre varie, le papier a du grain,
les couleurs sont très légèrement décalées (comme une impression). Déterministe pour une graine donnée."""
import numpy as np
import cairo
from scipy.ndimage import gaussian_filter, map_coordinates, zoom

W, H = 1080, 1920
_REFS = []          # garde en vie les tableaux utilisés par les surfaces cairo


def _champ(rng, amp, sigma, f=4):
    h, w = H // f, W // f
    a = gaussian_filter(rng.normal(0, 1, (h, w)), sigma / f)
    a = a / (a.std() + 1e-9) * amp
    return zoom(a, f, order=1)[:H, :W]


def appliquer(surf, graine, force=1.0, papier=True):
    """Renvoie une nouvelle surface. papier=False : seulement le tremblement du trait (pour les bulles, qui sont transparentes)."""
    rng = np.random.default_rng(graine)
    arr = np.frombuffer(surf.get_data(), np.uint8).reshape(H, W, 4).copy()
    dx, dy = _champ(rng, 2.0 * force, 38), _champ(rng, 2.0 * force, 38)           # ondulation lente du trait
    dx += _champ(rng, .9 * force, 9); dy += _champ(rng, .9 * force, 9)             # tremblé fin
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    co = [yy + dy, xx + dx]
    out = np.empty_like(arr)
    for ch in range(4):
        out[..., ch] = map_coordinates(arr[..., ch], co, order=1, mode="nearest")
    if papier:
        f = out.astype(np.float32)
        f[..., 2] = np.roll(f[..., 2], 1, axis=1); f[..., 0] = np.roll(f[..., 0], -1, axis=1)     # décalage d'impression
        dens = 1 + _champ(rng, .035, 120)[..., None]                                    # l'encre n'est pas uniforme
        f[..., :3] *= dens
        grain = rng.normal(0, 5.5 * force, (H // 2, W // 2)).repeat(2, 0).repeat(2, 1)[:H, :W]
        f[..., :3] += grain[..., None]
        f[..., :3] *= np.array([.985, .99, 1.0], np.float32)                           # papier légèrement chaud (BGR)
        out = np.clip(f, 0, 255).astype(np.uint8)
    out = np.ascontiguousarray(out)
    s = cairo.ImageSurface.create_for_data(out, cairo.FORMAT_ARGB32, W, H, W * 4)
    _REFS.append(out)
    return s
