"""Jeu neutre : 4 formes rebondissent à vitesse constante, un liquide violet monte, une sortie en haut.
Physique réelle (pymunk), jamais modifiée. La graine est enregistrée."""
import math, random, pymunk

W, H = 1080, 1920
FPS, SUB = 30, 4                      # 30 images/s, 4 pas de physique par image (120 Hz)
SPEED = 620                           # vitesse constante des formes (px/s)
LIQ_START, LIQ_DELAY, LIQ_SPEED = 1880, 3.0, 40
EXIT_Y = 112
T_MAX = 40

WALLS = [(0, 0, 40, H), (1040, 0, W, H), (0, 1880, W, H),
         (0, 120, 450, 156), (630, 120, W, 156),                       # plafond, sortie 450-630
         (40, 1500, 700, 1536), (920, 1500, 1040, 1536),
         (40, 1020, 140, 1056), (360, 1020, 1040, 1056),
         (40, 580, 600, 616), (820, 580, 1040, 616),
         (480, 1260, 600, 1300), (760, 1180, 820, 1260), (300, 780, 420, 820), (820, 300, 880, 360), (200, 330, 260, 390)]

# id : (nom, couleur, forme)
SHAPES = [("RED", (0.91, 0.20, 0.17), "square"), ("GREEN", (0.20, 0.72, 0.30), "circle"),
          ("BLUE", (0.20, 0.50, 0.92), "triangle"), ("YELLOW", (0.98, 0.78, 0.12), "diamond")]
SIZE = 34


def liquid_y(t):
    return LIQ_START - max(0.0, t - LIQ_DELAY) * LIQ_SPEED


def verts(kind, s=SIZE):
    if kind == "square":
        return [(-s, -s), (s, -s), (s, s), (-s, s)]
    if kind == "triangle":
        return [(0, -s * 1.15), (s * 1.1, s * .8), (-s * 1.1, s * .8)]
    if kind == "diamond":
        return [(0, -s * 1.2), (s * 1.0, 0), (0, s * 1.2), (-s * 1.0, 0)]
    return None


def simulate(seed):
    rnd = random.Random(seed)
    space = pymunk.Space()
    for x0, y0, x1, y1 in WALLS:
        sh = pymunk.Poly(space.static_body, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
        sh.elasticity, sh.friction = 1.0, 0.0
        space.add(sh)
    bodies, pos = [], []
    for i, (_, _, kind) in enumerate(SHAPES):
        while True:
            p = (rnd.uniform(90, 990), rnd.uniform(1580, 1830))
            if all(math.dist(p, q) > 110 for q in pos):
                break
        pos.append(p)
        b = pymunk.Body(1, float("inf"))
        b.position = p
        a = rnd.uniform(0, 2 * math.pi)
        b.velocity = (SPEED * math.cos(a), SPEED * math.sin(a))
        sh = pymunk.Circle(b, SIZE) if kind == "circle" else pymunk.Poly(b, verts(kind))
        sh.elasticity, sh.friction = 1.0, 0.0
        sh.sid = i
        space.add(b, sh)
        bodies.append(b)

    hits = []                                             # (t, a, b) ; b = -1 pour un mur
    clock = [0.0]

    def begin(arb, sp, data):
        s1, s2 = arb.shapes
        a, b = getattr(s1, "sid", -1), getattr(s2, "sid", -1)
        if a < 0:
            a, b = b, a
        hits.append((clock[0], a, b))
    space.on_collision(begin=begin)

    state = ["alive"] * 4                                 # alive / caught / escaped
    t_end = [None] * 4
    ghost = [None] * 4                                    # position/vitesse au moment de la sortie du jeu
    frames = []
    dt = 1 / (FPS * SUB)
    n = 0
    while clock[0] < T_MAX:
        for _ in range(SUB):
            space.step(dt)
            clock[0] += dt
            for i, b in enumerate(bodies):
                if state[i] != "alive":
                    continue
                vx, vy = b.velocity
                v = math.hypot(vx, vy) or 1
                vx, vy = vx / v * SPEED, vy / v * SPEED
                m = .3 * SPEED                            # évite les rebonds parfaitement horizontaux/verticaux
                if abs(vx) < m:
                    vx = math.copysign(m, vx or 1)
                if abs(vy) < m:
                    vy = math.copysign(m, vy or 1)
                v = math.hypot(vx, vy)
                b.velocity = (vx / v * SPEED, vy / v * SPEED)
                x, y = b.position
                if y < EXIT_Y:
                    state[i], t_end[i] = "escaped", clock[0]
                elif y > liquid_y(clock[0]):
                    state[i], t_end[i] = "caught", clock[0]
                if state[i] != "alive":
                    ghost[i] = (x, y, b.velocity.x, b.velocity.y)
                    space.remove(b, *b.shapes)
        n += 1
        t = clock[0]
        fr = []
        for i, b in enumerate(bodies):
            if state[i] == "alive":
                fr.append((b.position.x, b.position.y, b.velocity.x, b.velocity.y, "alive", 0))
            else:
                x, y, vx, vy = ghost[i]
                age = t - t_end[i]
                if state[i] == "escaped":
                    fr.append((x, y - SPEED * age, 0, -SPEED, "escaped", age))
                else:
                    fr.append((x + 25 * math.sin(age * 2), y + 45 * age, 0, 45, "caught", age))
        frames.append((t, liquid_y(t), fr))
        if all(s != "alive" for s in state) and t > max(t_end) + 2:
            break
    return dict(seed=seed, frames=frames, hits=hits, state=state, t_end=t_end)


def sacrifice(sim):
    """Cherche dans la VRAIE course : Rouge touche Vert près du liquide, Vert s'en sort, Rouge est englouti."""
    st, te = sim["state"], sim["t_end"]
    if st[0] != "caught" or st[1] != "escaped" or max(x for x in te if x) > 32:
        return None
    tr, tg = te[0], te[1]
    best = None
    for t, a, b in sim["hits"]:
        if {a, b} != {0, 1} or t < 7 or t > tr or tr - t > 5:
            continue
        fr = sim["frames"][min(int(t * FPS), len(sim["frames"]) - 1)]
        ly, s = fr[1], fr[2]
        if ly - max(s[0][1], s[1][1]) > 380 or s[1][3] > 0:   # près du liquide, Vert repart vers le haut
            continue
        score = tr - t
        if best is None or score < best[0]:
            best = (score, t)
    if not best:
        return None
    return dict(t_hit=best[1], t_red=tr, t_green=tg)


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    stats, found = {}, []
    for seed in range(n):
        s = simulate(seed)
        k = tuple(s["state"][:2])
        stats[k] = stats.get(k, 0) + 1
        h = sacrifice(s)
        if h:
            found.append((seed, h))
    print(stats)
    for f in found[:15]:
        print(f)
