"""Planification sur 7 jours, veille, fenêtre Buffer, et fiabilité des clics Telegram."""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from robot import planning  # noqa: E402
from robot.etat import Etat  # noqa: E402
from robot.telegram_bot import BotTelegram  # noqa: E402
from test_planning import FauxBot, FauxHebergeur, FauxPublieur, episodes  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")
SEMAINE = {"fuseau": "Europe/Paris", "creneaux": ["12:00", "20:00"], "marge_minutes": 30, "jours_avance": 7, "avance_min_heures": 3}


def paris(j, h, m=0):
    return datetime(2026, 10, j, h, m, tzinfo=PARIS)


def etat_vide(tmp_path):
    e = Etat.__new__(Etat)
    e.donnees = {"episodes": {}, "alertes": {}, "offset": 0, "pause": False}
    e.fichier = tmp_path / "etat.json"
    return e


def orch(tmp_path, quand, etat):
    from robot.config import charger_config
    from robot.orchestrateur import Orchestrateur
    conf = charger_config()
    conf["cadence"] = dict(SEMAINE)
    o = Orchestrateur(config=conf, secrets=type("S", (), {"masquer": staticmethod(lambda t: t)})(), etat=etat,
                      dossier_episodes=tmp_path, maintenant=lambda: quand)
    o._bot, o._heberg = FauxBot(), FauxHebergeur()
    pub = FauxPublieur()
    o._publieurs = {p: pub for p in ("tiktok", "youtube", "instagram")}
    return o, pub


def test_semaine_complete_puis_veille(tmp_path):
    # lundi 26/10 à 09:00 : midi est trop proche (< 3 h) -> créneaux de lundi 20 h jusqu'à lundi 2/11 20 h = 15 créneaux
    _, libres = planning.places_libres({}, paris(26, 9), SEMAINE)
    assert libres[0] == paris(26, 20) and libres[-1].date() == paris(26, 9).date() + timedelta(days=7) and len(libres) == 15
    etat = etat_vide(tmp_path)
    ids = [f"EP{n:03d}" for n in range(10, 25)]
    episodes(tmp_path, *ids)
    o, _ = orch(tmp_path, paris(26, 9), etat)
    o.envoyer_nouveaux()
    assert len(o.bot.videos) == 15 and "15 vidéo(s) à valider" in o.bot.messages[0]
    assert all(f.get("video_url") and f.get("meta") for f in etat.episodes.values())      # hébergée dès l'envoi
    # tout est couvert : veille (plus rien à envoyer, plus rien à fabriquer)
    assert planning.places_libres(etat.episodes, paris(26, 9, 10), SEMAINE)[1] == []


def test_valide_en_reserve_au_dela_de_4_jours_et_publie_sans_fichier(tmp_path):
    etat = etat_vide(tmp_path)
    loin, proche = paris(31, 12), paris(27, 12)
    for cle, c in (("EP030", loin), ("EP031", proche)):
        etat.donnees["episodes"][cle] = {"statut": "valide", "creneau_prevu": c.astimezone(ZoneInfo("UTC")).isoformat(),
                                         "programme": {}, "message_id": 1, "video_url": "https://x/v.mp4",
                                         "meta": {"titre": cle, "legende": "l", "hashtags": []}}
    o, pub = orch(tmp_path, paris(26, 9), etat)             # aucun fichier vidéo sur le disque (passage léger)
    o.publier_valides()
    assert etat.episodes["EP031"]["statut"] == "programme" and etat.episodes["EP030"]["statut"] == "valide"
    assert {d.astimezone(PARIS) for d in pub.dates} == {proche}


class SessionTelegram:
    """Faux Telegram : compte les getUpdates et renvoie des clics."""
    def __init__(self, maj):
        self.maj, self.appels, self.headers = maj, [], {}

    def request(self, methode, url, **kw):
        m = url.rsplit("/", 1)[-1]
        self.appels.append((m, (kw.get("json") or {}).get("offset")))
        res = self.maj if m == "getUpdates" else True
        return type("R", (), {"status_code": 200, "ok": True, "json": lambda s: {"ok": True, "result": res}, "text": ""})()


def test_une_seule_lecture_par_passe():
    s = SessionTelegram([{"update_id": 50, "callback_query": {"id": "c", "data": "v:EP005", "message": {"chat": {"id": 42}}}}])
    bot = BotTelegram("jeton", "42", s)
    evts, offset = bot.lire_tout(10)
    assert [m for m, _ in s.appels] == ["getUpdates"] and offset == 51 and evts[0].cle == "EP005"


def test_commande_ok_texte():
    s = SessionTelegram([{"update_id": 7, "message": {"chat": {"id": 42}, "text": "/ok 5"}}])
    evts, _ = BotTelegram("jeton", "42", s).lire_tout(0)
    assert evts[0].type == "bouton" and evts[0].action == "valider" and evts[0].cle == "EP005"


def test_un_clic_en_erreur_ne_bloque_pas_les_suivants(tmp_path):
    from robot.telegram_bot import Evenement
    etat = etat_vide(tmp_path)
    etat.donnees["episodes"].update({"EP005": {"statut": "envoye", "message_id": 1}, "EP006": {"statut": "envoye", "message_id": 2}})
    o, _ = orch(tmp_path, paris(26, 9), etat)
    o.bot.lire_tout = lambda off: ([Evenement("bouton", "valider", cle="EP005", callback_id="a"),
                                    Evenement("bouton", "valider", cle="EP006", callback_id="b")], off + 2)
    o.bot.moi, o.bot.appel = (lambda: "@x"), (lambda *a, **k: {})
    appels = []

    def repondre(cid, t):
        appels.append(cid)
        if cid == "a":
            raise RuntimeError("panne réseau")
    o.bot.repondre_bouton = repondre
    o.lire_telegram()
    assert etat.episodes["EP006"]["statut"] == "valide" and appels == ["a", "b"]


def test_reception_par_le_receptionniste(tmp_path, monkeypatch):
    """Clics lus chez le réceptionniste ; ceux du passage précédent sont confirmés au passage suivant."""
    import robot.orchestrateur as orc
    etat = etat_vide(tmp_path)
    etat.donnees["episodes"]["EP007"] = {"statut": "envoye", "message_id": 1}
    o, _ = orch(tmp_path, paris(27, 9), etat)
    o.secrets.telegram_token = "jeton"
    monkeypatch.setattr(orc.Orchestrateur, "adresse_relais", lambda self: "https://relais.test")
    appels = []

    def faux(session, methode, url, **kw):
        appels.append((methode, url.rsplit("/", 1)[-1], (kw.get("json") or {}).get("ids")))
        res = [{"update_id": 9, "callback_query": {"id": "c", "data": "v:EP007", "message": {"chat": {"id": 42}}}}]
        return type("R", (), {"json": lambda s: {"ok": True, "result": res if url.endswith("/clics") else []}})()
    import robot.reseau
    monkeypatch.setattr(robot.reseau, "requete", faux)
    o.bot.chat_id = "42"
    o.bot._interpreter = __import__("robot.telegram_bot", fromlist=["x"]).BotTelegram("j", "42")._interpreter
    o.lire_telegram()
    assert etat.episodes["EP007"]["statut"] == "valide" and etat.donnees["relais_a_confirmer"] == [9]
    o.lire_telegram()                                       # passage suivant : confirmation des clics déjà sauvegardés
    assert ("POST", "ack", [9]) in appels


def test_instagram_option_payante_reessaye_sans_option():
    """Buffer gratuit refuse les options payantes : pas de premier commentaire, et nouvel essai sans miniature."""
    from robot.publieurs.base import Publication
    from robot.publieurs.buffer import PublieurBuffer
    b = PublieurBuffer.__new__(PublieurBuffer)
    b.canal = lambda p: {"id": "c1"}
    envois = []

    def gql(req, variables=None, tentatives=3):
        envois.append(variables["input"])
        if len(envois) == 1:
            return {"createPost": {"__typename": "MutationError", "message": "This feature requires a paid plan"}}
        return {"createPost": {"__typename": "PostActionSuccess", "post": {"id": "p1"}}}
    b.gql = gql
    p = Publication(cle="EP9-instagram", episode_id="EP9", plateforme="instagram", date=paris(30, 12), texte="t",
                    video_url="https://x/v.mp4", premier_commentaire="vote")
    assert b._programmer(p).id_distant == "p1" and len(envois) == 2
    assert "firstComment" not in envois[0]["metadata"]["instagram"]
    assert "metadata" not in envois[1]["assets"][0]["video"]


def test_correctif_instagram_relance_les_abandons(tmp_path):
    etat = etat_vide(tmp_path)
    etat.donnees["episodes"]["EP008"] = {"statut": "programme", "creneau_prevu": paris(27, 20).astimezone(ZoneInfo("UTC")).isoformat(),
                                         "programme": {"tiktok": {"message": "ok"}, "youtube": {"message": "ok"}}, "refus": {"instagram": 3},
                                         "abandon": {"instagram": True}, "message_id": 1, "video_url": "https://x/v.mp4",
                                         "meta": {"titre": "t", "legende": "l", "hashtags": []}}
    o, pub = orch(tmp_path, paris(27, 9), etat)
    o.publier_valides()
    f = etat.episodes["EP008"]
    assert "instagram" in f["programme"] and f["statut"] == "programme" and not f.get("refus", {}).get("instagram")
