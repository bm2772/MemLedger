import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # eval/ and infra/ are scripts at the repo root, not installed packages
    sys.path.insert(0, str(ROOT))

import pytest


@pytest.fixture(autouse=True)
def offline_models(monkeypatch):
    """The demo runs real models only; its tests swap in the deterministic FooledModel and the code-only checkers."""
    from fooled import FooledModel

    from demo import chat

    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    monkeypatch.setattr(chat, "default_llm", FooledModel)
