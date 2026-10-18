# BRIEF — Shape Saga (robot de publication) — version du 18/10/2026

## Projet et conditions de Chahine
- Objectif : 100 000 abonnés sur au moins un des 3 comptes en 6 mois (non garanti). Budget 0 €. 2 vidéos/jour.
- Comptes : TikTok @Shape.Saga · YouTube @Shape_Saga · Instagram @Shape.Saga_ · GitHub ShapeSaga.
- Son seul geste : ✅ ou ❌ dans Telegram (+ installation unique). Il ne crée, ne publie, ne copie-colle rien.
- Style retenu : mélange Pompon & Noisette (dessins crayon mignons) + v6 (jeu neutre de formes, planches manga).
  Voir `projet-histoires-v6.zip` (BRIEF.md, code du moteur d'épisodes).
- Étiquette IA : `contenu_ia: false` dans config.yaml (dessins faits par du code). À repasser à true si une plateforme l'exige.

## Ce que contient ce dossier (publication seulement)
- `robot/` : lit Telegram, envoie les vidéos de `episodes/` avec ✅/❌/🔁, héberge la vidéo (Release GitHub),
  programme sur TikTok/YouTube/Instagram via l'API Buffer, 2 créneaux/jour (12 h, 19 h Paris).
- `episodes/EPxxx.mp4 + EPxxx.json` : un épisode prêt. `"test": true` = brouillons Buffer, rien de publié.
- Workflows : `cycle.yml` (toutes les heures), `tester.yml` (test des clés).
- `tests/` : 4 tests avec FAUX serveurs (parcours, refus, créneaux, pause) — passent. Ils ne prouvent PAS que les vrais serveurs acceptent.

## Vérifié / non vérifié
- Vérifié dans la doc Buffer (oct. 2026) : API sur toutes les offres dont la gratuite (1 clé, 100 req/24 h, 3 000/30 j) ;
  format `assets:[{video:{url}}]` ; `aiAssisted` existe ; YouTube/Instagram n'ont PAS de champ « IA » (retiré du code).
- NON vérifié (premier essai réel) : lecture des canaux/files (requêtes GraphQL), limite de 10 posts/canal en gratuit,
  publication publique TikTok/YouTube via l'offre gratuite, acceptation du brouillon `saveToDraft`.
- Plan B si Buffer refuse TikTok/YouTube : Zernio, puis API officielles (voir `chat-malin/docs/PUBLICATION_TIKTOK.md`, ancien projet).

## Reste à faire (dans l'ordre)
1. Installation + test (GUIDE_INSTALLATION.md) → corriger ce que le vrai Buffer refuse.
2. **Générateur d'épisodes automatique** (la plus grosse pièce) : brancher le moteur v6 (sim, dessin, son, monteur) pour produire
   chaque jour 2 épisodes (+ .json) dans `episodes/`. Aujourd'hui les épisodes v6 sont faits à la main.
3. Rapport hebdomadaire des statistiques (lecture Buffer) envoyé sur Telegram.
4. Gérer « 🔁 Refaire » (aujourd'hui traité comme ❌).
5. Voix : si besoin, Kokoro (Apache-2.0, testé : tourne ; non écouté). Éviter edge-tts (zone grise commerciale).
