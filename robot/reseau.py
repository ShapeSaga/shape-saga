"""Requêtes HTTP robustes : délai maximal, nouvelles tentatives, respect de Retry-After."""
from __future__ import annotations

import logging
import random
import time

import requests

log = logging.getLogger(__name__)

DELAI_DEFAUT = 60          # secondes
ATTENTE_MAX = 60           # secondes, plafond entre deux tentatives
CODES_TEMPORAIRES = {408, 425, 429, 500, 502, 503, 504}

# Remplaçable dans les tests pour ne pas attendre réellement.
dormir = time.sleep


class ErreurHTTP(RuntimeError):
    def __init__(self, message: str, statut: int | None = None, corps: str = ""):
        super().__init__(message)
        self.statut = statut
        self.corps = corps


def _attente(reponse: requests.Response | None, essai: int, base: float) -> float:
    if reponse is not None:
        valeur = reponse.headers.get("Retry-After")
        if valeur:
            try:
                return min(float(valeur), ATTENTE_MAX)
            except ValueError:
                pass
    return min(base * (2 ** essai) + random.uniform(0, 0.5), ATTENTE_MAX)


def requete(session: requests.Session, methode: str, url: str, *, tentatives: int = 3,
            attente_base: float = 2.0, accepter: tuple[int, ...] = (), etiquette: str | None = None,
            **kwargs) -> requests.Response:
    """Envoie une requête ; réessaie sur erreur réseau ou code temporaire.

    `etiquette` remplace l'URL dans les messages (indispensable quand l'URL contient un jeton).
    Lève ErreurHTTP si la réponse finale n'est pas un succès (2xx ou code de `accepter`).
    """
    kwargs.setdefault("timeout", DELAI_DEFAUT)
    nom = etiquette or url.split("?")[0]
    derniere: requests.Response | None = None
    for essai in range(tentatives):
        try:
            derniere = session.request(methode, url, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as exc:
            if essai == tentatives - 1:
                raise ErreurHTTP(f"{methode} {nom} : erreur réseau ({exc.__class__.__name__})") from exc
            dormir(_attente(None, essai, attente_base))
            continue
        if derniere.ok or derniere.status_code in accepter:
            return derniere
        if derniere.status_code in CODES_TEMPORAIRES and essai < tentatives - 1:
            attente = _attente(derniere, essai, attente_base)
            log.warning("%s %s → %s, nouvel essai dans %.0f s", methode, nom,
                        derniere.status_code, attente)
            dormir(attente)
            continue
        break
    assert derniere is not None
    raise ErreurHTTP(
        f"{methode} {nom} → HTTP {derniere.status_code} : {derniere.text[:300]}",
        statut=derniere.status_code, corps=derniere.text,
    )
