"""Test du parcours complet avec de FAUX serveurs (Telegram, GitHub, Buffer) : aucune vraie clé nécessaire."""
import json
import re
from datetime import datetime, timezone

import pytest

from robot import reseau
from robot.config import Secrets, charger_config
from robot.etat import BROUILLON, ENVOYE, PROGRAMME, Etat
from robot.orchestrateur import Orchestrateur

reseau.dormir = lambda s: None


class Rep:
    def __init__(self, donnees, statut=200):
        self._d, self.status_code, self.headers = donnees, statut, {}
        self.text = json.dumps(donnees); self.ok = statut < 400; self.content = b"x"

    def json(self):
        return self._d


class FauxSession:
    def __init__(self):
        self.headers = {}; self.appels = []; self.mises_a_jour = []; self.posts = []; self.assets = []

    def request(self, methode, url, **kw):
        self.appels.append((methode, url))
        if "api.telegram.org" in url:
            m = url.rsplit("/", 1)[-1]
            if m == "getUpdates":
                lot, self.mises_a_jour = self.mises_a_jour, []
                return Rep({"ok": True, "result": lot})
            if m in ("sendVideo", "sendMessage"):
                return Rep({"ok": True, "result": {"message_id": 100 + len(self.appels)}})
            return Rep({"ok": True, "result": {"username": "shape_bot"} if m == "getMe" else True})
        if "uploads.github.com" in url:
            nom = kw["params"]["name"]; a = {"id": 7, "name": nom, "size": 1,
                                              "browser_download_url": f"https://github.com/ShapeSaga/shape-saga/releases/download/videos/{nom}"}
            self.assets.append(a); return Rep(a, 201)
        if "api.github.com" in url:
            if url.endswith("/releases/tags/videos"):
                return Rep({}, 404)
            if url.endswith("/releases"):
                return Rep({"id": 1, "tag_name": "videos"}, 201)
            if "/assets" in url:
                return Rep(self.assets)
        if "api.buffer.com" in url:
            q = kw["json"]["query"]; v = kw["json"].get("variables", {})
            if "organizations" in q:
                return Rep({"data": {"account": {"organizations": [{"id": "org1", "name": "x"}]}}})
            if "channels(" in q:
                return Rep({"data": {"channels": [
                    {"id": f"c-{s}", "name": s, "displayName": s, "service": s, "isQueuePaused": False}
                    for s in ("tiktok", "youtube", "instagram")]}})
            if "posts(" in q:
                return Rep({"data": {"posts": {"edges": []}}})
            if "createPost" in q:
                self.posts.append(v["input"])
                return Rep({"data": {"createPost": {"__typename": "PostActionSuccess",
                                                    "post": {"id": f"p{len(self.posts)}", "dueAt": v["input"].get("dueAt")}}}})
        raise AssertionError(f"appel inattendu : {methode} {url}")


def bouton(action, cle):
    return {"update_id": 1, "callback_query": {"id": "cb", "data": f"{action}:{cle}",
                                               "message": {"message_id": 5, "chat": {"id": 42}}}}


@pytest.fixture
def monde(tmp_path):
    eps = tmp_path / "episodes"; eps.mkdir()
    for nom, test in (("EP000", True), ("EP001", False)):
        (eps / f"{nom}.mp4").write_bytes(b"v")
        (eps / f"{nom}.json").write_text(json.dumps({"id": nom, "titre": f"Titre {nom}", "legende": "Une histoire.",
                                                     "hashtags": ["#shapesaga"], "test": test}))
    s = FauxSession()
    sec = Secrets("tok", "42", "cle-buffer-123", "ghp_xxxxxx", "ShapeSaga/shape-saga")
    maintenant = [datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc)]
    o = Orchestrateur(config=charger_config(), secrets=sec, etat=Etat(tmp_path / "etat.json"), session=s,
                      maintenant=lambda: maintenant[0], dossier_episodes=eps)
    return o, s


def test_parcours_complet(monde):
    o, s = monde
    o.cycle()                                              # envoie les 2 vidéos sur Telegram
    assert o.etat.episodes["EP000"]["statut"] == ENVOYE and o.etat.episodes["EP001"]["statut"] == ENVOYE
    s.mises_a_jour = [bouton("v", "EP000"), bouton("v", "EP001")]
    o.cycle()                                              # ✅ ✅ → hébergement + Buffer
    assert o.etat.episodes["EP000"]["statut"] == BROUILLON
    assert o.etat.episodes["EP001"]["statut"] == PROGRAMME
    brouillons, vrais = s.posts[:3], s.posts[3:]
    assert all(p.get("saveToDraft") and "dueAt" not in p for p in brouillons)
    assert len(vrais) == 3 and all("saveToDraft" not in p and p["dueAt"].endswith("Z") for p in vrais)
    for p in s.posts:                                      # uniquement des champs qui existent dans le schéma Buffer
        assert p["assets"][0]["video"]["url"].startswith("https://github.com/ShapeSaga/")
        assert "isAiGenerated" not in json.dumps(p["metadata"].get("youtube", {}) | p["metadata"].get("instagram", {}))
    yt = [p for p in vrais if "youtube" in p["metadata"]][0]
    assert yt["metadata"]["youtube"]["title"] == "Titre EP001" and yt["metadata"]["youtube"]["madeForKids"] is False
    assert o.etat.episodes["EP001"]["creneau"].startswith("2026-10-20T10:00")        # 12 h Paris = 10 h UTC (heure d'été)


def test_refus_et_double_clic(monde):
    o, s = monde
    o.cycle()
    s.mises_a_jour = [bouton("r", "EP001")]
    o.cycle()
    assert o.etat.episodes["EP001"]["statut"] == "refuse"
    s.mises_a_jour = [bouton("v", "EP001")]
    o.cycle()
    assert o.etat.episodes["EP001"]["statut"] == "refuse"      # un refus ne se transforme pas en publication
    assert not [p for p in s.posts if "EP001" in json.dumps(p)]


def test_deux_videos_deux_creneaux_differents(monde):
    o, s = monde
    for ep in ("EP000",):
        pass
    c1 = o.prochain_creneau().astimezone(timezone.utc).isoformat()
    o.etat.episodes["X"] = {"statut": PROGRAMME, "creneau": c1}
    c2 = o.prochain_creneau().astimezone(timezone.utc).isoformat()
    assert c1 != c2 and c1.startswith("2026-10-20T10:00") and c2.startswith("2026-10-20T18:00")   # 20 h à Paris (heure d été)


def test_pause(monde):
    o, s = monde
    o.cycle()
    o.etat.donnees["pause"] = True
    s.mises_a_jour = [bouton("v", "EP001")]
    o.cycle()
    assert o.etat.episodes["EP001"]["statut"] == "valide" and not s.posts
