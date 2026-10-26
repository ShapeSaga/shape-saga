"""Moteur de jeu v2 — physique réelle (pymunk), jamais truquée, entièrement déterminée par la graine.
 - les formes TOURNENT : un carré touché par un autre bascule vraiment (moment d'inertie réel, frottement)
 - rebonds naturels : restitution variable, petites rafales aléatoires (pas de vitesse constante imposée)
 - obstacles ANIMÉS : plateformes qui glissent, barres qui tournent (corps cinématiques)
 - le liquide monte jusqu'à 60–100 % du niveau, avec un profil aléatoire (linéaire, accélérant, vagues, à-coups)
 - mode PRISON : cellule qui se resserre, points de vie, dégâts selon l'impact ; la porte s'ouvre quand il n'en reste qu'un."""
import math, random, pymunk
import sim as base

W, H, FPS, SUB = base.W, base.H, base.FPS, base.SUB
SHAPES, SIZE, verts = base.SHAPES, base.SIZE, base.verts
EXIT_Y = 112
LIQ_START = 1880
MASSE = {"square": 1.3, "circle": 1.0, "triangle": .8, "diamond": 1.0}


# ------------------------------------------------------------------ liquide
def profil_liquide(rr):
    return dict(f=rr.uniform(.60, 1.0), T=rr.uniform(10, 17), delay=rr.uniform(1.5, 4.0),
                forme=rr.choice(["lineaire", "accel", "vagues", "surges"]), ph=rr.uniform(0, 6.28))


def liquid_y(t, L):
    u = (t - L["delay"]) / (L["T"] - L["delay"])
    if u <= 0:
        return LIQ_START
    uu = min(u, 1.0)
    g = {"lineaire": uu, "accel": uu ** 1.7, "vagues": uu + .05 * math.sin(6.2832 * 3 * uu + L["ph"]) * 4 * uu * (1 - uu),
         "surges": uu + .045 * math.sin(6.2832 * 4 * uu + L["ph"])}[L["forme"]]
    y = LIQ_START - g * L["f"] * (LIQ_START - EXIT_Y)
    if u > 1:
        y -= (t - L["T"]) * 26                            # il continue de monter doucement : pas d'impasse
    return y


# ------------------------------------------------------------------ obstacles animés
def obstacles_animes(rr, walls, n=None):
    """Plateformes qui glissent et barres qui tournent, placées dans les zones libres du niveau."""
    out, essais = [], 0
    n = rr.choice([2, 3, 3, 4]) if n is None else n
    libre = lambda x0, y0, x1, y1: all(x1 < a - 50 or x0 > c + 50 or y1 < b - 50 or y0 > d + 50 for a, b, c, d in walls if not (a == 0 or c == W))
    while len(out) < n and essais < 80:
        essais += 1
        kind = rr.choice(["slide", "slide", "spin"])
        if kind == "slide":
            w = rr.choice([160, 200, 240]); x = rr.uniform(150, 930 - w); y = rr.uniform(380, 1380); amp = rr.uniform(120, 260)
            if libre(x - amp, y - 20, x + w + amp, y + 40):
                out.append(dict(kind="slide", x=x, y=y, w=w, h=30, ax=amp, ay=0, per=rr.uniform(3.5, 7), ph=rr.uniform(0, 6.28)))
        else:
            L = rr.choice([230, 280, 330]); cx = rr.uniform(260, 820); cy = rr.uniform(420, 1360)
            if libre(cx - L / 2, cy - L / 2, cx + L / 2, cy + L / 2):
                out.append(dict(kind="spin", x=cx, y=cy, w=L, h=26, om=rr.choice([-1, 1]) * rr.uniform(.8, 1.7), ph=rr.uniform(0, 6.28)))
    return out


def _pos_obstacle(o, t):
    if o["kind"] == "slide":
        a = 6.2832 * t / o["per"] + o["ph"]
        return (o["x"] + o["w"] / 2 + o["ax"] * math.sin(a), o["y"] + o["h"] / 2 + o["ay"] * math.sin(a), 0.0,
                o["ax"] * math.cos(a) * 6.2832 / o["per"], 0.0, 0.0)
    return (o["x"], o["y"], o["om"] * t + o["ph"], 0.0, 0.0, o["om"])


# ------------------------------------------------------------------ course
def simulate(seed, walls, anim=None, liq=None):
    rnd = random.Random(seed)
    L = liq or profil_liquide(rnd)
    anim = anim or []
    space = pymunk.Space()
    for x0, y0, x1, y1 in walls:
        sh = pymunk.Poly(space.static_body, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
        sh.elasticity, sh.friction = .95, .15
        space.add(sh)
    movers = []
    for o in anim:
        b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        s = pymunk.Poly.create_box(b, (o["w"], o["h"]))
        s.elasticity, s.friction = 1.0, .2
        space.add(b, s)
        movers.append((o, b))
    elast = rnd.uniform(.92, 1.0)
    speed0 = rnd.uniform(480, 720)
    bodies, pos = [], []
    for i, (_, _, kind) in enumerate(SHAPES):
        while True:
            p = (rnd.uniform(90, 990), rnd.uniform(1580, 1830))
            if all(math.dist(p, q) > 110 for q in pos):
                break
        pos.append(p)
        m = MASSE[kind]
        mom = pymunk.moment_for_circle(m, 0, SIZE) if kind == "circle" else pymunk.moment_for_poly(m, verts(kind))
        b = pymunk.Body(m, mom)
        b.position, b.angle = p, rnd.uniform(0, 6.28)
        b.angular_velocity = rnd.uniform(-5, 5)
        a = rnd.uniform(0, 2 * math.pi)
        b.velocity = (speed0 * math.cos(a), speed0 * math.sin(a))
        sh = pymunk.Circle(b, SIZE) if kind == "circle" else pymunk.Poly(b, verts(kind))
        sh.elasticity, sh.friction = elast, .22
        sh.sid = i
        space.add(b, sh)
        bodies.append(b)
    hits, clock = [], [0.0]

    def begin(arb, sp, data):
        s1, s2 = arb.shapes
        a, b = getattr(s1, "sid", -1), getattr(s2, "sid", -1)
        if a < 0:
            a, b = b, a
        hits.append((clock[0], a, b))
    space.on_collision(begin=begin)
    return _boucle(space, bodies, movers, hits, clock, rnd, seed, L, mode="course")


def _boucle(space, bodies, movers, hits, clock, rnd, seed, L, mode, extra=None):
    state, t_end, ghost = ["alive"] * 4, [None] * 4, [None] * 4
    frames, dt, n = [], 1 / (FPS * SUB), 0
    while clock[0] < 40:
        for _ in range(SUB):
            tnow = clock[0]
            for o, b in movers:
                x, y, ang, vx, vy, om = _pos_obstacle(o, tnow)
                b.position, b.angle, b.velocity, b.angular_velocity = (x, y), ang, (vx, vy), om
            if extra:
                extra["avant"](tnow, space)
            space.step(dt)
            clock[0] += dt
            if n % 8 == 0:                                     # petites rafales : l'imprévu d'une vraie aventure
                for i, b in enumerate(bodies):
                    if state[i] == "alive":
                        b.velocity = (b.velocity.x + rnd.gauss(0, 14), b.velocity.y + rnd.gauss(0, 14))
            for i, b in enumerate(bodies):
                if state[i] != "alive":
                    continue
                v = math.hypot(*b.velocity) or 1
                if v > 840 or v < 380:                         # garde l'action vivante sans figer la vitesse
                    k = (840 if v > 840 else 380) / v
                    b.velocity = (b.velocity.x * k, b.velocity.y * k)
                x, y = b.position
                if mode == "course":
                    if y < EXIT_Y:
                        state[i], t_end[i] = "escaped", clock[0]
                    elif y > liquid_y(clock[0], L):
                        state[i], t_end[i] = "caught", clock[0]
                else:
                    r = extra["verifier"](i, b, clock[0])
                    if r:
                        state[i], t_end[i] = r, clock[0]
                if state[i] != "alive":
                    ghost[i] = (x, y, b.velocity.x, b.velocity.y, b.angle)
                    space.remove(b, *b.shapes)
            n += 1
        t = clock[0]
        fr = []
        for i, b in enumerate(bodies):
            hp = extra["hp"][i] if extra else 100
            if state[i] == "alive":
                fr.append((b.position.x, b.position.y, b.velocity.x, b.velocity.y, "alive", 0, b.angle, hp))
            else:
                x, y, vx, vy, ang = ghost[i]
                age = t - t_end[i]
                if state[i] == "escaped":
                    fr.append((x, y - 620 * age, 0, -620, "escaped", age, ang, hp))
                else:
                    fr.append((x + 25 * math.sin(age * 2), y + 45 * age, 0, 45, "caught", age, ang + age * 2, hp))
        dyn = [(*_pos_obstacle(o, t)[:3], o["w"], o["h"], o["kind"]) for o, _ in movers]
        dyn = [(x, y, w, h, ang, k) for (x, y, ang, w, h, k) in dyn]
        if extra:
            dyn += extra["dyn"](t)
        ly = liquid_y(t, L) if mode == "course" else None
        frames.append((t, ly, fr, dyn))
        if all(s != "alive" for s in state) and t > max(x for x in t_end if x is not None) + 2:
            break
        if extra and extra["fin"](t, state, t_end):
            break
    return dict(seed=seed, frames=frames, hits=hits, state=state, t_end=t_end, mode=mode, liq=L)


# ------------------------------------------------------------------ prison
def simulate_prison(seed):
    """Quatre prisonniers dans une cellule qui se resserre. Chaque choc fait des dégâts selon sa violence et la masse
    de l'autre. Quand il n'en reste qu'un, la porte s'ouvre : il peut sortir."""
    rnd = random.Random(seed)
    space = pymunk.Space()
    cx, cy, w0, h0 = 540, 1010, 760, 1060
    hp = [100.0] * 4
    ouv = {"t": None}
    shrink = rnd.uniform(.16, .26)
    walls = {}
    for nom in ("g", "d", "h", "b"):
        b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        s = pymunk.Poly.create_box(b, (60, h0 + 120) if nom in "gd" else (w0 + 120, 60))
        s.elasticity, s.friction = .95, .15
        space.add(b, s)
        walls[nom] = b
    def taille(t):
        s_ = 1 - shrink * min(1, t / 26)
        return w0 * s_, h0 * s_

    def glisse(t):
        return min(1.0, max(0.0, (t - ouv["t"]) / .8)) if ouv["t"] is not None else 0.0

    def place(t):
        w, h = taille(t)
        r = 0 if t >= 26 else 1
        walls["g"].position = (cx - w / 2 - 30, cy); walls["g"].velocity = (shrink * w0 / 2 / 26 * r, 0)
        walls["d"].position = (cx + w / 2 + 30, cy); walls["d"].velocity = (-shrink * w0 / 2 / 26 * r, 0)
        walls["b"].position = (cx, cy + h / 2 + 30); walls["b"].velocity = (0, -shrink * h0 / 2 / 26 * r)
        walls["h"].position = (cx - 520 * glisse(t), cy - h / 2 - 30)      # le plafond coulisse : c'est la porte
        walls["h"].velocity = (-520 / .8 if 0 < glisse(t) < 1 else 0, shrink * h0 / 2 / 26 * r)

    bodies = []
    for i, (_, _, kind) in enumerate(SHAPES):
        m = MASSE[kind]
        mom = pymunk.moment_for_circle(m, 0, SIZE) if kind == "circle" else pymunk.moment_for_poly(m, verts(kind))
        b = pymunk.Body(m, mom)
        b.position = (cx + rnd.uniform(-250, 250), cy + rnd.uniform(-380, 380))
        b.angle, b.angular_velocity = rnd.uniform(0, 6.28), rnd.uniform(-4, 4)
        a = rnd.uniform(0, 6.28); sp = rnd.uniform(520, 700)
        b.velocity = (sp * math.cos(a), sp * math.sin(a))
        sh = pymunk.Circle(b, SIZE) if kind == "circle" else pymunk.Poly(b, verts(kind))
        sh.elasticity, sh.friction = .95, .25
        sh.sid = i
        space.add(b, sh)
        bodies.append(b)
    hits, clock = [], [0.0]

    def begin(arb, sp, data):
        s1, s2 = arb.shapes
        a, b = getattr(s1, "sid", -1), getattr(s2, "sid", -1)
        hits.append((clock[0], a, b))
        if a >= 0 and b >= 0 and hp[a] > 0 and hp[b] > 0:
            n = arb.normal
            rel = abs((s1.body.velocity - s2.body.velocity).dot(n))
            imp = min(1.4, rel / 620)
            ma, mb = s1.body.mass, s2.body.mass
            hp[a] = max(0, hp[a] - 24 * imp * (2 * mb / (ma + mb)))
            hp[b] = max(0, hp[b] - 24 * imp * (2 * ma / (ma + mb)))
    space.on_collision(begin=begin)
    place(0)

    def verifier(i, b, t):
        if hp[i] <= 0:
            return "caught"
        if ouv["t"] is not None and b.position.y < cy - taille(t)[1] / 2 - 60:
            return "escaped"
        vivants = [k for k in range(4) if hp[k] > 0]
        if len(vivants) == 1 and ouv["t"] is None:
            ouv["t"] = t + .8
        return None

    def dyn(t):
        w, h = taille(t)
        g = glisse(t)
        return [(cx - w / 2 - 30, cy, 60, h + 120, 0.0, "cellule"), (cx + w / 2 + 30, cy, 60, h + 120, 0.0, "cellule"),
                (cx, cy + h / 2 + 30, w + 120, 60, 0.0, "cellule"), (cx - 520 * g, cy - h / 2 - 30, w + 120, 60, 0.0, "porte")]

    def avant(t, sp):
        place(t)

    def fin(t, state, t_end):
        vivants = sum(1 for s in state if s == "alive")
        return (vivants == 0 and t > max(x for x in t_end if x is not None) + 1.5)

    extra = dict(avant=avant, verifier=verifier, dyn=dyn, fin=fin, hp=hp)
    S = _boucle(space, bodies, [], hits, clock, rnd, seed, None, "prison", extra)
    return S
