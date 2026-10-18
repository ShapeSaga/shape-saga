"""Le robot : lit Telegram (✅ ❌), envoie les nouvelles vidéos, programme les vidéos validées via Buffer.

Un « épisode prêt » = deux fichiers dans episodes/ : EP001.mp4 et EP001.json
    {"id": "EP001", "titre": "...", "legende": "...", "youtube_description": "...",
     "hashtags": ["#shapesaga", "#shorts"], "test": false}
Un épisode avec "test": true part en BROUILLON dans Buffer : rien n'est publié.
"""
from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import RACINE, Secrets, charger_config
from .etat import BROUILLON, ENVOYE, EXPIRE, PROGRAMME, PUBLIE, REFUSE, VALIDE, Etat
from .hebergement import ErreurHebergement, HebergeurGitHub
from .publieurs import ErreurPublication, Publication, creer_publieurs
from .telegram_bot import BotTelegram, echapper

log = logging.getLogger(__name__)
NOMS = {"tiktok": "TikTok", "youtube": "YouTube", "instagram": "Instagram"}


class Orchestrateur:
    def __init__(self, config=None, secrets=None, etat=None, essai=False, session=None, maintenant=None,
                 dossier_episodes=None):
        self.conf = config or charger_config()
        self.secrets = secrets or Secrets.depuis_env()
        self.etat = etat or Etat()
        self.essai = essai
        self.session = session
        self.maintenant = maintenant or (lambda: datetime.now(timezone.utc))
        self.dossier = Path(dossier_episodes) if dossier_episodes else RACINE / "episodes"
        self._bot = self._publieurs = self._heberg = None

    # ------------------------------------------------------------------ outils
    @property
    def bot(self) -> BotTelegram:
        if not self._bot:
            self._bot = BotTelegram(self.secrets.telegram_token, self.secrets.telegram_chat_id, self.session)
        return self._bot

    @property
    def publieurs(self):
        if not self._publieurs:
            self._publieurs = creer_publieurs(self.conf, self.secrets, essai=self.essai, etat=self.etat,
                                              session=self.session)
        return self._publieurs

    @property
    def hebergeur(self) -> HebergeurGitHub:
        if not self._heberg:
            h = self.conf["publication"]["hebergement"]
            depot = h.get("depot") or self.secrets.github_depot
            self._heberg = HebergeurGitHub(depot, self.secrets.github_token, h.get("tag_release", "videos"),
                                           self.session)
        return self._heberg

    def alerter(self, cle: str, message: str) -> None:
        derniere = self.etat.donnees["alertes"].get(cle)
        if derniere:
            ecart = self.maintenant() - datetime.fromisoformat(derniere)
            if ecart < timedelta(hours=self.conf["alertes"]["repetition_heures"]):
                return
        self.etat.donnees["alertes"][cle] = self.maintenant().isoformat()
        try:
            self.bot.envoyer_message("⚠️ <b>Problème</b>\n" + echapper(self.secrets.masquer(message)))
        except Exception:  # noqa: BLE001
            log.exception("Impossible d'envoyer l'alerte Telegram")

    def episodes_prets(self) -> list[dict]:
        liste = []
        for fj in sorted(self.dossier.glob("*.json")):
            try:
                ep = json.loads(fj.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            ep.setdefault("id", fj.stem)
            video = fj.with_suffix(".mp4")
            if video.exists():
                ep["_fichier"] = video
                liste.append(ep)
        return liste

    def legende(self, ep: dict) -> str:
        tags = " ".join(ep.get("hashtags", []))
        return f"{ep.get('legende', '')}\n\n{tags}".strip()

    # ------------------------------------------------------------------ Telegram
    def lire_telegram(self) -> None:
        evts, offset = self.bot.lire_tout(self.etat.donnees["offset"])
        self.etat.donnees["offset"] = offset
        for e in evts:
            if e.type == "commande":
                self.commande(e.action)
                continue
            fiche = self.etat.episodes.get(e.cle)
            if not fiche:
                self.bot.repondre_bouton(e.callback_id, "Épisode inconnu")
                continue
            if fiche["statut"] != ENVOYE:
                self.bot.repondre_bouton(e.callback_id, f"Déjà traité ({fiche['statut']})")
                continue
            if e.action == "valider":
                fiche["statut"] = VALIDE
                self.bot.repondre_bouton(e.callback_id, "✅ Validé")
                self.marquer(fiche, e.cle, "✅ VALIDÉ")
            else:
                fiche["statut"] = REFUSE
                texte = "❌ REFUSÉ" if e.action == "refuser" else "❌ ÉCARTÉ (« Refaire » n'est pas encore disponible)"
                self.bot.repondre_bouton(e.callback_id, texte)
                self.marquer(fiche, e.cle, texte)

    def marquer(self, fiche: dict, cle: str, etiquette: str) -> None:
        try:
            self.bot.editer_legende(fiche["message_id"], f"{etiquette} — {echapper(fiche.get('titre', cle))}")
        except Exception:  # noqa: BLE001
            log.warning("Légende Telegram non modifiée pour %s", cle)

    def commande(self, action: str) -> None:
        if action == "pause":
            self.etat.donnees["pause"] = True
            self.bot.envoyer_message("⏸ Publications en pause. /reprendre pour relancer.")
        elif action == "reprendre":
            self.etat.donnees["pause"] = False
            self.bot.envoyer_message("▶️ Publications relancées.")
        else:
            self.bot.envoyer_message(self.texte_statut())

    def texte_statut(self) -> str:
        n: dict[str, int] = {}
        for f in self.etat.episodes.values():
            n[f["statut"]] = n.get(f["statut"], 0) + 1
        lignes = [f"<b>{echapper(self.conf['identite']['nom_compte'])}</b>"]
        lignes.append("⏸ EN PAUSE" if self.etat.donnees["pause"] else "▶️ en marche")
        lignes += [f"• {s} : {c}" for s, c in sorted(n.items())] or ["• aucun épisode pour l'instant"]
        return "\n".join(lignes)

    def envoyer_nouveaux(self) -> None:
        attente = sum(1 for f in self.etat.episodes.values() if f["statut"] == ENVOYE)
        place = self.conf["validation"]["max_en_attente"] - attente
        for ep in self.episodes_prets():
            if place <= 0:
                break
            if ep["id"] in self.etat.episodes:
                continue
            avert = "⚠️ <b>TEST</b> : s'il est validé, il part en BROUILLON dans Buffer (rien n'est publié).\n\n" if ep.get("test") else ""
            legende = f"{avert}🎬 <b>{echapper(ep['id'])} — {echapper(ep.get('titre', ''))}</b>\n\n{echapper(self.legende(ep))}"
            mid = self.bot.envoyer_video(ep["_fichier"], legende, ep["id"])
            self.etat.episodes[ep["id"]] = {"statut": ENVOYE, "message_id": mid, "titre": ep.get("titre", ""),
                                            "test": bool(ep.get("test")), "envoye_le": self.maintenant().isoformat(),
                                            "programme": {}}
            place -= 1

    def gerer_delais(self) -> None:
        v = self.conf["validation"]
        for cle, f in self.etat.episodes.items():
            if f["statut"] != ENVOYE:
                continue
            age = self.maintenant() - datetime.fromisoformat(f["envoye_le"])
            if age > timedelta(hours=v["delai_heures"]):
                f["statut"] = EXPIRE
                self.marquer(f, cle, "⌛ EXPIRÉ (aucune réponse, non publié)")
            elif age > timedelta(hours=v["rappel_heures"]) and not f.get("rappel"):
                f["rappel"] = True
                self.bot.envoyer_message(f"⏰ {echapper(cle)} attend ta réponse (✅ ou ❌).", reponse_a=f["message_id"])

    # ------------------------------------------------------------------ publication
    def prochain_creneau(self) -> datetime:
        tz = ZoneInfo(self.conf["cadence"]["fuseau"])
        now = self.maintenant().astimezone(tz)
        pris = {f["creneau"] for f in self.etat.episodes.values() if f.get("creneau")}
        marge = timedelta(minutes=self.conf["cadence"]["marge_minutes"])
        heures = sorted(tuple(int(x) for x in h.split(":")) for h in self.conf["cadence"]["creneaux"])
        for d in range(90):
            for hh, mm in heures:
                dt = datetime.combine(now.date() + timedelta(days=d), time(hh, mm), tz)
                if dt >= now + marge and dt.astimezone(timezone.utc).isoformat() not in pris:
                    return dt
        raise RuntimeError("aucun créneau libre dans les 90 prochains jours")

    def publier_valides(self) -> None:
        if self.etat.donnees["pause"]:
            return
        prets = {e["id"]: e for e in self.episodes_prets()}
        for cle, f in sorted(self.etat.episodes.items()):
            if f["statut"] != VALIDE:
                continue
            ep = prets.get(cle)
            if not ep:
                self.alerter(f"absent-{cle}", f"{cle} validé mais ses fichiers ne sont plus dans episodes/.")
                continue
            self.publier_episode(cle, f, ep)

    def publier_episode(self, cle: str, f: dict, ep: dict) -> None:
        test = bool(f.get("test"))
        if not f.get("video_url"):
            try:
                f["video_url"] = self.hebergeur.deposer(ep["_fichier"], nom=f"{cle}.mp4", remplacer=False)["url"]
            except ErreurHebergement as exc:
                self.alerter(f"heberg-{cle}", f"Hébergement de {cle} impossible : {exc}")
                return
        if not f.get("creneau") and not test:
            f["creneau"] = self.prochain_creneau().astimezone(timezone.utc).isoformat()
        date = datetime.fromisoformat(f["creneau"]) if f.get("creneau") else self.maintenant()
        tags = ep.get("hashtags", [])
        for plateforme in self.conf["publication"]["plateformes"]:
            if plateforme in f["programme"]:
                continue
            pub = self.publieurs[plateforme]
            texte = self.legende(ep)
            if plateforme == "youtube":
                texte = f"{ep.get('youtube_description') or ep.get('legende', '')}\n\n{' '.join(tags)}".strip()
            p = Publication(cle=f"{cle}-{plateforme}", episode_id=cle, plateforme=plateforme, date=date, texte=texte,
                            titre=(ep.get("titre") or cle)[:100], hashtags=tags, video_url=f["video_url"],
                            contenu_ia=bool(self.conf["publication"]["contenu_ia"]), brouillon=test)
            try:
                place = pub.places_disponibles(plateforme) if not test else None
            except ErreurPublication as exc:
                log.warning("Places Buffer inconnues (%s) : on essaie quand même", exc)
                place = None
            if place == 0:
                self.alerter(f"file-{plateforme}", f"File Buffer pleine sur {NOMS[plateforme]} : {cle} attend une place.")
                continue
            try:
                res = pub.programmer(p)
            except ErreurPublication as exc:
                self.alerter(f"pub-{cle}-{plateforme}", f"{cle} sur {NOMS[plateforme]} : {exc}")
                continue
            f["programme"][plateforme] = {"id": res.id_distant, "message": res.message}
        if all(p in f["programme"] for p in self.conf["publication"]["plateformes"]):
            f["statut"] = BROUILLON if test else PROGRAMME
            lignes = [f"• {NOMS[p]} : {echapper(r['message'])}" for p, r in f["programme"].items()]
            tete = "📝 Brouillons créés dans Buffer (test, rien de publié)" if test else "📅 Programmé"
            self.bot.envoyer_message(f"{tete} — <b>{echapper(cle)}</b>\n" + "\n".join(lignes), reponse_a=f["message_id"])

    def menage(self) -> None:
        jours = self.conf["publication"]["hebergement"]["conserver_jours"]
        for cle, f in self.etat.episodes.items():
            if f["statut"] == PROGRAMME and f.get("creneau"):
                if self.maintenant() > datetime.fromisoformat(f["creneau"]) + timedelta(hours=2):
                    f["statut"] = PUBLIE
            if f["statut"] in (PUBLIE, BROUILLON) and f.get("video_url") and not f.get("nettoye"):
                ref = datetime.fromisoformat(f["creneau"]) if f.get("creneau") else datetime.fromisoformat(f["envoye_le"])
                if self.maintenant() > ref + timedelta(days=jours):
                    try:
                        self.hebergeur.supprimer_nom(f"{cle}.mp4"); f["nettoye"] = True
                    except ErreurHebergement as exc:
                        log.warning("Nettoyage de %s impossible : %s", cle, exc)

    # ------------------------------------------------------------------ cycle
    def _etape(self, nom: str, fonction) -> None:
        try:
            fonction()
        except Exception as exc:  # noqa: BLE001
            log.error("Étape « %s » en échec : %s", nom, self.secrets.masquer(traceback.format_exc()))
            self.alerter(f"etape-{nom}", f"Étape « {nom} » : {exc.__class__.__name__} : {exc}")

    def cycle(self) -> None:
        manquants = self.secrets.manquants()
        if manquants:
            raise SystemExit("Secrets manquants : " + ", ".join(manquants))
        for nom, fn in (("Telegram", self.lire_telegram), ("délais", self.gerer_delais),
                        ("envoi des nouvelles vidéos", self.envoyer_nouveaux),
                        ("publication", self.publier_valides), ("ménage", self.menage)):
            self._etape(nom, fn)
        self.etat.sauvegarder()
