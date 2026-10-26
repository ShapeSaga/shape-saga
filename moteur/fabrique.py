"""Fabrique les épisodes dont le robot a besoin, avant chaque cycle.
 - les épisodes en attente de ✅ (statut envoye) ou validés (valide) ont besoin de leur .mp4 ;
 - de nouveaux épisodes sont fabriqués tant qu'il y a de la place dans la file d'attente de validation.
Un même numéro redonne toujours le même épisode : les vidéos ne sont donc pas stockées dans GitHub, on les refait au besoin.
Chaque épisode est fabriqué dans son propre processus, pour rester identique d'une fois sur l'autre."""
import json
import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
from robot import planning  # noqa: E402  (calendrier partagé avec le robot)
ETAT = RACINE / "etat" / "etat.json"
ECHECS = RACINE / "etat" / "echecs_fabrication.json"     # lu par le robot, qui prévient sur Telegram
EPISODES = RACINE / "episodes"
MAX_NOUVEAUX_PAR_PASSAGE = 4             # une semaine = 14 vidéos : envoyées par paquets de 4


def numero(cle):
    return int(cle[2:]) if cle.startswith("EP") and cle[2:].isdigit() else None


def a_fabriquer(episodes, max_attente=4, nouveaux_max=None):
    """episodes : le dictionnaire etat["episodes"]. Renvoie la liste triée des numéros à fabriquer.
    nouveaux_max : nombre de créneaux libres à remplir (calendrier quotidien) ; None = ancien fonctionnement (file d'attente)."""
    besoin = {numero(k) for k, f in episodes.items()
              if f.get("statut") == "valide" and not f.get("video_url")}
    attente = sum(1 for f in episodes.values() if f.get("statut") == "envoye")
    connus = [numero(k) for k in episodes if numero(k) is not None]
    prochain = max(connus + [0]) + 1
    place = min(max(max_attente - attente, 0), MAX_NOUVEAUX_PAR_PASSAGE)
    if nouveaux_max is not None:                         # calendrier : on remplit les créneaux libres, quelle que soit la file
        place = min(MAX_NOUVEAUX_PAR_PASSAGE, nouveaux_max)
    nouveaux = set(range(prochain, prochain + place))
    return sorted(n for n in (besoin | nouveaux) if n)


def mode_test():
    """config.yaml -> fabrique.mode_test : true = les épisodes partent en BROUILLON Buffer après ✅ (rien n'est publié)."""
    try:
        import yaml
        conf = yaml.safe_load((RACINE / "config.yaml").read_text(encoding="utf-8")) or {}
        return bool((conf.get("fabrique") or {}).get("mode_test", False))
    except Exception:  # noqa: BLE001
        return True                                      # dans le doute, on ne publie rien


def marquer_test(fichier_json):
    meta = json.loads(fichier_json.read_text(encoding="utf-8"))
    if not meta.get("test"):
        meta["test"] = True
        meta["titre"] = "[TEST] " + meta.get("titre", "")
        fichier_json.write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")


def main(liste_seulement=False):
    """liste_seulement : n'affiche que ce qu'il faudrait fabriquer (sans rien fabriquer) et l'écrit pour GitHub Actions,
    qui saute alors l'installation lourde (ffmpeg, cairo…) quand il n'y a rien à faire : passage en moins d'une minute."""
    episodes = {}
    if ETAT.exists():
        episodes = json.loads(ETAT.read_text(encoding="utf-8")).get("episodes", {})
    EPISODES.mkdir(exist_ok=True)
    test, echecs = mode_test(), []
    nouveaux_max = None
    try:
        import yaml
        from datetime import datetime, timezone
        cad = (yaml.safe_load((RACINE / "config.yaml").read_text(encoding="utf-8")) or {}).get("cadence", {})
        if (cad.get("envoi") or cad.get("jours_avance")) and not test:
            nouveaux_max = len(planning.places_libres(episodes, datetime.now(timezone.utc), cad)[1])
    except Exception as exc:  # noqa: BLE001
        print("Calendrier illisible, ancien fonctionnement :", exc, flush=True)
    numeros = a_fabriquer(episodes, nouveaux_max=nouveaux_max)
    if liste_seulement:
        print("À fabriquer :", ["EP%03d" % n for n in numeros] or "rien (veille)", flush=True)
        sortie = os.environ.get("GITHUB_OUTPUT")
        if sortie:
            with open(sortie, "a", encoding="utf-8") as f:
                f.write("besoin=" + ("oui" if numeros else "non") + chr(10))
        return
    for n in numeros:
        ep = "EP%03d" % n
        if (EPISODES / (ep + ".mp4")).exists() and (EPISODES / (ep + ".json")).exists():
            continue
        print("Fabrication de", ep, flush=True)
        r = subprocess.run([sys.executable, str(Path(__file__).with_name("generateur.py")), str(n), str(EPISODES)],
                           capture_output=True, text=True)
        print(r.stdout[-2000:], r.stderr[-4000:], flush=True)
        if r.returncode != 0:
            print("ÉCHEC de la fabrication de", ep, "- le cycle continue sans lui", flush=True)
            derniere = (r.stderr.strip().splitlines() or ["erreur inconnue"])[-1]
            echecs.append({"episode": ep, "erreur": derniere[:300]})
        elif test:
            marquer_test(EPISODES / (ep + ".json"))
    ECHECS.parent.mkdir(exist_ok=True)
    texte = json.dumps(echecs, indent=1, ensure_ascii=False)
    if not ECHECS.exists() or ECHECS.read_text(encoding="utf-8") != texte:   # n'écrit que si ça change (moins de conflits git)
        ECHECS.write_text(texte, encoding="utf-8")


if __name__ == "__main__":
    main(liste_seulement="--liste" in sys.argv)
