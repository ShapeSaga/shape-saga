"""Interface commune à tous les publieurs (Buffer, Zernio, API officielles)."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import requests

from ..config import Secrets

log = logging.getLogger(__name__)


class ErreurPublication(RuntimeError):
    """Échec de publication. `temporaire=True` : on réessaiera au prochain passage."""

    def __init__(self, message: str, temporaire: bool = True):
        super().__init__(message)
        self.temporaire = temporaire


@dataclass
class Publication:
    cle: str                        # clé interne de l'épisode (ex. S1E004-1)
    episode_id: str                 # ex. S1E004
    plateforme: str                 # tiktok | youtube | instagram
    date: datetime                  # créneau de publication (avec fuseau)
    texte: str                      # légende / description complète
    titre: str = ""                 # titre (YouTube)
    hashtags: list[str] = field(default_factory=list)
    video_url: str = ""             # adresse publique de la vidéo
    obtenir_fichier: Callable[[], Path] | None = None   # pour les API qui veulent le fichier
    contenu_ia: bool = True
    miniature_ms: int = 1500        # image de couverture (TikTok / Instagram)
    premier_commentaire: str = ""   # Instagram : commentaire publié avec la vidéo (sert de sondage)
    brouillon: bool = False         # True = enregistré en BROUILLON, rien n'est publié (épisodes de test)


@dataclass
class Resultat:
    id_distant: str
    url: str = ""
    message: str = ""


class Publieur(ABC):
    nom: str = "abstrait"
    #: True si la plateforme accepte une date future (sinon l'automate publie à l'heure dite)
    programmation_distante: bool = True
    plateformes_supportees: tuple[str, ...] = ("tiktok", "youtube", "instagram")

    def __init__(self, config: dict, secrets: Secrets, session: requests.Session | None = None,
                 essai: bool = False, etat=None):
        self.conf = config
        self.etat = etat                # accès à etat/ (jetons rafraîchis), facultatif
        self.secrets = secrets
        self.session = session or requests.Session()
        self.essai = essai

    @property
    def limite_file(self) -> int | None:
        """Nombre maximal de posts programmés par canal (None = pas de limite connue)."""
        return None

    @abstractmethod
    def tester_connexion(self) -> str:
        """Vérifie les accès. Renvoie un résumé lisible ; lève une exception si problème."""

    @abstractmethod
    def _programmer(self, pub: Publication) -> Resultat:
        """Programme (ou publie immédiatement) la vidéo."""

    def programmer(self, pub: Publication) -> Resultat:
        if pub.plateforme not in self.plateformes_supportees:
            raise ErreurPublication(f"{self.nom} ne gère pas {pub.plateforme}", temporaire=False)
        if self.essai:
            log.info("[ESSAI] %s → %s le %s : « %s »", self.nom, pub.plateforme,
                     pub.date.isoformat(), pub.titre or pub.texte[:60])
            return Resultat(id_distant=f"essai-{pub.cle}-{pub.plateforme}", message="essai (rien envoyé)")
        return self._programmer(pub)

    def places_disponibles(self, plateforme: str) -> int | None:
        """Places libres dans la file distante (None = inconnu / illimité)."""
        return None

    def statistiques(self, depuis: datetime) -> dict | None:
        """Statistiques gratuites disponibles (None si non géré)."""
        return None

    @staticmethod
    def date_utc(dt: datetime) -> str:
        """Date ISO 8601 en UTC avec « Z » (format attendu par la plupart des API)."""
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
