# ÉTAT DU PROJET — Shape Saga (21/10/2026)

## 1. But
Chaînes de vidéos courtes (≤ 30 s) TikTok / YouTube Shorts / Instagram Reels, **100 % automatiques**, 0 €. L'utilisateur ne crée rien, ne publie rien, ne copie-colle rien :
son seul geste est ✅/❌ dans Telegram (+ installation unique guidée). Objectif : 100 000 abonnés sur au moins un compte en 6 mois ; rythme visé : 2 vidéos/jour.
Principe : un vrai jeu physique (formes de couleur, liquide qui monte, sortie en haut) → un événement réel raconte une histoire → planches manga en animaux géométriques → morale de fin.

## 2. Infrastructure (FAIT et TESTÉ sur GitHub)
- Dépôt GitHub public `ShapeSaga/shape-saga` ; secrets TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, BUFFER_API_KEY posés (jeton Telegram renouvelé après une fuite dans le chat).
- Workflow « Tester les connexions » : tout ✅ (Telegram, Buffer avec TikTok/YouTube/Instagram, hébergement release `videos`).
- Workflow « Cycle du robot » : testé avec l'épisode EP000 (envoi Telegram, ✅, 3 brouillons Buffer créés puis supprimés par l'utilisateur).
- Les brouillons de test n'avaient pas de texte : les vrais épisodes portent titre, légende (+ mention IA), hashtags, description YouTube.
- `contenu_ia: true` (TikTok a un champ ; Instagram a une étiquette IA que Buffer ne permet pas de cocher : à vérifier une fois dans l'appli ; YouTube : à vérifier).
- Mises à jour 1, 2 et 3 livrées sous forme de zip : **on ignore lesquelles l'utilisateur a réellement installées dans son dépôt. À DEMANDER EN PREMIER.**
- Méthode de mise à jour : zip → remplacer le dossier `shape-saga` → GitHub Desktop (Commit + Push). Pas d'accès direct de Claude à GitHub (pas d'abonnement payant : Claude Code web exclu).

## 3. Code (dans `shape-saga/`)
- `robot/` : orchestrateur (Telegram, Buffer, statuts brouillon/envoye/valide/programme/publie, créneaux 12 h et 19 h). Testé.
- `moteur/` : fabrication des épisodes.
  - `fabrique.py` : avant chaque cycle, fabrique les .mp4 nécessaires (épisodes en attente ou validés + nouveaux). Les .mp4 ne sont PAS dans Git (refaits au besoin : même numéro = même vidéo, vérifié par empreinte md5 ; chaque épisode dans son propre processus).
  - `generateur.py` (v4) : `python generateur.py NUMERO DOSSIER`. Choisit un scénario via `ORDRE[numero % 14]`, cherche une vraie partie qui le raconte, monte planches + musique, écrit `EPxxx.mp4/.json`.
  - `sim.py` (ancien moteur, constantes et formes), `sim2.py` (NOUVEAU moteur : voir §4), `niveaux.py` (6 architectures de niveaux : etages, cheminee, plinko, labyrinthe, escaliers, piliers), `detecteurs.py` (7 histoires),
    `monteur.py` (rendu des images, transitions, assemblage ffmpeg avec grain/vignette/décalage RVB), `decor.py` (10 décors + prison, murs en matériaux, liquide lumineux, particules),
    `effets.py` (13 fonds de planches), `panneaux.py` (planches : intro, chute, défi, fin, espoir, presque, adieu, duel diagonal, perdant, union, carte finale, lettrage manuel, onomatopées),
    `animaux.py` (42 têtes d'animaux, 6 expressions : crying, fierce, sad_smile, scared, serene, determined), `musique.py` (compositeur, 6 styles), `son.py`/`son2.py` (instruments),
    `artisanal.py` (trait tremblé, grain de papier), `dessin.py` (outils d'encrage manga), `data/` (textes.json, textes_plus.json, themes.json), `polices/`.
- `.github/workflows/cycle.yml` : ubuntu-24.04, installe ffmpeg + libcairo2-dev + polices, `pip install -r requirements.txt` (pymunk==7.3.1, pycairo, numpy, scipy), `python moteur/fabrique.py`, puis le cycle. **Jamais exécuté avec le générateur sur GitHub.**

## 4. Moteur de jeu v2 (`sim2.py`) — ce que l'utilisateur a demandé et ce qui est fait
- Liquide (lave/eau/etc.) : final aléatoire 60–100 % du niveau, profil aléatoire, temps d'atteinte 13–21 s. FAIT.
- Rebonds naturels : formes qui tournent (moment d'inertie réel), restitution 0,92–1,0, frottement, petites rafales gaussiennes, vitesse bornée 380–840 (plus de vitesse constante imposée). FAIT.
- Obstacles animés : glissières et barres tournantes (corps cinématiques) placés dans les zones libres. FAIT dans le moteur et le rendu, **jamais vu à l'image**.
- Mode PRISON : cellule qui se resserre, PV (100), dégâts = impact × masse de l'autre, élimination à 0 PV, la porte (plafond) coulisse quand il n'en reste qu'un, il doit sortir. FAIT, vérifié visuellement une fois.
- Issues possibles : 0 à 4 gagnants (rare au-delà d'1). Fréquences mesurées (3000 parties de course) : presque ≈ 10 %, dernier ≈ 2,3 %, duel 0,7 %, sacrifice 0,5 %, trahison 0,4 %, ensemble 0,5 % ; prison : 30 % des parties donnent un champion.
- PAS FAIT : relais coopératif (interrupteurs qui ouvrent des portes : « chacun donne sa pierre »), complot multi-formes, effets de planche animés (pluie qui tombe…), plus de scénarios, obstacles qui piègent.

## 5. Les 7 histoires (détecteurs sur de vraies parties)
dernier (survivant seul) · presque (le dernier à tomber avait presque atteint la sortie, fin triste) · duel (photo-finish, rival juste derrière) ·
sacrifice (un choc près du liquide propulse un ami vers le haut ; celui qui l'a aidé tombe) · trahison (un choc pousse un ami vers le bas ; l'autre s'échappe) ·
ensemble (≥ 2 sorties rapprochées) · prison (champion). Chaque histoire a sa structure de planches, ses textes (data/textes_plus.json), son arc musical (calme/tendu/sombre/puissance/triomphe/sad), son coup final (triomphal ou dramatique).

## 6. Décisions et règles du projet
- Le jeu reste neutre (pas de visages sur les formes) ; physique réelle, jamais truquée, jamais de ralenti ; l'histoire naît d'un vrai événement.
- Planches : animal géométrique qui garde la forme et la couleur de la forme de jeu, tête seulement (pas de corps, pas de mains), pas de titres dans les dessins, texte en anglais.
- Vidéo ≤ 30 s, sommet dans les 8 dernières secondes, morale de fin, mention IA dans chaque légende.
- Musique : le compositeur interne tire un style par épisode, le suspense suit la distance liquide/formes, quasi-silence avant le sommet puis coup final.
- **Suno : aucune API publique en oct. 2026** (annonce de juillet : « exploration » avec quelques partenaires ; seulement revendeurs payants ≈ 0,07–0,11 $/morceau ou wrappers non officiels risqués). Écarté (0 €). Alternatives à examiner seulement si l'utilisateur l'accepte : ElevenLabs Music / Mureka (offres gratuites annoncées, droits commerciaux et quotas NON vérifiés). Sinon continuer à renforcer la synthèse interne.
- Sécurité : ne jamais demander ni stocker mot de passe/clé dans le chat ; les clés vont directement dans les secrets GitHub. Claude n'a aucun accès au Gmail ni à GitHub.
- Un ✅ dans Telegram programme réellement la publication (12 h / 19 h) ; ❌ pour juste regarder.

## 7. Ce qui reste à faire (ordre conseillé)
1. Demander à l'utilisateur quelle mise à jour est installée (1, 2, 3 ?) et le résultat du dernier cycle.
2. Valider v4 : générer et REGARDER (planches-contact) au moins un épisode de chaque scénario (dernier, presque, duel, sacrifice, trahison, ensemble, prison) avec sim2, et des niveaux AVEC obstacles animés. Corriger ce qui casse (rien n'est garanti en dehors de prison et sacrifice(non regardé)).
3. Vérifier la durée ≤ 30 s de chaque scénario, la lisibilité des PV, la porte de la prison, les temps de recherche des histoires rares (objectif < 2 min/épisode).
4. Tester sur GitHub Actions (cycle complet) puis vérifier les brouillons Buffer d'un vrai épisode (titre, légende, hashtags, étiquette IA).
5. Écouter/mesurer la musique (puissance, mastering : compression/limiteur), l'améliorer si besoin (couches, chœurs, impacts).
6. Relais coopératif + autres scénarios ; effets animés dans les planches ; stories Instagram et sondages (à tester via Buffer : champs `type` et `firstComment` ; sondages probablement non automatisables).
7. Variété long terme : pour éviter l'effet « répétitif », suivre les statistiques de l'utilisateur (vues/likes) et ajuster.

## 8. Environnement de travail de Claude (pour la prochaine conversation)
- Le bac à sable n'a PAS Internet. pymunk et pycairo n'y sont pas installés : l'utilisateur doit fournir `paquets_pymunk_pycairo_linux_py312.zip` (Linux x86_64, Python 3.12) → `pip install --no-index --find-links . --break-system-packages pymunk pycairo`. numpy, scipy, PIL, ffmpeg, gcc, libcairo présents. Copier `moteur/polices/*.ttf` dans `~/.fonts` puis `fc-cache -f`.
- Lancer un épisode : `cd shape-saga/moteur && python3 generateur.py NUMERO /dossier/sortie` (≈ 65–110 s). Ne pas lancer plusieurs épisodes en arrière-plan (les processus sont tués à la fin de la commande) ; un seul cœur.
- Vérifier toujours avec une planche-contact (`ffmpeg -vf "fps=0.7,scale=130:-1,tile=14x1"`) avant de montrer quoi que ce soit.
