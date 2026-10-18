"""Publieurs : pour l'instant Buffer seulement (TikTok, YouTube, Instagram)."""
from __future__ import annotations

import requests

from ..config import Secrets
from .base import ErreurPublication, Publication, Publieur, Resultat
from .buffer import PublieurBuffer


def creer_publieurs(config: dict, secrets: Secrets, *, essai: bool = False, etat=None,
                    session: requests.Session | None = None) -> dict[str, Publieur]:
    session = session or requests.Session()
    buffer = PublieurBuffer(config, secrets, session=session, essai=essai, etat=etat)
    return {p: buffer for p in config["publication"]["plateformes"]}


__all__ = ["ErreurPublication", "Publication", "Publieur", "Resultat", "creer_publieurs", "PublieurBuffer"]
