"""Générateur d'épisodes Shape Saga (v4).
Usage : python generateur.py NUMERO DOSSIER_SORTIE
Un numéro = un épisode, toujours identique. Deux modes de jeu : COURSE (le liquide monte, obstacles animés) et PRISON (points de vie).
Sept histoires repérées dans de vraies parties : dernier, presque, duel, sacrifice, trahison, ensemble (union), prison (champion)."""
import sys, os, json, random
import sim, sim2, niveaux, detecteurs, monteur, musique, panneaux, effets, artisanal, murs
import animaux

ICI = os.path.dirname(os.path.abspath(__file__))
ORDRE = ["dernier", "murs", "prison", "sacrifice", "presque", "murs", "trahison", "duel", "ensemble", "murs", "prison", "presque", "sacrifice", "murs",
         "dernier", "duel", "trahison", "ensemble"]   # « murs » = Duel de murs (4 vidéos sur 18)
TOUS = ["etages", "cheminee", "plinko", "escaliers", "piliers", "labyrinthe"]
CONF = dict(
    dernier=dict(tmax=19.3, niveaux=TOUS, styles=["orchestral", "guerre", "electro"]),
    presque=dict(tmax=19.0, niveaux=["cheminee", "plinko", "escaliers", "piliers", "labyrinthe"], styles=["melancolie", "thriller"]),
    duel=dict(tmax=18.5, niveaux=["escaliers", "cheminee", "piliers", "plinko"], styles=["thriller", "electro", "guerre"]),
    sacrifice=dict(tmax=18.0, niveaux=TOUS, styles=["melancolie", "orchestral", "espoir"]),
    trahison=dict(tmax=18.5, niveaux=TOUS, styles=["thriller", "electro"]),
    ensemble=dict(tmax=22.0, niveaux=TOUS, styles=["espoir", "orchestral", "guerre"]),
    prison=dict(tmax=19.5, niveaux=None, styles=["guerre", "thriller", "electro"]),
)
# Accroche affichée en haut de l'écran pendant toute la partie ({C} = couleur du héros, {R} = l'autre forme de l'histoire).
# Pas d'émoji : les polices des serveurs GitHub ne savent pas les dessiner.
ACCROCHES = dict(
    dernier=["Only one of them makes it out", "{C} refused to give up", "3 fell. {C} kept climbing", "Nobody expected {C} to survive",
             "Watch {C} until the end"],
    presque=["{C} was SO close...", "This one hurts", "The exit was RIGHT there", "{C} almost had it...", "Don't blink at the end"],
    duel=["{C} vs {R}: only one gets out", "Photo finish incoming", "{R} was right behind...", "Pick a side: {C} or {R}?", "Closest race ever?"],
    sacrifice=["{R} gave everything for {C}", "Real friends do THIS", "Not every hero escapes", "{R} didn't have to do that..."],
    trahison=["{C} betrayed {R}", "{R} got backstabbed", "Never trust {C}", "{C} chose violence", "Friendship? Not today"],
    ensemble=["Nobody gets left behind", "Teamwork or nothing", "They escaped TOGETHER", "This is what friends do"],
    prison=["4 enter. 1 leaves.", "Only the last one gets out", "{C} showed no mercy", "Prison fight: who wins?", "The walls are closing in"],
)
RARES = ("sacrifice", "trahison", "ensemble", "duel")
TRANSITIONS = ["impact", "glisse", "iris", "zoom", "tourne", "coupe"]

TITRES = dict(
    presque=["{animal}: So Close to the Exit", "The {animal} Who Almost Made It", "One Step Short: The Story of a {animal}",
             "{animal}'s Last Climb", "So Close, {animal}... So Close", "The Exit Was Right There", "A {animal} Against the Flood",
             "The Climb That Almost Worked", "Almost Free: {animal}", "When the {animal} Reached for the Light"],
    duel=["{animal} vs {rival}: Photo Finish", "Rivals at the Top: {animal} and {rival}", "{animal} Beats {rival} by a Heartbeat",
          "The Race Between {animal} and {rival}", "Only One Exit: {animal} or {rival}?", "{rival} Was Right Behind",
          "The Closest Race Yet: {animal} vs {rival}", "{animal} and {rival}: Who Escapes?"],
    sacrifice=["The {animal} Who Gave Everything", "{animal}'s Sacrifice", "A Friend Lifted {rival} Out", "The Last Gift of a {animal}",
               "{animal} Saved {rival}", "Why the {animal} Let Go", "The Hero Who Stayed Behind"],
    trahison=["{animal} Pushed {rival}", "The Betrayal at the Top", "{animal}'s Dark Choice", "Was It Fair, {animal}?",
              "Only One Left: {animal} and {rival}", "{rival} Never Saw It Coming", "The Push That Changed Everything"],
    ensemble=["Together: {animal} and Friends Escape", "Nobody Left Behind", "How {animal} Made It Out With Friends",
              "The Escape That Needed Everyone", "Four Friends, One Exit", "United at the Top"],
    prison=["{animal}: The Last One Standing", "Four Entered. {animal} Left.", "The Prison Fight: {animal} Wins", "{animal} Walks Out Alone",
            "Battle in the Cell: {animal}", "The Door Opens for {animal}", "No Mercy in the Prison"],
)
LEGENDES = dict(
    presque=["Have you ever come this close to something? Tell me below.", "The {animal} gave everything. Would you have made it?",
             "Falling short still counts as trying. Agree?", "So close! What would you have done differently?",
             "Some climbs end before the top. What's your toughest almost?", "Who deserved to win this one?"],
    duel=["The {animal} or the {rival}? Who did you root for?", "Half a second decided it. Who do you think wins the rematch?",
          "A true rivalry. Are you team {animal} or team {rival}?", "Photo finish! Did you see it coming?",
          "One escapes, one doesn't. Was it fair?", "Rematch? Tell me who should race next."],
    sacrifice=["Would you have done the same for a friend?", "The {animal} gave everything. Who deserves a rematch?",
               "Real friends lift you up. Who lifted you?", "Heroes don't always get to escape. Do you agree?"],
    trahison=["Betrayal or survival? What would you do?", "Was the {animal} a villain or just scared?",
              "Only one could leave. Do you forgive the {animal}?", "Team {animal} or team {rival}?"],
    ensemble=["Together is stronger. Tag someone who never leaves you behind.", "Four friends, one exit, zero left behind. Your favorite moment?",
              "Who carried who here? Tell me below.", "Teamwork wins. Do you agree?"],
    prison=["Only one door. Who would you bet on next time?", "The {animal} won the cell. Who should fight next?",
            "Last one standing! Would you survive the prison?", "Which animal should enter the cell next?"],
)


def charger(nom):
    return json.load(open(os.path.join(ICI, "data", nom), encoding="utf-8"))


LIQ_MIN = 0.60   # demande de Chahine : au moment décisif, le danger a monté d'au moins 60 % du niveau


def niveau_liquide(S):
    """Part du niveau (0..1) recouverte par le liquide au moment où la dernière forme sort ou tombe."""
    fins = [t for t in S["t_end"] if t is not None]
    t = max(fins) if fins else S["frames"][-1][0]
    return (sim2.LIQ_START - sim2.liquid_y(t, S["liq"])) / (sim2.LIQ_START - sim2.EXIT_Y)


def chercher(scen, numero, rnd):
    """Cherche une vraie partie qui raconte ce scénario (niveau, obstacles et liquide tirés au hasard)."""
    conf, det, cible, n = CONF[scen], detecteurs.DETECTEURS[scen], numero % 4, 0
    relax = 700 if scen in RARES else 2500
    tour = 0
    while n < 60000:
        if scen == "prison":
            depart = rnd.randrange(10 ** 6)
            for k in range(300):
                S = sim2.simulate_prison(depart + k); n += 1
                ev = det(S, conf["tmax"])
                if ev and (n > relax or ev["hero"] == cible):
                    return "prison", 0, depart + k, S, ev, [], []
            continue
        # niveau en rotation (anti-répétition) : deux épisodes qui se suivent n'ont pas la même architecture
        arch, gn = conf["niveaux"][(numero * 5 + tour) % len(conf["niveaux"])], rnd.randrange(10 ** 6)
        tour += 1
        walls = niveaux.generer(arch, gn)
        anim = sim2.obstacles_animes(random.Random(gn + 1), walls)
        depart = rnd.randrange(10 ** 6)
        for k in range(2500 if tour == 1 else 400):   # on insiste sur le niveau du tour (variété) avant de changer
            S = sim2.simulate(depart + k, walls, anim); n += 1
            ev = det(S, conf["tmax"])
            if ev and niveau_liquide(S) >= LIQ_MIN and (n > relax or ev["hero"] == cible):
                return arch, gn, depart + k, S, ev, walls, anim
    raise RuntimeError("aucune histoire trouvée")


def faire_tension(S, gmap, tfin):
    """Tension (0..1) tirée de la vraie partie : le liquide est-il près des formes ? (prison : qui reste-t-il, avec combien de vie ?)"""
    def f(vt):
        for v0, g0, g1 in gmap:
            if v0 <= vt < v0 + (g1 - g0):
                gt = g0 + vt - v0
                fr = S["frames"][min(int(gt * 30), len(S["frames"]) - 1)]
                vivants = [x for x in fr[2] if x[4] == "alive"]
                if fr[1] is None:
                    pv = min((x[7] for x in vivants), default=100)
                    return min(1, (4 - len(vivants)) * .22 + (1 - pv / 100) * .45 + .1)
                dist = fr[1] - max((x[1] for x in vivants), default=fr[1] - 400)
                return min(1, max(0, 1 - dist / 900)) * .65 + min(1, gt / max(tfin, 1)) * .35
        return .55
    return f


def maj(t):
    return t[:1].upper() + t[1:]


def hash_nom(s):
    return sum((i + 1) * ord(ch) for i, ch in enumerate(s)) % 997


def generer(numero, sortie):
    rnd = random.Random(numero * 7919 + 13)
    scen = ORDRE[numero % len(ORDRE)]
    if scen == "murs":
        return generer_murs(numero, sortie, rnd)
    conf = CONF[scen]
    T, TP, TH = charger("textes.json"), charger("textes_plus.json"), charger("themes.json")["themes"]
    arch, gniv, seed, S, ev, walls, anim = chercher(scen, numero, rnd)
    sim.WALLS = walls
    hero = ev["hero"]
    cast = []
    for i in range(4):   # casting en rotation : chaque forme parcourt tous ses animaux avant d'en revoir un
        forme = sim.SHAPES[i][2]
        liste = sorted(n for n, d in animaux.ANIMAUX.items() if d["forme"] == forme)
        random.Random(forme).shuffle(liste)
        cast.append(liste[(numero + 3 * i) % len(liste)])
    cols = [sim.SHAPES[i][1] for i in range(4)]
    nom_h = cast[hero]
    if scen == "prison":
        th_nom, theme = "prison", {}
    else:
        ordre_th = sorted(TH)
        random.Random(2026).shuffle(ordre_th)
        th_nom = ordre_th[numero % len(ordre_th)]   # décor en rotation : jamais deux fois de suite
        theme = {k: tuple(v) for k, v in TH[th_nom].items() if k != "nom_en"}
    theme["_nom"] = th_nom
    theme["_graine"] = rnd.randrange(1, 10 ** 5)
    gr = lambda: rnd.randrange(10 ** 6)
    trans = lambda: rnd.choice(TRANSITIONS)
    P, PAN, fonds = {}, {}, {}
    cle_cadre = {"prison": "prison_cadre", "ensemble": "ensemble_cadre"}.get(scen, "cadre_intro")
    cadre = rnd.choice(TP[cle_cadre])
    fonds["intro"] = rnd.choice(["coucher", "etoiles", "aube"] if scen == "prison" else ["aube", "sakura", "coucher", "etoiles", "soleil"])
    P["intro"] = panneaux.p_intro(cast, cols, theme, cadre, fonds["intro"], gr()) + ("coupe",)
    PAN["intro"] = 1.7
    morale = rnd.choice(T["morales"])
    cle_card = rnd.choice(["aube", "sakura", "plumes", "coucher"])
    fond_fin = rnd.choice(effets.SCENES["fin"])

    if scen == "dernier":
        (t1, _), (t2, _), (t3, _) = ev["falls"]; tE = ev["t_fin"]
        amis = [(cast[i], cols[i]) for _, i in ev["falls"]]
        PAN.update(chute=1.9, defi=1.9, fin=2.3, card=2.3)
        seq = [("panel", "intro"), ("game", 0, t2 + .3), ("panel", "chute"), ("game", t2 + .3, t3 + .3), ("panel", "defi"),
               ("game", t3 + .3, tE + .4), ("panel", "fin"), ("panel", "card")]
        fonds.update(chute=rnd.choice(effets.SCENES["chute"]), defi=rnd.choice(effets.SCENES["defi"]), fin=fond_fin)
        P["chute"] = panneaux.p_notyou(nom_h, cols[hero], theme, rnd.choice(T["repliques"]["friend_falls_2"]), fonds["chute"], gr()) + ("impact",)
        P["defi"] = panneaux.p_notdone(nom_h, cols[hero], theme, rnd.choice(T["repliques"]["defiant"]), fonds["defi"], gr()) + (trans(),)
        P["fin"] = panneaux.p_forall(nom_h, cols[hero], theme, rnd.choice(T["repliques"]["after_escape"]), amis, fonds["fin"], gr()) + (trans(),)
        evts, shake = {"climax": tE}, ("chute",)
    elif scen == "presque":
        t_h = ev["t_fin"]; ta = max(3.0, ev["t_top"] - .3)
        if ta > t_h - .6:
            ta = t_h - .6
        amis = [(cast[i], cols[i]) for i in range(4) if i != hero]
        PAN.update(espoir=1.9, chute=2.2, adieu=2.5, card=2.3)
        seq = [("panel", "intro"), ("game", 0, ta), ("panel", "espoir"), ("game", ta, t_h + .35), ("panel", "chute"), ("panel", "adieu"), ("panel", "card")]
        fonds.update(espoir=rnd.choice(["aube", "soleil", "sakura"]), chute=rnd.choice(["vitre", "pluie", "vitesse"]), adieu=rnd.choice(["coucher", "plumes", "etoiles", "sakura"]))
        P["espoir"] = panneaux.p_espoir(nom_h, cols[hero], theme, rnd.choice(TP["espoir"]), fonds["espoir"], gr()) + (trans(),)
        P["chute"] = panneaux.p_presque(nom_h, cols[hero], theme, rnd.choice(TP["presque_chute"]), fonds["chute"], gr()) + ("impact",)
        P["adieu"] = panneaux.p_adieu(nom_h, cols[hero], theme, rnd.choice(TP["adieu"]), amis, fonds["adieu"], gr()) + ("iris",)
        evts, shake = {"climax": t_h}, ("chute",)
    elif scen in ("duel", "trahison", "prison"):
        tE = ev["t_fin"]; riv = ev["rival"]
        if scen == "duel":
            ta = max(2.5, tE - 3.0)
        elif scen == "trahison":
            ta = max(2.5, ev["t_hit"] - .7)
        else:
            ta = max(3.0, ev["t_dernier"] - 1.3)
        amis = [(cast[i], cols[i]) for i in range(4) if i != hero]
        PAN.update(duel=2.4, fin=2.3, card=2.2)
        seq = [("panel", "intro"), ("game", 0, ta), ("panel", "duel"), ("game", ta, tE + .4), ("panel", "fin")]
        if scen != "prison":
            PAN["perdant"] = 2.2
            seq.append(("panel", "perdant"))
        seq.append(("panel", "card"))
        if scen == "duel":
            fonds.update(duel=rnd.choice(["eclair", "vitesse", "onde", "aura"]), perdant=rnd.choice(["pluie", "coucher", "plumes"]))
            P["duel"] = panneaux.p_duel(nom_h, cols[hero], cast[riv], cols[riv], theme, rnd.choice(TP["hero_defi"]), rnd.choice(TP["rival_defi"]), fonds["duel"], gr()) + ("impact",)
            P["fin"] = panneaux.p_forall(nom_h, cols[hero], theme, rnd.choice(TP["vainqueur"]), amis, fond_fin, gr()) + (trans(),)
            P["perdant"] = panneaux.p_perdant(cast[riv], cols[riv], theme, rnd.choice(TP["perdant"]), fonds["perdant"], gr()) + ("glisse",)
        elif scen == "trahison":
            fonds.update(duel=rnd.choice(["eclair", "vitre", "vitesse"]), perdant=rnd.choice(["pluie", "coucher"]))
            P["duel"] = panneaux.p_duel(nom_h, cols[hero], cast[riv], cols[riv], theme, rnd.choice(TP["trahison_hero"]), rnd.choice(TP["trahison_victime"]),
                                        fonds["duel"], gr(), "determined", "scared") + ("impact",)
            P["fin"] = panneaux.p_forall(nom_h, cols[hero], theme, rnd.choice(TP["trahison_fin"]), amis, rnd.choice(["coucher", "pluie"]), gr()) + (trans(),)
            P["perdant"] = panneaux.p_perdant(cast[riv], cols[riv], theme, rnd.choice(TP["trahison_victime"]), fonds["perdant"], gr()) + ("glisse",)
        else:
            fonds.update(duel=rnd.choice(["eclair", "vitesse", "onde", "aura", "explosion"]))
            P["duel"] = panneaux.p_duel(nom_h, cols[hero], cast[riv], cols[riv], theme, rnd.choice(TP["prison_defi"]), rnd.choice(TP["prison_perdu"]),
                                        fonds["duel"], gr()) + ("impact",)
            P["fin"] = panneaux.p_forall(nom_h, cols[hero], theme, rnd.choice(T["repliques"]["after_escape"]), [(cast[i], cols[i]) for i in ev["morts"]], fond_fin, gr()) + (trans(),)
        evts, shake = {"climax": tE}, ("duel",)
    elif scen == "sacrifice":
        tE = ev["t_fin"]; ben = ev["ben"]
        ta = max(2.5, ev["t_hit"] - .8)
        autres = [(cast[i], cols[i]) for i in range(4) if i not in (hero, ben)]
        PAN.update(lien=2.4, adieu=2.5, fin=2.3, card=2.2)
        seq = [("panel", "intro"), ("game", 0, ta), ("panel", "lien"), ("game", ta, tE + .4), ("panel", "adieu"), ("panel", "fin"), ("panel", "card")]
        fonds.update(lien=rnd.choice(["aube", "coucher", "sakura", "plumes"]), adieu=rnd.choice(["plumes", "etoiles", "coucher"]))
        P["lien"] = panneaux.p_duel(cast[ben], cols[ben], nom_h, cols[hero], theme, rnd.choice(TP["sacrifice_ben"]), rnd.choice(TP["sacrifice_hero"]),
                                    fonds["lien"], gr(), "scared", "determined") + ("impact",)
        P["adieu"] = panneaux.p_adieu(nom_h, cols[hero], theme, rnd.choice(TP["sacrifice_adieu"]), [(cast[ben], cols[ben])] + autres, fonds["adieu"], gr()) + ("iris",)
        P["fin"] = panneaux.p_forall(cast[ben], cols[ben], theme, rnd.choice(T["repliques"]["thanks"]), [(nom_h, cols[hero])] + autres, fond_fin, gr()) + (trans(),)
        evts, shake = {"climax": tE}, ("lien",)
    else:  # ensemble
        tE = ev["t_fin"]
        hs = ev["heros"]
        PAN.update(union=2.7, card=2.2)
        seq = [("panel", "intro"), ("game", 0, tE + .4), ("panel", "union"), ("panel", "card")]
        fonds.update(union=rnd.choice(["soleil", "aube", "sakura", "plumes"]))
        P["union"] = panneaux.p_union([cast[i] for i in hs], [cols[i] for i in hs], theme, rnd.choice(TP["ensemble"]), fonds["union"], gr()) + ("zoom",)
        evts, shake = {"climax": tE}, ()
    P["card"] = panneaux.p_card(morale, cle_card, gr()) + ("zoom",)

    for k, v in list(P.items()):
        base, bulles, style = v
        base2 = artisanal.appliquer(base, 100 + hash_nom(k) + numero, 1.0, True)
        bulles2 = [(artisanal.appliquer(b, 300 + hash_nom(k) + numero, .8, False), d, pos) for (b, d, pos) in bulles]
        P[k] = (base2, bulles2, style)
    autre = ev.get("rival", ev.get("ben", hero))
    nomc = lambda i: sim.SHAPES[i][0].title()
    accroche = random.Random(numero * 31 + 7).choice(ACCROCHES[scen]).format(C=nomc(hero), R=nomc(autre))
    marks, gmap, total = monteur.timeline(seq, PAN, evts)
    os.makedirs(sortie, exist_ok=True)
    ep = "EP%03d" % numero
    out = os.path.join(sortie, ep)
    monteur.render(S, seq, PAN, P, theme, out, shake_names=shake, accroche=accroche)

    climax = marks["climax"]
    tension = faire_tension(S, gmap, ev["t_fin"])
    style = rnd.choice(conf["styles"])
    mk = lambda k: marks.get(k, climax)
    if scen == "dernier":
        arc = [(0, mk("chute"), "tendu"), (mk("chute"), mk("chute") + 1.9, "sombre"), (mk("chute") + 1.9, mk("defi"), "tendu"), (mk("defi"), climax, "puissance"), (climax, total, "triomphe")]
        hits, risers, drame = [(mk("chute"), "sting"), (mk("defi"), "braam"), (mk("fin"), "piano")], [mk("chute"), mk("defi")], False
    elif scen == "presque":
        arc = [(0, mk("espoir"), "tendu"), (mk("espoir"), climax, "tendu"), (climax, mk("adieu"), "sombre"), (mk("adieu"), total, "sad")]
        hits, risers, drame = [(mk("adieu"), "piano")], [mk("espoir")], True
    elif scen == "duel":
        arc = [(0, mk("duel"), "tendu"), (mk("duel"), climax, "puissance"), (climax, mk("perdant"), "triomphe"), (mk("perdant"), total, "sad")]
        hits, risers, drame = [(mk("duel"), "braam"), (mk("perdant"), "piano")], [mk("duel")], False
    elif scen == "trahison":
        arc = [(0, mk("duel"), "tendu"), (mk("duel"), climax, "puissance"), (climax, mk("perdant"), "sombre"), (mk("perdant"), total, "sad")]
        hits, risers, drame = [(mk("duel"), "sting"), (mk("perdant"), "piano")], [mk("duel")], True
    elif scen == "prison":
        arc = [(0, mk("duel"), "tendu"), (mk("duel"), climax, "puissance"), (climax, total, "triomphe")]
        hits, risers, drame = [(mk("duel"), "braam"), (mk("fin"), "piano")], [mk("duel")], False
    elif scen == "sacrifice":
        arc = [(0, mk("lien"), "tendu"), (mk("lien"), climax, "puissance"), (climax, mk("adieu"), "triomphe"), (mk("adieu"), total, "sad")]
        hits, risers, drame = [(mk("lien"), "sting"), (mk("adieu"), "piano")], [mk("lien")], False
    else:
        arc = [(0, climax, "tendu"), (climax, total, "triomphe")]
        hits, risers, drame = [(mk("union"), "piano")], [climax], False
    sfx = monteur.bounces(S, gmap)
    info_m = musique.composer(dict(_risers=risers), sfx, total, out + ".wav", style, arc, tension, hits, climax, numero * 31 + 7, drame)
    monteur.mux(out)
    for f in (out + "_v.mp4", out + ".wav"):
        os.remove(f)

    a_en = animaux.ANIMAUX[nom_h]["nom_en"]
    r_idx = ev.get("rival", ev.get("ben"))
    r_en = animaux.ANIMAUX[cast[r_idx]]["nom_en"] if r_idx is not None else ""
    if scen == "dernier":
        titre = maj(rnd.choice(T["titres"]).format(animal=a_en.title()))
        legende = maj(rnd.choice(T["legendes"]).format(animal=a_en))
    else:
        titre = maj(rnd.choice(TITRES[scen]).format(animal=a_en.title(), rival=r_en.title()))
        legende = maj(rnd.choice(LEGENDES[scen]).format(animal=a_en, rival=r_en))
    mention = rnd.choice(T["mention_ia"])
    tags = list(rnd.choice(T["hashtags"]))
    meta = dict(id=ep, titre=titre, legende=f"{legende}\n\n{mention}",
                youtube_description=f"{legende}\n\n{mention}\nEvery Shape Has a Story.", hashtags=tags, test=False,
                _info=dict(accroche=accroche, scenario=scen, mode=S.get("mode"), niveau=arch, niveau_graine=gniv, seed=seed, animal=nom_h, casting=cast, theme=th_nom,
                           liquide=(S.get("liq") or {}), obstacles=len(anim), fonds=fonds, musique=info_m, morale=morale, duree=round(total, 1),
                           marks={k: round(v, 1) for k, v in marks.items()}))
    json.dump(meta, open(out + ".json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return meta


# ------------------------------------------------------------------ Duel de murs
PAIRES = [(0, 2), (1, 3), (0, 1), (2, 3), (0, 3), (1, 2)]          # quelles deux formes s'affrontent (en rotation)
MURS_TXT = dict(
    defi_bas=["Bet you can't\nget past me.", "This board\nis MINE.", "Ready to lose?", "One wall\nat a time.", "Try and stop me!"],
    defi_haut=["You? Beat ME?", "I'll box you in!", "Not a chance!", "Say goodbye\nto your path.", "Watch this."],
    piege=["A WALL?!\nSERIOUSLY?!", "NOT\nTHIS WALL!", "WHERE DO\nI GO NOW?!", "YOU TRAPPED\nME!"],
    relance=["MY TURN\nNOW!", "NOT DONE\nYET!", "WATCH\nTHIS!"],
    gagne=["TOO\nEASY!", "WHO'S THE\nMASTER NOW?", "CHECKMATE!", "SEE YOU\nNEVER!"],
)
ACC_MURS = dict(
    photo=["{C} won by ONE step", "Closest finish ever?", "{R} was one move away...", "{C} vs {R}: down to the last move"],
    retournement=["{R} was winning... until this", "Never celebrate too early", "{C} came back from nowhere", "Pro vs Master?"],
    piege=["{R} got trapped", "{R} got cyberbullied", "That wall was personal", "{C} built a prison for {R}"],
    domination=["{R} got cyberbullied", "{C} vs {R}: total domination", "{R} never stood a chance", "Pro vs Noob?"],
)
TITRES_MURS = ["{animal} vs {rival}: The Wall Duel", "{animal} Walled {rival} In", "One Wall Too Many for {rival}",
               "{animal} and {rival}: Who Gets Through?", "The {animal} Who Built a Maze", "Trapped by the {animal}"]
LEGENDES_MURS = ["Which color would you play? Tell me below.", "Would you have placed that wall? Tell me below.",
                 "Team {animal} or team {rival}?", "Best move of the game? Comment the moment.", "Who should play the rematch?"]


def generer_murs(numero, sortie, rnd):
    """Un épisode « Duel de murs » : vraie partie entre deux IA, planches manga aux moments forts."""
    T, TH = charger("textes.json"), charger("themes.json")["themes"]
    # k = rang de cet épisode parmi les duels : histoire, plateau et formes tournent sans se suivre au même rythme
    k_duel = (numero // len(ORDRE)) * ORDRE.count("murs") + [i for i, s in enumerate(ORDRE) if s == "murs"].index(numero % len(ORDRE))
    histoire = murs.HISTOIRES[k_duel % len(murs.HISTOIRES)]
    depart, ev, S = rnd.randrange(10 ** 6), None, None
    for k in range(20000):
        S = murs.simulate(depart + k)
        ev = murs.detecter(S, histoire)
        if ev and S["t_fin"] <= 17.5:
            break
    else:
        raise RuntimeError("aucune partie trouvée pour " + histoire)
    idx = PAIRES[k_duel % len(PAIRES)]               # joueur 0 (part du bas) et joueur 1 (part du haut) -> formes du jeu
    cast = {}
    for i in idx:
        forme = sim.SHAPES[i][2]
        liste = sorted(n for n, d in animaux.ANIMAUX.items() if d["forme"] == forme)
        random.Random(forme).shuffle(liste)
        cast[i] = liste[(numero + 3 * i) % len(liste)]
    col = {i: sim.SHAPES[i][1] for i in idx}
    g, p = idx[ev["hero"]], idx[ev["rival"]]
    look = list(murs.LOOKS)[(k_duel + k_duel // 4) % len(murs.LOOKS)]
    ordre_th = sorted(TH); random.Random(2026).shuffle(ordre_th)
    th_nom = ordre_th[numero % len(ordre_th)]
    theme = {k: tuple(v) for k, v in TH[th_nom].items() if k != "nom_en"}
    theme.update(_nom="murs-" + look, _graine=rnd.randrange(1, 10 ** 5), _look=look,
                 _joueurs=tuple((sim.SHAPES[i][2], sim.SHAPES[i][1]) for i in idx))
    gr = lambda: rnd.randrange(10 ** 6)
    t_fin = S["t_fin"]
    t_cle = min(max(ev["t_cle"], 3.0), t_fin - 2.5)
    victime = ev["histoire"] in ("piege", "domination") or (ev["histoire"] == "photo" and rnd.random() < .5)
    P, PAN, fonds = {}, dict(intro=1.7, cle=2.0, fin=2.0, perdant=2.0, card=2.0), {}
    fonds.update(intro=rnd.choice(["eclair", "vitesse", "aura"]),
                 cle=rnd.choice(["vitre", "eclair", "pluie"]) if victime else rnd.choice(["aura", "vitesse"]),
                 fin=rnd.choice(["soleil", "aura", "explosion"]), perdant=rnd.choice(["pluie", "coucher"]))
    P["intro"] = panneaux.p_duel(cast[idx[0]], col[idx[0]], cast[idx[1]], col[idx[1]], theme, rnd.choice(MURS_TXT["defi_bas"]),
                                 rnd.choice(MURS_TXT["defi_haut"]), fonds["intro"], gr(), "determined", "fierce") + ("impact",)
    if victime:
        P["cle"] = panneaux.p_notyou(cast[p], col[p], theme, rnd.choice(MURS_TXT["piege"]), fonds["cle"], gr()) + ("impact",)
    else:
        P["cle"] = panneaux.p_notdone(cast[g], col[g], theme, rnd.choice(MURS_TXT["relance"]), fonds["cle"], gr()) + ("impact",)
    P["fin"] = panneaux.p_notdone(cast[g], col[g], theme, rnd.choice(MURS_TXT["gagne"]), fonds["fin"], gr(), larmes=0) + (rnd.choice(TRANSITIONS),)
    P["perdant"] = panneaux.p_perdant(cast[p], col[p], theme, rnd.choice(charger("textes_plus.json")["perdant"]), fonds["perdant"], gr()) + ("glisse",)
    morale = rnd.choice(T["morales"])
    P["card"] = panneaux.p_card(morale, rnd.choice(["aube", "sakura", "plumes", "coucher"]), gr()) + ("zoom",)
    seq = [("panel", "intro"), ("game", 0, t_cle), ("panel", "cle"), ("game", t_cle, t_fin + .6), ("panel", "fin"), ("panel", "perdant"), ("panel", "card")]
    for k, v in list(P.items()):
        base, bulles, style = v
        P[k] = (artisanal.appliquer(base, 100 + hash_nom(k) + numero, 1.0, True),
                [(artisanal.appliquer(b, 300 + hash_nom(k) + numero, .8, False), d, pos) for (b, d, pos) in bulles], style)
    nomc = lambda i: sim.SHAPES[i][0].title()
    accroche = random.Random(numero * 31 + 7).choice(ACC_MURS[ev["histoire"]]).format(C=nomc(g), R=nomc(p))
    marks, gmap, total = monteur.timeline(seq, PAN, {"climax": t_fin})
    os.makedirs(sortie, exist_ok=True)
    ep = "EP%03d" % numero
    out = os.path.join(sortie, ep)
    monteur.render(S, seq, PAN, P, theme, out, shake_names=("cle",), accroche=accroche)

    climax = marks["climax"]
    mk = lambda k: marks.get(k, climax)

    def tension(vt):
        for v0, g0, g1 in gmap:
            if v0 <= vt < v0 + (g1 - g0):
                return murs.tension(S, g0 + vt - v0)
        return .55
    arc = [(0, mk("cle"), "tendu"), (mk("cle"), climax, "puissance"), (climax, mk("perdant"), "triomphe"), (mk("perdant"), total, "sad")]
    hits = [(mk("cle"), "sting" if victime else "braam"), (mk("perdant"), "piano")]
    style = rnd.choice(["thriller", "electro", "guerre"])
    info_m = musique.composer(dict(_risers=[mk("cle")]), monteur.bounces(S, gmap), total, out + ".wav", style, arc, tension, hits, climax,
                              numero * 31 + 7, False)
    monteur.mux(out)
    for f in (out + "_v.mp4", out + ".wav"):
        os.remove(f)

    a_en, r_en = animaux.ANIMAUX[cast[g]]["nom_en"], animaux.ANIMAUX[cast[p]]["nom_en"]
    titre = maj(rnd.choice(TITRES_MURS).format(animal=a_en.title(), rival=r_en.title()))
    legende = maj(rnd.choice(LEGENDES_MURS).format(animal=a_en, rival=r_en))
    mention = rnd.choice(T["mention_ia"])
    meta = dict(id=ep, titre=titre, legende=f"{legende}\n\n{mention}",
                youtube_description=f"{legende}\n\n{mention}\nEvery Shape Has a Story.", hashtags=list(rnd.choice(T["hashtags"])), test=False,
                _info=dict(accroche=accroche, scenario="murs", histoire=ev["histoire"], mode="murs", niveau=look, seed=S["seed"], animal=cast[g],
                           casting=[cast[i] for i in idx], theme=th_nom, murs=ev["murs"], coups=len(S["plis"]), fonds=fonds, musique=info_m,
                           morale=morale, duree=round(total, 1), marks={k: round(v, 1) for k, v in marks.items()}))
    json.dump(meta, open(out + ".json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return meta


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    d = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ICI, "sortie")
    m = generer(n, d)
    print(json.dumps(m["_info"], ensure_ascii=False))
