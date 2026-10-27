import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "moteur"))
import fabrique


def test_nouveaux_episodes_si_file_vide():
    assert fabrique.a_fabriquer({}) == [1, 2, 3, 4]          # paquets de 4


def test_file_pleine_ne_fabrique_rien():
    eps = {f"EP00{i}": {"statut": "envoye"} for i in range(1, 5)}
    assert fabrique.a_fabriquer(eps) == []                 # déjà sur Telegram : jamais refabriquées


def test_valide_deja_heberge_pas_refait():
    eps = {"EP001": {"statut": "valide", "video_url": "https://x/EP001.mp4", "meta": {"titre": "t"}}, "EP002": {"statut": "envoye"}}
    assert fabrique.a_fabriquer(eps, nouveaux_max=0) == []


def test_test_ep000_ignore_et_valide_refait():
    eps = {"EP000": {"statut": "brouillon", "test": True}, "EP001": {"statut": "valide"}}
    assert fabrique.a_fabriquer(eps) == [1, 2, 3, 4, 5]     # EP001 validé sans vidéo hébergée + 4 nouveaux


def test_ancien_valide_sans_meta_est_refait():
    eps = {"EP008": {"statut": "valide", "video_url": "https://x/EP008.mp4"},
           "EP009": {"statut": "valide", "video_url": "https://x/EP009.mp4", "meta": {"titre": "t"}}}
    assert fabrique.a_fabriquer(eps, nouveaux_max=0) == [8]
