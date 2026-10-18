"""Lecture de config.yaml et des secrets (variables d'environnement = « Secrets » GitHub)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent

DEFAUTS = {
    "identite": {"nom_compte": "Shape Saga"},
    "cadence": {"fuseau": "Europe/Paris", "creneaux": ["12:00", "19:00"], "marge_minutes": 30},
    "validation": {"delai_heures": 48, "rappel_heures": 24, "max_en_attente": 4},
    "publication": {
        "plateformes": ["tiktok", "youtube", "instagram"],
        "publieurs": {"tiktok": "buffer", "youtube": "buffer", "instagram": "buffer"},
        "limite_file_par_canal": 10,
        "contenu_ia": False,
        "buffer": {"organisation_id": "", "canaux": {"tiktok": "", "youtube": "", "instagram": ""},
                   "youtube_categorie": "24"},
        "hebergement": {"depot": "", "tag_release": "videos", "conserver_jours": 10},
    },
    "alertes": {"repetition_heures": 12},
}


class ErreurConfig(ValueError):
    pass


def _fusionner(base: dict, ajout: dict) -> dict:
    sortie = dict(base)
    for cle, valeur in (ajout or {}).items():
        if isinstance(valeur, dict) and isinstance(sortie.get(cle), dict):
            sortie[cle] = _fusionner(sortie[cle], valeur)
        else:
            sortie[cle] = valeur
    return sortie


def charger_config(chemin: str | Path | None = None) -> dict:
    chemin = Path(chemin) if chemin else RACINE / "config.yaml"
    contenu: dict = {}
    if chemin.exists():
        contenu = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}
    conf = _fusionner(DEFAUTS, contenu)
    for p in conf["publication"]["plateformes"]:
        if p not in ("tiktok", "youtube", "instagram"):
            raise ErreurConfig(f"plateforme inconnue : {p}")
        if conf["publication"]["publieurs"].get(p) != "buffer":
            raise ErreurConfig(f"seul Buffer est branché pour l'instant ({p})")
    return conf


def _env(nom: str) -> str:
    return (os.environ.get(nom) or "").strip()


@dataclass(frozen=True)
class Secrets:
    """Jamais écrits sur disque ni dans les journaux."""

    telegram_token: str = ""
    telegram_chat_id: str = ""
    buffer: str = ""
    github_token: str = ""
    github_depot: str = ""

    @classmethod
    def depuis_env(cls) -> "Secrets":
        return cls(telegram_token=_env("TELEGRAM_BOT_TOKEN"), telegram_chat_id=_env("TELEGRAM_CHAT_ID"),
                   buffer=_env("BUFFER_API_KEY"), github_token=_env("GITHUB_TOKEN"),
                   github_depot=_env("GITHUB_REPOSITORY"))

    def masquer(self, texte: str) -> str:
        for valeur in (self.telegram_token, self.buffer, self.github_token):
            if valeur and len(valeur) >= 6:
                texte = texte.replace(valeur, "***")
        return texte

    def manquants(self) -> list[str]:
        requis = {"TELEGRAM_BOT_TOKEN": self.telegram_token, "TELEGRAM_CHAT_ID": self.telegram_chat_id,
                  "BUFFER_API_KEY": self.buffer}
        return [n for n, v in requis.items() if not v]
