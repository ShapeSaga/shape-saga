"""Calendrier quotidien : envoi à 19 h des vidéos du lendemain, validation la nuit, publication à 12 h et 20 h."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from robot import planning  # noqa: E402
from robot.etat import Etat  # noqa: E402
from robot.orchestrateur import Orchestrateur  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")
CAD = {"fuseau": "Europe/Paris", "envoi": "19:00", "creneaux": ["12:00", "20:00"], "marge_minutes": 30}


def paris(j, h, m=0):
    return datetime(2026, 10, j, h, m, tzinfo=PARIS)


def test_jour_cible():
    assert planning.jour_cible(paris(26, 18, 59), CAD) is None              # l'après-midi : rien
    assert planning.jour_cible(paris(26, 19, 5), CAD).day == 27            # le soir : le lendemain
    assert planning.jour_cible(paris(27, 2, 0), CAD).day == 27             # la nuit : toujours ce jour-là
    assert planning.jour_cible(paris(27, 11, 0), CAD) is None              # trop près de midi


class FauxBot:
    def __init__(self):
        self.videos, self.messages = [], []

    def envoyer_video(self, f, legende, cle, miniature=None, details=None):
        self.videos.append((cle, details)); return len(self.videos)

    def envoyer_photo(self, *a, **k):
        return 0

    def envoyer_message(self, texte, reponse_a=None):
        self.messages.append(texte); return 0

    def editer_legende(self, *a, **k):
        pass


class FauxPublieur:
    def places_disponibles(self, p):
        return 5

    def programmer(self, pub):
        self.dates = getattr(self, "dates", []) + [pub.date]
        from robot.publieurs import Resultat
        return Resultat(id_distant="x", message="ok")


class FauxHebergeur:
    def deposer(self, *a, **k):
        return {"url": "https://exemple/v.mp4"}


def orchestrateur(tmp_path, quand, etat):
    conf = __import__("robot.config", fromlist=["x"]).charger_config()
    conf["cadence"] = dict(CAD)
    o = Orchestrateur(config=conf, secrets=object(), etat=etat, dossier_episodes=tmp_path, maintenant=lambda: quand)
    o._bot, o._heberg = FauxBot(), FauxHebergeur()
    pub = FauxPublieur()
    o._publieurs = {p: pub for p in ("tiktok", "youtube", "instagram")}
    return o, pub


def episodes(tmp_path, *ids):
    for i in ids:
        (tmp_path / f"{i}.mp4").write_bytes(b"x")
        (tmp_path / f"{i}.json").write_text(json.dumps({"id": i, "titre": i, "legende": "l", "hashtags": []}), encoding="utf-8")


def test_journee_complete(tmp_path):
    etat = Etat.__new__(Etat)
    etat.donnees = {"episodes": {}, "alertes": {}, "offset": 0, "pause": False}
    etat.fichier = tmp_path / "etat.json"
    episodes(tmp_path, "EP005", "EP006", "EP007")
    # 15 h : rien ne part
    o, _ = orchestrateur(tmp_path, paris(26, 15), etat)
    o.envoyer_nouveaux()
    assert not o.bot.videos
    # 19 h 07 : les 2 vidéos de demain partent, une par créneau
    o, _ = orchestrateur(tmp_path, paris(26, 19, 7), etat)
    o.envoyer_nouveaux()
    assert [c for c, _ in o.bot.videos] == ["EP005", "EP006"]
    fiches = [m for m in o.bot.messages if "Publication prévue" in m]
    assert "mardi 27/10 à 12:00" in fiches[0] and "mardi 27/10 à 20:00" in fiches[1]
    # 23 h : ✅ sur EP005, ❌ sur EP006
    etat.episodes["EP005"]["statut"] = "valide"
    etat.episodes["EP006"]["statut"] = "refuse"
    o, pub = orchestrateur(tmp_path, paris(26, 23), etat)
    o.publier_valides()
    assert etat.episodes["EP005"]["statut"] == "programme"
    assert pub.dates[0].astimezone(PARIS) == paris(27, 12)
    # 23 h 07 : le remplaçant part pour 20 h
    o.envoyer_nouveaux()
    assert [c for c, _ in o.bot.videos] == ["EP007"] and "mardi 27/10 à 20:00" in o.bot.messages[-1]
    # 20 h 01 le lendemain sans réponse : EP007 n'est pas publié
    o, _ = orchestrateur(tmp_path, paris(27, 20, 1), etat)
    o.gerer_delais()
    assert etat.episodes["EP007"]["statut"] == "expire"


def test_fabrique_ne_fabrique_que_les_places_libres():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "moteur"))
    import fabrique
    eps = {"EP005": {"statut": "programme", "creneau": paris(27, 12).astimezone(timezone.utc).isoformat()}}
    libres = planning.places_libres(eps, paris(26, 19, 7), CAD)[1]
    assert len(libres) == 1
    assert fabrique.a_fabriquer(eps, nouveaux_max=len(libres)) == [6]
