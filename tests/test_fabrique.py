import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "moteur"))
import fabrique


def test_nouveaux_episodes_si_file_vide():
    assert fabrique.a_fabriquer({}) == [1, 2]


def test_file_pleine_ne_fabrique_pas_de_nouveau():
    eps = {f"EP00{i}": {"statut": "envoye"} for i in range(1, 5)}
    assert fabrique.a_fabriquer(eps) == [1, 2, 3, 4]      # on refait seulement ceux en attente


def test_episode_de_test_en_attente_est_refait():
    eps = {"EP001": {"statut": "envoye", "test": True}}
    assert 1 in fabrique.a_fabriquer(eps)


def test_test_ep000_ignore_et_valide_refait():
    eps = {"EP000": {"statut": "brouillon", "test": True}, "EP001": {"statut": "valide"}}
    assert fabrique.a_fabriquer(eps) == [1, 2, 3]
