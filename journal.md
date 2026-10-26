# Journal
- 18/10/2026 — Création du dossier Shape Saga : robot de publication simplifié (réutilise Telegram, hébergement, Buffer de l'ancien
  projet), module Buffer corrigé d'après la doc actuelle (champs « IA » YouTube/Instagram supprimés, mode brouillon pour les tests),
  4 tests passent avec de faux serveurs. Étape suivante : installation par Chahine + test des connexions.

## 2026-10-19 — Session : générateur d'épisodes v1
- Constat : l'histoire « The Last One » exacte est trop rare (1/8000). Nouvelle histoire fréquente : « le dernier survivant »
  (une seule forme s'échappe, les 3 autres tombent espacés) → ~3 % des courses, ≤ 20,5 s, les 4 formes peuvent être héros.
- Ajouté `moteur/` : `generateur.py` (un numéro = un épisode, toujours identique : vérifié par empreinte), `panneaux.py`
  (planches génériques), `animaux.py` (42 animaux du pack), `fabrique.py` (fabrique ce dont le robot a besoin avant chaque cycle),
  `data/textes.json` + `data/themes.json` (155 morales, 60 titres, 40 légendes, 10 décors).
- Les vidéos ne sont plus stockées dans GitHub (`episodes/*.mp4` ignorés sauf EP000) : refaites au besoin.
- `contenu_ia` passé à `true` ; mention IA dans chaque légende.
- Workflow `cycle.yml` : ubuntu-24.04 fixé, installation ffmpeg/cairo/polices, étape « Fabriquer les épisodes ».
- PAS ENCORE TESTÉ sur GitHub (testé en local : 2 épisodes fabriqués en 78 s). Pas encore fait : stories Instagram, sondages,
  autres niveaux de jeu, héros animal pour les « amis » (fantômes encore en formes géométriques).

## 2026-10-19 (suite) — Décors et planches de qualité
- `moteur/decor.py` : 10 décors illustrés (volcans, nuages, marais, montagnes enneigées, lune, dunes, bonbons, forêt, nébuleuse, engrenages),
  murs en vrais matériaux (brique, pierre, glace avec stalactites, grès, rayures bonbon, bois, cristal, métal rivetté, mousse),
  liquide lumineux animé (dégradé, écume, caustiques, bulles, croûte pour lave/métal) et particules (braises, neige, lucioles…).
- `moteur/effets.py` : 13 fonds de planches. Émotion : pluie, vitre, sakura, coucher, aube, plumes, étoiles (lanternes).
  Shonen : vitesse, éclair, aura (flammes), onde de choc, explosion, soleil. Choix par type de scène (`SCENES` : chute / défi / fin).
- La carte finale reprend le fond de la dernière planche en filigrane. `_info.fonds` mémorise les fonds choisis.
- Toujours déterministe (même numéro = même vidéo). Durée de fabrication : 30–45 s par épisode.
- Idées à faire : variantes de plateformes/niveaux, héros en animal aussi pour les amis, effets animés dans les planches (pluie qui tombe,
  éclairs qui clignotent), stories Instagram.

## 2026-10-20 — v3 : scénarios, niveaux, musique, rendu « fait main » (réponse au retour : « répétitif, ça fait IA »)
- Constat de l'utilisateur : les vidéos avaient le même squelette (même niveau, même histoire, mêmes planches), seuls l'animal et la couleur changeaient.
- 3 scénarios (`moteur/detecteurs.py`) repérés dans de vraies courses, avec des structures différentes :
  « dernier » (survivant seul), « presque » (le dernier à tomber avait presque atteint la sortie : fin triste), « duel » (photo-finish : rival juste derrière).
- 6 architectures de niveaux (`moteur/niveaux.py`) : étages, cheminée, plinko, labyrinthe, escaliers, piliers. Décor variable à chaque épisode (graine + teintes).
- Les 4 amis sont maintenant des animaux (ouverture « cast », fantômes en animaux). Nouvelles planches : intro, espoir, chute, adieu, duel (page diagonale), perdant ;
  onomatopées lettrées à la main, cases de narration, 6 styles d'entrée de planche (impact, glisse, iris, zoom, tourne, coupe).
- Musique (`moteur/musique.py`) : 6 styles (orchestral, thriller, guerre, mélancolie, électro, espoir), mode/tempo/progression tirés par épisode,
  suspense piloté par la course réelle (distance liquide/formes), crescendo, quasi-silence avant le sommet, coup final (triomphal ou dramatique).
- Rendu « fait main » (`moteur/artisanal.py` + filtre ffmpeg) : trait tremblé, encre irrégulière, grain de papier, léger décalage d'impression.
- Toujours déterministe (vérifié par empreinte). Durée de fabrication : ~65 s par épisode.
- Non testé sur GitHub. À faire : effets animés dans les planches, plus de scénarios (rescapé, sacrifice), niveaux avec obstacles mobiles.

## 2026-10-21 — v4 (EN COURS, NON VALIDÉ) : nouveau moteur de jeu et 7 histoires
Retour utilisateur : « la lave ne monte jamais assez (≈20 %), les formes perdent trop tôt, je veux de l'imprévisible (0 à 4 gagnants), des rebonds naturels,
des obstacles animés, une musique plus puissante, des histoires variées (prison avec PV, sacrifice, réussite collective, complot) ».
- `moteur/sim2.py` (nouveau) : rotation réelle des formes, restitution variable, petites rafales aléatoires, obstacles animés (glissières, barres tournantes),
  liquide à profil aléatoire (final 60–100 % du niveau ; linéaire/accélérant/vagues/à-coups), mode PRISON (cellule qui se resserre, PV, dégâts selon impact et masse, porte au plafond).
- `moteur/detecteurs.py` : + sacrifice, trahison, ensemble (union), prison. `moteur/generateur.py` v4 : 7 scénarios, 2 modes.
- `moteur/monteur.py` : dessin des obstacles, rotation des formes, barres de vie ; `moteur/decor.py` : décor « prison ».
- Suno : PAS d'API publique (oct. 2026) ; seulement revendeurs payants / bidouilles non officielles → écarté (0 €).
- VÉRIFIÉ : épisode prison (numéro 1) vu sur planche-contact ; épisode sacrifice (numéro 2) généré mais PAS regardé.
- NON VÉRIFIÉ : trahison, ensemble, dernier/presque/duel avec sim2, obstacles animés à l'image (le test n'en avait aucun), musique à l'écoute,
  exécution sur GitHub Actions. Le « relais coopératif » (interrupteurs/portes) n'est pas fait. Effets de planche toujours fixes.

## 2026-10-26 — Travail direct sur le PC (plus de zip) + validation v4 + Duel de murs (NON ENVOYÉ sur GitHub)
- Le dépôt GitHub Desktop est `D:\ZONE IA\CLAUDE_DB\ShapeSaga\shape-saga`. Sur GitHub il n'y avait que la version du 18/10 (aucune mise à jour 1–4 installée).
  La v4 a été copiée dans ce dossier ; outils installés sur le PC : ffmpeg (winget), pymunk 7.3.1, pycairo, numpy, scipy, tzdata (Python 3.14), polices du projet.
- Validation v4 : les 7 histoires fabriquées et regardées (planches-contact). Durées 20–28 s, fabrication 25–230 s par épisode sur le PC.
- Corrigé : liquide qui n'atteignait pas 60 % quand l'histoire finissait tôt (montée en 10–17 s + partie rejetée si < 60 % au moment décisif) ;
  texte illisible dans les bulles de cri (coupé en 2 lignes, bulles plus grandes) ; répétition (décor, casting et niveau en rotation : jamais deux fois de suite) ;
  texte trop petit des bulles ovales ; ordre de dessin des murs qui rendait la vidéo non reproductible.
- Nouveau : accroche en anglais en haut de l'écran pendant le jeu (s'efface quand une forme approche de la sortie).
- Nouveau mode « Duel de murs » (`moteur/murs.py`), inspiré des vidéos de référence pokyygame : 2 formes sur une grille 7×9, chacune avance ou pose
  un mur (4 chacune), deux IA de niveaux tirés au hasard, 4 histoires (photo, retournement, piège, domination), 4 plateaux (nuit, papier, ardoise, sable),
  planches manga (défi, piège, victoire, perdant), 22–24 s. 4 épisodes sur 18 dans `ORDRE`. Statistiques sur 400 parties : 100 % terminées, gagnants 209/191.
- Vérifié : 7 tests du robot OK ; même numéro = même vidéo (empreinte identique) pour un duel et une histoire classique.
- NON vérifié : exécution sur GitHub Actions, musique à l'écoute, rendu sur téléphone.

## 2026-10-26 (nuit) — Passage en publication réelle
- `mode_test: false` : un ✅ programme désormais VRAIMENT la publication (12 h / 19 h Paris).
- Chaque vidéo envoyée sur Telegram est suivie d'une fiche : statut, date de publication prévue, réseaux, titre YouTube, sondage,
  1er commentaire Instagram, puis la miniature en photo. La miniature = 1re planche forte (ne dévoile pas la fin), transmise à Buffer (thumbnailOffset).
- Sondage : les vrais sondages à boutons n'existent pas dans l'API Buffer → vote en commentaires (ligne dans la légende + 1er commentaire Instagram).
- Vérifié en local (faux Telegram) ; NON vérifié en réel : acceptation de firstComment et thumbnailOffset par Buffer.

## 2026-10-26 (nuit, suite) — Calendrier quotidien (demande de Chahine)
- Chaque soir dès 19 h (passage du robot vers 19 h 07–19 h 15), les 2 vidéos du LENDEMAIN arrivent sur Telegram, une par créneau (12 h et 20 h),
  précédées d'un message « 🌙 Vidéos de mardi 27/10 ». Chahine valide quand il veut la nuit ; chaque vidéo validée est programmée dans Buffer à SON heure.
- ❌ = remplacée au passage suivant (jusqu'à 10 h 30 le jour même). Non validée avant son heure = non publiée (⌛).
- Nouveau `robot/planning.py` (calendrier partagé robot + fabrique) ; la fabrique ne fabrique que pour les créneaux libres.
- 2e créneau passé de 19 h à 20 h. Tests : 11 OK, dont une journée complète simulée (envoi, ✅, ❌ + remplaçant, expiration).
