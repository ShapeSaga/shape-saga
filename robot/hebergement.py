"""Hébergement des vidéos à une adresse publique via les « Releases » GitHub.

Les vidéos sont déposées comme fichiers joints (assets) d'une release unique
(tag `videos`). L'adresse `browser_download_url` est publique si le dépôt est
public : Buffer, Zernio et Instagram viennent y chercher la vidéo.

Le même stockage sert de « disque » entre deux passages du robot (les machines
GitHub Actions sont effacées après chaque exécution).
"""
from __future__ import annotations

import logging
from pathlib import Path

import requests

from .reseau import ErreurHTTP, requete

log = logging.getLogger(__name__)

API = "https://api.github.com"
UPLOAD = "https://uploads.github.com"


class ErreurHebergement(RuntimeError):
    pass


class HebergeurGitHub:
    def __init__(self, depot: str, jeton: str, tag: str = "videos", session: requests.Session | None = None):
        if not depot or "/" not in depot:
            raise ErreurHebergement("dépôt GitHub inconnu (GITHUB_REPOSITORY ou publication.hebergement.depot)")
        if not jeton:
            raise ErreurHebergement("jeton GitHub absent (GITHUB_TOKEN)")
        self.depot = depot
        self.tag = tag
        self.session = session or requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {jeton}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        self._release: dict | None = None

    def _req(self, methode: str, url: str, **kw) -> requests.Response:
        try:
            return requete(self.session, methode, url, etiquette=f"GitHub {url.split('/repos/')[-1][:60]}", **kw)
        except ErreurHTTP as exc:
            raise ErreurHebergement(str(exc)) from exc

    def release(self) -> dict:
        if self._release:
            return self._release
        rep = self._req("GET", f"{API}/repos/{self.depot}/releases/tags/{self.tag}", accepter=(404,))
        if rep.status_code == 404:
            log.info("Création de la release « %s » pour héberger les vidéos", self.tag)
            rep = self._req("POST", f"{API}/repos/{self.depot}/releases", json={
                "tag_name": self.tag, "name": "Vidéos (hébergement automatique)",
                "body": "Fichiers déposés automatiquement par l'automate. Ne pas modifier à la main.",
                "draft": False, "prerelease": True,
            })
        self._release = rep.json()
        return self._release

    def lister(self) -> list[dict]:
        rel = self.release()
        assets, page = [], 1
        while True:
            rep = self._req("GET", f"{API}/repos/{self.depot}/releases/{rel['id']}/assets",
                            params={"per_page": 100, "page": page})
            lot = rep.json()
            assets.extend(lot)
            if len(lot) < 100:
                return assets
            page += 1

    def supprimer(self, asset_id: int) -> None:
        self._req("DELETE", f"{API}/repos/{self.depot}/releases/assets/{asset_id}", accepter=(404,))

    def supprimer_nom(self, nom: str) -> bool:
        for asset in self.lister():
            if asset["name"] == nom:
                self.supprimer(asset["id"])
                return True
        return False

    def deposer(self, chemin: str | Path, nom: str | None = None, remplacer: bool = True) -> dict:
        """Dépose un fichier ; renvoie {"id", "url"}. Idempotent : réutilise un fichier identique."""
        chemin = Path(chemin)
        nom = nom or chemin.name
        taille = chemin.stat().st_size
        for asset in self.lister():
            if asset["name"] == nom:
                if asset.get("size") == taille and not remplacer:
                    return {"id": asset["id"], "url": asset["browser_download_url"]}
                self.supprimer(asset["id"])
        rel = self.release()
        rep = self._req("POST", f"{UPLOAD}/repos/{self.depot}/releases/{rel['id']}/assets",
                        params={"name": nom}, data=chemin.read_bytes(), timeout=600,
                        headers={"Content-Type": "video/mp4" if nom.endswith(".mp4") else "application/octet-stream"})
        asset = rep.json()
        log.info("Vidéo hébergée : %s (%.1f Mo)", nom, taille / 1e6)
        return {"id": asset["id"], "url": asset["browser_download_url"]}

    def telecharger(self, asset_id: int, destination: str | Path) -> Path:
        """Récupère un fichier déposé (fonctionne aussi si le dépôt est privé)."""
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        rep = self._req("GET", f"{API}/repos/{self.depot}/releases/assets/{asset_id}", timeout=600,
                        headers={"Accept": "application/octet-stream"})
        destination.write_bytes(rep.content)
        return destination
