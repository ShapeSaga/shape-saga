"""Montage générique : séquence de segments 'game' (vitesse réelle, coupes franches possibles) et 'panel' (planches animées)."""
import math, subprocess, cairo, json
import sim, dessin, decor, murs

FPS, W, H = 30, 1080, 1920


def timeline(seq, PAN, events):
    """events : {nom: temps de jeu} -> temps vidéo. Retourne marks, gmap, total."""
    marks, gmap, v = {}, [], 0.0
    for s in seq:
        if s[0] == "game":
            gmap.append((v, s[1], s[2]))
            for name, tt in events.items():
                if s[1] <= tt < s[2]:
                    marks[name] = v + tt - s[1]
            v += s[2] - s[1]
        else:
            marks.setdefault(s[1], v)
            v += PAN[s[1]]
    return marks, gmap, v


def _barre_vie(c, x, y, hp):
    w = 96
    c.rectangle(x - w / 2 - 3, y - 83, w + 6, 17); c.set_source_rgba(.05, .05, .08, .85); c.fill()
    k = max(0, min(1, hp / 100))
    c.rectangle(x - w / 2, y - 80, w * k, 11); c.set_source_rgb(min(1, 2 * (1 - k)) * .95 + .05, min(1, 2 * k) * .85 + .05, .12); c.fill()
    c.rectangle(x - w / 2 - 3, y - 83, w + 6, 17); c.set_source_rgb(0, 0, 0); c.set_line_width(2.5); c.stroke()


def _obstacle(c, x, y, w, h, ang, kind):
    """Obstacles animés : machinerie (glissières, barres tournantes) et cellule de la prison."""
    c.save(); c.translate(x, y); c.rotate(ang)
    c.rectangle(-w / 2 + 5, -h / 2 + 7, w, h); c.set_source_rgba(0, 0, 0, .28); c.fill()
    if kind in ("cellule", "porte"):
        base = (.16, .16, .20) if kind == "cellule" else (.42, .34, .14)
        c.rectangle(-w / 2, -h / 2, w, h); c.set_source_rgb(*base); c.fill_preserve(); c.set_source_rgb(.02, .02, .04); c.set_line_width(4); c.stroke()
        if w > h:
            for xx in range(int(-w / 2) + 20, int(w / 2), 34):
                c.move_to(xx, -h / 2 + 4); c.line_to(xx, h / 2 - 4); c.set_source_rgba(.7, .72, .8, .55); c.set_line_width(5); c.stroke()
        else:
            for yy in range(int(-h / 2) + 20, int(h / 2), 34):
                c.move_to(-w / 2 + 4, yy); c.line_to(w / 2 - 4, yy); c.set_source_rgba(.7, .72, .8, .55); c.set_line_width(5); c.stroke()
    else:
        g = cairo.LinearGradient(0, -h / 2, 0, h / 2)
        g.add_color_stop_rgb(0, .85, .86, .9); g.add_color_stop_rgb(1, .35, .36, .42)
        if kind == "spin":
            g = cairo.LinearGradient(0, -h / 2, 0, h / 2); g.add_color_stop_rgb(0, 1, .65, .2); g.add_color_stop_rgb(1, .75, .22, .08)
        c.rectangle(-w / 2, -h / 2, w, h); c.set_source(g); c.fill_preserve(); c.set_source_rgb(.05, .05, .08); c.set_line_width(4); c.stroke()
        for k in range(int(w // 36)):                            # chevrons de danger jaune et noir
            xx = -w / 2 + 14 + k * 36
            c.move_to(xx, h / 2 - 2); c.line_to(xx + 14, h / 2 - 2); c.line_to(xx + 24, -h / 2 + 2); c.line_to(xx + 10, -h / 2 + 2); c.close_path()
            c.set_source_rgba(.08, .08, .1, .55); c.fill()
        if kind == "spin":
            c.new_path(); c.arc(0, 0, h * .75, 0, 6.2832); c.set_source_rgb(.25, .25, .3); c.fill_preserve(); c.set_source_rgb(.05, .05, .08); c.set_line_width(4); c.stroke()
            c.new_path(); c.arc(0, 0, h * .28, 0, 6.2832); c.set_source_rgb(.9, .85, .5); c.fill()
    c.restore()


def draw_game(c, S, gt, th):
    if S.get("mode") == "murs":
        return murs.dessiner(c, S, gt, th["_look"], th["_joueurs"], sim.verts)
    F = S["frames"]
    i = min(int(round(gt * FPS)), len(F) - 1)
    ly, fr = F[i][1], F[i][2]
    dyn = F[i][3] if len(F[i]) > 3 else []
    nom = th.get("_nom")
    riche = nom in decor.DECOR
    if riche:
        decor.dessiner_jeu(c, nom, sim.WALLS, ly, gt, th.get("_graine", 0))
    else:
        c.set_source_rgb(*th["bg"]); c.paint()
        c.rectangle(0, 0, W, 120); c.set_source_rgb(*th["sky"]); c.fill()
        for x0, y0, x1, y1 in sim.WALLS:
            c.rectangle(x0, y0, x1 - x0, y1 - y0)
            c.set_source_rgb(*th["wall"]); c.fill_preserve()
            c.set_source_rgb(*th["wallk"]); c.set_line_width(3); c.stroke()
    for (ox, oy, ow, oh, oang, okind) in dyn:
        _obstacle(c, ox, oy, ow, oh, oang, okind)
    for k, (name, col, kind) in enumerate(sim.SHAPES):
        for j in range(6, -1, -1):
            e = F[max(0, i - j)][2][k]
            x, y, vx, vy, st, age = e[:6]
            ang = e[6] if len(e) > 6 else 0.0
            if y < -80 or (st == "caught" and age > 4):
                continue
            a = 1 if j == 0 else .18 * (1 - j / 7)
            sc = 1 if j == 0 else .85 - j * .05
            c.save(); c.translate(x, y); c.scale(sc, sc); c.rotate(ang)
            vs = sim.verts(kind)
            c.new_path()
            if vs:
                c.move_to(*vs[0])
                for p in vs[1:]:
                    c.line_to(*p)
                c.close_path()
            else:
                c.arc(0, 0, sim.SIZE, 0, 2 * math.pi)
            c.set_source_rgba(*col, a)
            if j == 0:
                c.fill_preserve(); c.set_source_rgba(*[q * .55 for q in col], 1); c.set_line_width(5); c.stroke()
            else:
                c.fill()
            c.restore()
    if S.get("mode") == "prison":
        for k in range(4):
            e = F[i][2][k]
            if e[4] == "alive":
                _barre_vie(c, e[0], e[1], e[7] if len(e) > 7 else 100)
        return
    if riche:
        decor.liquide(c, nom, ly, gt)
        return
    wave = [(x, ly + 7 * math.sin(x / 40 + gt * 5) + 3 * math.sin(x / 13 - gt * 7)) for x in range(0, W + 1, 12)]
    c.new_path(); c.move_to(*wave[0])
    for p in wave[1:]:
        c.line_to(*p)
    c.line_to(W, H); c.line_to(0, H); c.close_path()
    c.set_source_rgba(*th["liq"], .88); c.fill()
    c.new_path(); c.move_to(*wave[0])
    for p in wave[1:]:
        c.line_to(*p)
    c.set_source_rgba(*th["liqtop"], .95); c.set_line_width(7); c.stroke()


def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def draw_panel(c, P, PAN, name, tau, shake_names=()):
    """Une planche entre de façons différentes selon son style : impact, glisse, iris, zoom, tourne, coupe."""
    base, bubbles = P[name][:2]
    style = P[name][2] if len(P[name]) > 2 else "impact"
    dur = PAN[name]
    z = 1 + .04 * tau / dur
    sx = sy = 0.0
    rot = 0.0
    clip_r = None
    if style == "impact":
        if tau < .18:
            z *= 1 + .12 * (1 - tau / .18)
        if tau < .4:
            a = 20 * (1 - tau / .4)
            sx, sy = a * math.sin(tau * 90), a * math.cos(tau * 77)
    elif style == "glisse":
        sx = (1 - _ease(tau / .28)) * W * .9
    elif style == "iris":
        clip_r = _ease(tau / .38) * 1400
    elif style == "zoom":
        z *= 1 + .38 * (1 - _ease(tau / .34))
    elif style == "tourne":
        rot = -.09 * (1 - _ease(tau / .3)); z *= 1 + .18 * (1 - _ease(tau / .3))
    if name in shake_names and tau > .4:
        sx, sy = 3.5 * math.sin(tau * 60), 2.5 * math.cos(tau * 53)
    c.set_source_rgb(*dessin.WHITE); c.paint()
    c.save()
    if clip_r is not None:
        c.new_path(); c.arc(W / 2, H / 2, clip_r, 0, 6.2832); c.clip()
    c.translate(W / 2 + sx, H / 2 + sy); c.rotate(rot); c.scale(z, z); c.translate(-W / 2, -H / 2)
    c.set_source_surface(base); c.paint()
    for surf, delay, (bx, by) in bubbles:
        if tau < delay:
            continue
        p = (tau - delay) / .14
        s = 1.15 * p if p < 1 else 1.15 - .15 * min(1, (p - 1) / .4)
        c.save(); c.translate(bx, by); c.scale(max(s, .01), max(s, .01)); c.translate(-bx, -by)
        c.set_source_surface(surf); c.paint(); c.restore()
    c.restore()
    if style == "impact" and tau < .12:
        c.set_source_rgba(1, 1, 1, .8 * (1 - tau / .12)); c.paint()


BANDEAU_Y = 300


def _visibilite_bandeau(S, gt):
    """1 = accroche visible ; s'efface quand une forme encore en jeu monte près du haut (la sortie ne doit jamais être cachée).
    On regarde ±0,5 s autour de l'instant pour un fondu doux, sans clignotement."""
    if S.get("mode") == "murs":
        return 1.0                                       # le plateau commence sous l'accroche
    F, ymin = S["frames"], 9999
    for k in range(-15, 16, 3):
        fr = F[max(0, min(int(gt * FPS) + k, len(F) - 1))]
        ymin = min([ymin] + [x[1] for x in fr[2] if x[4] == "alive"])
    seuil, rampe = (470, 60) if F[0][1] is None else (520, 260)   # prison : seule la porte du plafond compte
    return max(0.0, min(1.0, (ymin - seuil) / rampe))


def bandeau(c, txt, y=BANDEAU_Y):
    """Accroche en haut de l'écran : pastille blanche, texte noir gras (lisible même en petit sur téléphone)."""
    c.save()
    c.select_font_face("Comic Neue", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    size = 58
    c.set_font_size(size)
    e = c.text_extents(txt)
    if e.width > 900:
        size = size * 900 / e.width
        c.set_font_size(size); e = c.text_extents(txt)
    w, h, r = e.width + 64, size * 1.5, 18
    x0, y0 = (W - w) / 2, y - h / 2
    c.new_sub_path()
    for cx, cy, a in ((x0 + w - r, y0 + r, -math.pi / 2), (x0 + w - r, y0 + h - r, 0), (x0 + r, y0 + h - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
        c.arc(cx, cy, r, a, a + math.pi / 2)
    c.close_path()
    c.set_source_rgba(0, 0, 0, .35); c.save(); c.translate(0, 6); c.fill_preserve(); c.restore()
    c.set_source_rgb(1, 1, 1); c.fill()
    c.move_to(W / 2 - e.width / 2 - e.x_bearing, y - e.height / 2 - e.y_bearing)
    c.set_source_rgb(.05, .05, .07); c.show_text(txt)
    c.restore()


def render(S, seq, PAN, P, theme, out, shake_names=(), accroche=None):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-vf", "noise=alls=6:allf=t,rgbashift=rh=-1:bh=1,vignette=PI/7", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", out + "_v.mp4"],
                           stdin=subprocess.PIPE)
    durs = [(s[2] - s[1]) if s[0] == "game" else PAN[s[1]] for s in seq]
    total = sum(durs)
    for f in range(int(round(total * FPS))):
        t, vt = f / FPS, 0.0
        for s, d in zip(seq, durs):
            if t < vt + d or s is seq[-1]:
                if s[0] == "game":
                    draw_game(c, S, s[1] + (t - vt), theme)
                    if t - vt < 2 / FPS and vt > 0 and seq[seq.index(s) - 1][0] == "game":   # coupe franche : flash bref
                        c.set_source_rgba(1, 1, 1, .5); c.paint()
                else:
                    draw_panel(c, P, PAN, s[1], t - vt, shake_names)
                if accroche and s[0] == "game":      # seulement sur le jeu : les planches ont déjà leur texte
                    a = _visibilite_bandeau(S, s[1] + (t - vt))
                    if a > 0:
                        c.push_group(); bandeau(c, accroche); c.pop_group_to_source(); c.paint_with_alpha(a)
                break
            vt += d
        surf.flush()
        enc.stdin.write(bytes(surf.get_data()))
    enc.stdin.close(); enc.wait()


# Mastering : basses renforcées et présence, puis UN SEUL gain pour atteindre le volume standard des réseaux (-14 LUFS)
# et un limiteur rapide qui ne touche que les pointes. Pas de compresseur ni de loudnorm « dynamique » : ils écrasaient
# l'écart de ~10 dB entre la montée et le sommet (mesuré : il ne restait que 2 dB), d'où une musique qui sonnait plate.
EQ = "highpass=f=28,equalizer=f=62:t=q:w=1.1:g=3,equalizer=f=3200:t=q:w=1.4:g=1.5"


def mux(out):
    m = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", out + ".wav", "-af", EQ + ",ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, check=True).stderr
    i_lufs = float(m[m.rindex("I:"):].split()[1])
    gain = max(-20.0, min(20.0, -14.0 - i_lufs))
    af = f"{EQ},volume={gain:.2f}dB,alimiter=limit=0.79:attack=1:release=50:level=false"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out + "_v.mp4", "-i", out + ".wav", "-c:v", "copy",
                    "-af", af, "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", out + ".mp4"], check=True)


def bounces(S, gmap):
    return [(v0 + t - g0, "bounce") for v0, g0, g1 in gmap for t, a, b in S["hits"] if g0 <= t < g1]
