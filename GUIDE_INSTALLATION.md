# Shape Saga — installation du robot (une seule fois, environ 30 min)

Avant de commencer, tu dois avoir : les 3 comptes, ton bot Telegram (jeton + identifiant), ton compte Buffer
avec les 3 réseaux connectés et sa clé d'API, et ton compte GitHub **ShapeSaga** avec GitHub Desktop.
Ne montre tes clés à personne et ne les colle jamais dans une conversation.

## 1. Mettre le projet sur GitHub (≈ 10 min)
1. Dézippe `shape-saga.zip` sur ton ordinateur.
2. Ouvre **GitHub Desktop** → *File → Add local repository* → choisis le dossier `shape-saga`.
3. S'il dit « not a git repository », clique **create a repository**, puis **Create repository**.
4. Clique **Publish repository**, **décoche « Keep this code private »**, garde le nom `shape-saga`, puis **Publish**.
   (Le dépôt doit être **public** : c'est ce qui héberge gratuitement les vidéos pour Buffer. Il ne contient aucun secret.)

## 2. Ranger les 3 clés (≈ 5 min)
Sur github.com, ouvre le dépôt `ShapeSaga/shape-saga` → **Settings → Secrets and variables → Actions → New repository secret**.
Crée ces 3 secrets (nom exact à gauche, ta valeur à droite) :

| Nom | Valeur |
|---|---|
| `TELEGRAM_BOT_TOKEN` | le jeton donné par @BotFather |
| `TELEGRAM_CHAT_ID` | ton identifiant donné par @userinfobot |
| `BUFFER_API_KEY` | ta clé d'API Buffer |

## 3. Allumer et tester (≈ 10 min)
1. Onglet **Actions** → si GitHub le demande, clique « I understand my workflows, go ahead and enable them ».
2. Choisis **Tester les connexions** → **Run workflow**. Après 1 minute, ouvre l'exécution → l'étape « Tester » doit afficher
   `Telegram ✅`, `Buffer ✅ ... tiktok, youtube, instagram` et `Hébergement GitHub ✅`.
   - Une ligne ❌ ? Envoie-moi seulement cette ligne (jamais une clé).
3. Choisis **Cycle du robot** → **Run workflow**. En 1 minute, une vidéo **EP000 — TEST** arrive sur Telegram.
4. Appuie sur **✅ Valider**, puis relance **Cycle du robot**. Tu reçois « 📝 Brouillons créés dans Buffer ».
5. Ouvre Buffer : tu dois voir **3 brouillons** (TikTok, YouTube, Instagram). **Rien n'est publié** : c'est un test.
   Supprime ces 3 brouillons à la main dans Buffer.

## Ensuite
Le robot tourne tout seul toutes les heures. Une vraie vidéo arrive sur Telegram → **✅** (publiée au prochain créneau
12 h ou 19 h, heure de Paris) ou **❌**. Commandes Telegram : `/statut`, `/pause`, `/reprendre`.
Si un problème survient, le bot t'envoie « ⚠️ Problème » avec l'explication.
