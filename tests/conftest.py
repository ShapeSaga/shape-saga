"""Les tests n'utilisent jamais le vrai réceptionniste (etat/relais.json du dépôt)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def sans_receptionniste(monkeypatch):
    from robot.orchestrateur import Orchestrateur
    monkeypatch.setattr(Orchestrateur, "adresse_relais", lambda self: None)
