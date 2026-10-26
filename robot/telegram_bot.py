"""Bot Telegram de validation : envoi des vidéos avec ✅ / ❌ / 🔁, lecture par getUpdates.

Pas de webhook, pas de serveur : à chaque passage du robot, on lit les nouvelles
réponses à partir d'un « offset » mémorisé dans etat/telegram.json.
Seuls les messages venant de TELEGRAM_CHAT_ID sont pris en compte.
"""
from __future__ import annotations

import html
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import requests

from .reseau import ErreurHTTP, requete

log = logging.getLogger(__name__)

API = "https://api.telegram.org/bot{jeton}/{methode}"
TAILLE_MAX_VIDEO = 50 * 1024 * 1024
LIMITE_LEGENDE = 1024
LIMITE_MESSAGE = 4096

# Préfixes des boutons (callback_data ≤ 64 octets)
VALIDER, REFUSER, REFAIRE = "v", "r", "f"
ACTIONS = {VALIDER: "valider", REFUSER: "refuser", REFAIRE: "refaire"}
COMMANDES = ("statut", "pause", "reprendre", "rapport", "aide", "start")
COMMANDES_EPISODE = {"ok": "valider", "valider": "valider", "non": "refuser", "refuser": "refuser"}   # /ok EP005


class ErreurTelegram(RuntimeError):
    pass


@dataclass
class Evenement:
    """Une action de Chahine, déjà filtrée (bon chat uniquement)."""

    type: str                       # "bouton" | "commande"
    action: str                     # valider / refuser / refaire / statut / pause / ...
    cle: str = ""                   # clé de l'épisode pour un bouton
    callback_id: str = ""
    message_id: int | None = None


def echapper(texte: str) -> str:
    return html.escape(str(texte), quote=False)


def couper(texte: str, limite: int) -> str:
    return texte if len(texte) <= limite else texte[: limite - 1].rstrip() + "…"


class BotTelegram:
    def __init__(self, jeton: str, chat_id: str, session: requests.Session | None = None):
        if not jeton or not chat_id:
            raise ErreurTelegram("TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID sont obligatoires")
        self.jeton = jeton
        self.chat_id = str(chat_id).strip()
        self.session = session or requests.Session()

    # ------------------------------------------------------------------ bas niveau
    def appel(self, methode: str, *, donnees: dict | None = None, fichiers: dict | None = None,
              json_corps: dict | None = None, timeout: int = 60, tentatives: int = 3) -> dict:
        url = API.format(jeton=self.jeton, methode=methode)
        try:
            rep = requete(self.session, "POST", url, data=donnees, files=fichiers, json=json_corps,
                          timeout=timeout, tentatives=tentatives, etiquette=f"Telegram {methode}",
                          accepter=(400, 403))
        except ErreurHTTP as exc:
            raise ErreurTelegram(str(exc)) from exc
        corps = rep.json()
        if not corps.get("ok"):
            raise ErreurTelegram(f"Telegram {methode} : {corps.get('description', 'erreur inconnue')}")
        return corps["result"]

    @staticmethod
    def clavier(cle: str) -> dict:
        return {"inline_keyboard": [[
            {"text": "✅ Valider", "callback_data": f"{VALIDER}:{cle}"},
            {"text": "❌ Refuser", "callback_data": f"{REFUSER}:{cle}"},
            {"text": "🔁 Refaire", "callback_data": f"{REFAIRE}:{cle}"},
        ]]}

    # ------------------------------------------------------------------ envois
    def envoyer_message(self, texte: str, *, reponse_a: int | None = None) -> int:
        donnees = {"chat_id": self.chat_id, "text": couper(texte, LIMITE_MESSAGE),
                   "parse_mode": "HTML", "disable_web_page_preview": True}
        if reponse_a:
            donnees["reply_parameters"] = {"message_id": reponse_a, "allow_sending_without_reply": True}
        return self.appel("sendMessage", json_corps=donnees)["message_id"]

    def envoyer_video(self, chemin: str | Path, legende: str, cle: str,
                      miniature: str | Path | None = None, details: str | None = None) -> int:
        """Envoie la vidéo avec les 3 boutons. `details` (texte long) part en réponse si besoin."""
        chemin = Path(chemin)
        taille = chemin.stat().st_size
        if taille >= TAILLE_MAX_VIDEO:
            raise ErreurTelegram(f"vidéo trop lourde pour Telegram : {taille / 1e6:.1f} Mo (max 50)")
        donnees = {"chat_id": self.chat_id, "caption": couper(legende, LIMITE_LEGENDE),
                   "parse_mode": "HTML", "supports_streaming": "true",
                   "width": "1080", "height": "1920",
                   "reply_markup": json.dumps(self.clavier(cle))}
        fichiers = {"video": (chemin.name, chemin.read_bytes(), "video/mp4")}
        if miniature and Path(miniature).exists() and Path(miniature).stat().st_size < 200_000:
            fichiers["thumbnail"] = (Path(miniature).name, Path(miniature).read_bytes(), "image/jpeg")
        message_id = self.appel("sendVideo", donnees=donnees, fichiers=fichiers, timeout=300)["message_id"]
        if details:
            self.envoyer_message(details, reponse_a=message_id)
        return message_id

    def envoyer_photo(self, chemin: str | Path, legende: str, *, reponse_a: int | None = None) -> int:
        chemin = Path(chemin)
        donnees = {"chat_id": self.chat_id, "caption": couper(legende, LIMITE_LEGENDE), "parse_mode": "HTML"}
        if reponse_a:
            donnees["reply_parameters"] = json.dumps({"message_id": reponse_a, "allow_sending_without_reply": True})
        fichiers = {"photo": (chemin.name, chemin.read_bytes(), "image/jpeg")}
        return self.appel("sendPhoto", donnees=donnees, fichiers=fichiers)["message_id"]

    def editer_legende(self, message_id: int, legende: str, garder_boutons_de: str | None = None) -> None:
        """Remplace la légende ; sans `garder_boutons_de`, les boutons disparaissent."""
        corps = {"chat_id": self.chat_id, "message_id": message_id,
                 "caption": couper(legende, LIMITE_LEGENDE), "parse_mode": "HTML"}
        if garder_boutons_de:
            corps["reply_markup"] = self.clavier(garder_boutons_de)
        try:
            self.appel("editMessageCaption", json_corps=corps)
        except ErreurTelegram as exc:
            if "message is not modified" not in str(exc):
                raise

    def repondre_bouton(self, callback_id: str, texte: str) -> None:
        """answerCallbackQuery ; un bouton trop ancien (> quelques minutes) est ignoré sans erreur."""
        try:
            self.appel("answerCallbackQuery", json_corps={"callback_query_id": callback_id,
                                                          "text": couper(texte, 200)}, tentatives=1)
        except ErreurTelegram as exc:
            log.debug("answerCallbackQuery ignoré : %s", exc)

    # ------------------------------------------------------------------ lecture
    def lire(self, offset: int) -> tuple[list[Evenement], int]:
        """Lit les nouvelles mises à jour. Renvoie (événements autorisés, nouvel offset)."""
        mises_a_jour = self.appel("getUpdates", json_corps={
            "offset": offset, "timeout": 0, "limit": 100,
            "allowed_updates": ["message", "callback_query"],
        })
        evenements: list[Evenement] = []
        nouvel_offset = offset
        for maj in mises_a_jour:
            nouvel_offset = max(nouvel_offset, int(maj["update_id"]) + 1)
            evt = self._interpreter(maj)
            if evt:
                evenements.append(evt)
        return evenements, nouvel_offset

    def lire_tout(self, offset: int) -> tuple[list[Evenement], int]:
        """UNE seule lecture (100 max). Telegram supprime les clics dont l'identifiant est inférieur à l'offset demandé :
        on ne redemande donc pas avec le nouvel offset dans la même passe. Le nouvel offset est enregistré dans l'état et
        envoyé au passage SUIVANT, donc seulement après la sauvegarde réussie de cette passe. Si la sauvegarde échoue,
        les mêmes clics reviennent et sont traités une 2e fois sans effet (statut déjà changé)."""
        return self.lire(offset)

    def moi(self) -> str:
        """@nom du bot utilisé par le robot (pour vérifier que c'est bien celui qui envoie les vidéos)."""
        try:
            r = self.appel("getMe")
            return "@" + r.get("username", "?") if isinstance(r, dict) else "?"
        except Exception:  # noqa: BLE001
            return "?"

    def _autorise(self, chat: dict | None) -> bool:
        return chat is not None and str(chat.get("id")) == self.chat_id

    def _interpreter(self, maj: dict) -> Evenement | None:
        if "callback_query" in maj:
            cq = maj["callback_query"]
            message = cq.get("message") or {}
            if not self._autorise(message.get("chat")):
                log.warning("Bouton ignoré : chat non autorisé")
                return None
            prefixe, _, cle = str(cq.get("data", "")).partition(":")
            if prefixe not in ACTIONS or not cle:
                return None
            return Evenement("bouton", ACTIONS[prefixe], cle=cle, callback_id=cq.get("id", ""),
                             message_id=message.get("message_id"))
        message = maj.get("message")
        if message:
            if not self._autorise(message.get("chat")):
                log.warning("Message ignoré : chat non autorisé")
                return None
            texte = (message.get("text") or "").strip()
            if texte.startswith("/"):
                mots = texte[1:].split()
                commande = mots[0].split("@")[0].lower() if mots else ""
                if commande in COMMANDES_EPISODE and len(mots) > 1:
                    cle = mots[1].upper()
                    cle = cle if cle.startswith("EP") else "EP%03d" % int(cle) if cle.isdigit() else cle
                    return Evenement("bouton", COMMANDES_EPISODE[commande], cle=cle, message_id=message.get("message_id"))
                if commande in COMMANDES:
                    return Evenement("commande", "aide" if commande == "start" else commande,
                                     message_id=message.get("message_id"))
        return None
