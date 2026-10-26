"""Calendrier quotidien (demande de Chahine, 26/10/2026) :
- chaque soir à l'heure d'envoi (19 h), les vidéos du LENDEMAIN partent sur Telegram, une par créneau (12 h et 20 h) ;
- Chahine valide quand il veut dans la soirée ou la nuit ; le robot programme alors chaque vidéo à SON créneau ;
- une vidéo refusée est remplacée au passage suivant, tant que la nuit n'est pas finie.
Fonctions pures (sans réseau) : utilisées par le robot ET par moteur/fabrique.py, pour qu'ils soient toujours d'accord."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

ACTIFS = ("envoye", "valide", "programme", "publie")      # un épisode dans ces statuts occupe son créneau
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def _hm(texte: str) -> time:
    h, m = texte.split(":")
    return time(int(h), int(m))


def jour_cible(maintenant: datetime, cadence: dict) -> date | None:
    """Jour dont on prépare les vidéos en ce moment : le lendemain dès l'heure d'envoi, le jour même pendant la nuit
    (jusqu'à 1 h 30 avant son premier créneau). Le reste de la journée : rien à envoyer."""
    if not cadence.get("envoi"):
        return None
    tz = ZoneInfo(cadence["fuseau"])
    now = maintenant.astimezone(tz)
    if now.time() >= _hm(cadence["envoi"]):
        return now.date() + timedelta(days=1)
    premier = datetime.combine(now.date(), min(_hm(h) for h in cadence["creneaux"]), tz)
    if now < premier - timedelta(minutes=90):
        return now.date()
    return None


def creneaux_du_jour(jour: date, cadence: dict) -> list[datetime]:
    tz = ZoneInfo(cadence["fuseau"])
    return [datetime.combine(jour, h, tz) for h in sorted(_hm(x) for x in cadence["creneaux"])]


def places_libres(episodes: dict, maintenant: datetime, cadence: dict) -> tuple[date | None, list[datetime]]:
    """(premier jour concerné, créneaux sans vidéo active).
    Mode « jours_avance » (ex. 7) : tous les créneaux libres des N prochains jours, dès qu'il en manque, à toute heure
    (au moins `avance_min_heures` avant le créneau, pour laisser le temps de valider). Quand tout est couvert : veille.
    Sans jours_avance : ancien mode « chaque soir les vidéos du lendemain »."""
    if cadence.get("jours_avance"):
        tz = ZoneInfo(cadence["fuseau"])
        now = maintenant.astimezone(tz)
        pris = {f.get("creneau") or f.get("creneau_prevu") for f in episodes.values() if f.get("statut") in ACTIFS}
        debut = maintenant + timedelta(hours=cadence.get("avance_min_heures", 3))
        libres = [c for d in range(int(cadence["jours_avance"]) + 1)
                  for c in creneaux_du_jour(now.date() + timedelta(days=d), cadence)
                  if c > debut and c.astimezone(timezone.utc).isoformat() not in pris
                  and c.date() <= now.date() + timedelta(days=int(cadence["jours_avance"]))]
        return (libres[0].date() if libres else None), libres
    jour = jour_cible(maintenant, cadence)
    if jour is None:
        return None, []
    pris = {f.get("creneau") or f.get("creneau_prevu") for f in episodes.values() if f.get("statut") in ACTIFS}
    marge = timedelta(minutes=cadence.get("marge_minutes", 30))
    libres = [c for c in creneaux_du_jour(jour, cadence)
              if c.astimezone(timezone.utc).isoformat() not in pris and c > maintenant + marge]
    return jour, libres


def en_clair(dt: datetime, cadence: dict) -> str:
    """« lundi 26/10 à 12:00 » (heure de Paris)."""
    d = dt.astimezone(ZoneInfo(cadence["fuseau"]))
    return f"{JOURS[d.weekday()]} {d:%d/%m} à {d:%H:%M}"

