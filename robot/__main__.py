"""    python -m robot cycle                # ce que lance GitHub Actions toutes les heures
    python -m robot cycle --essai        # tout, sauf envoyer pour de vrai à Buffer
    python -m robot tester-connexions    # vérifie Telegram, Buffer, hébergement GitHub
    python -m robot statut
"""
from __future__ import annotations

import argparse
import logging
import sys

from .config import Secrets, charger_config
from .etat import Etat


def tester_connexions(o) -> int:
    ok = True
    print("Secrets manquants :", ", ".join(o.secrets.manquants()) or "aucun ✅")
    try:
        me = o.bot.appel("getMe"); print(f"Telegram ✅ bot @{me.get('username')}")
    except Exception as exc:  # noqa: BLE001
        ok = False; print("Telegram ❌", o.secrets.masquer(str(exc)))
    try:
        print("Buffer ✅", o.publieurs["tiktok"].tester_connexion())
    except Exception as exc:  # noqa: BLE001
        ok = False; print("Buffer ❌", o.secrets.masquer(str(exc)))
    try:
        rel = o.hebergeur.release(); print("Hébergement GitHub ✅ release", rel.get("tag_name"))
    except Exception as exc:  # noqa: BLE001
        ok = False; print("Hébergement GitHub ❌", o.secrets.masquer(str(exc)))
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m robot")
    ap.add_argument("commande", choices=["cycle", "tester-connexions", "statut"])
    ap.add_argument("--essai", action="store_true")
    ap.add_argument("--config", default=None)
    ap.add_argument("-v", "--verbeux", action="store_true")
    a = ap.parse_args(argv)
    secrets = Secrets.depuis_env()
    logging.basicConfig(level=logging.DEBUG if a.verbeux else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s : %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    from .orchestrateur import Orchestrateur
    o = Orchestrateur(config=charger_config(a.config), secrets=secrets, etat=Etat(), essai=a.essai)
    if a.commande == "cycle":
        o.cycle(); return 0
    if a.commande == "tester-connexions":
        return tester_connexions(o)
    print(o.texte_statut().replace("<b>", "").replace("</b>", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
