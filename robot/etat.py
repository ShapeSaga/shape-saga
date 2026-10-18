"""Mémoire du robot : un seul fichier etat/etat.json, sauvegardé dans le dépôt après chaque passage."""
from __future__ import annotations

import json
from pathlib import Path

from .config import RACINE

FICHIER = RACINE / "etat" / "etat.json"

# statuts d'un épisode
ENVOYE = "envoye"          # vidéo envoyée sur Telegram, en attente de ✅ / ❌
VALIDE = "valide"          # ✅ reçu, publication en cours
PROGRAMME = "programme"    # programmé sur les 3 réseaux
BROUILLON = "brouillon"    # épisode de test : brouillons Buffer, rien de publié
PUBLIE = "publie"          # créneau passé
REFUSE = "refuse"          # ❌ (ou 🔁 : pas encore géré)
EXPIRE = "expire"          # aucune réponse dans le délai


class Etat:
    def __init__(self, fichier: Path | None = None):
        self.fichier = Path(fichier) if fichier else FICHIER
        self.donnees = {"offset": 0, "pause": False, "episodes": {}, "alertes": {}}
        if self.fichier.exists():
            self.donnees.update(json.loads(self.fichier.read_text(encoding="utf-8")))

    @property
    def episodes(self) -> dict:
        return self.donnees["episodes"]

    def sauvegarder(self) -> None:
        self.fichier.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.fichier.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.donnees, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        tmp.replace(self.fichier)
