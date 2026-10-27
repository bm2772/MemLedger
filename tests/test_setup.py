"""M3 reproducible setup: model fetcher, dataset licences, committed suite manifest (no network)."""

import json
import sys
import types

from bench import download, fetch_models


def test_every_dataset_has_a_licence_note():
    assert set(download.LICENSES) == set(download.NAMES)


def test_fetch_models_skips_gated_without_token_and_keeps_going(monkeypatch, capsys):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.setitem(sys.modules, "huggingface_hub", types.ModuleType("huggingface_hub"))  # CI has no [models]
    calls = []

    def fake_fetch(model_id, patterns, check_only=False):
        calls.append(model_id)
        if "nli" in model_id:
            raise OSError("offline")
        return "1.00 GB at /cache"

    monkeypatch.setattr(fetch_models, "fetch", fake_fetch)
    assert fetch_models.main([]) == 0  # downloading never fails setup
    out = capsys.readouterr().out
    assert "Llama-Prompt-Guard-2-86M: skipped (gated" in out and "DeBERTa-v3-large-mnli-fever-anli-ling-wanli: skipped (OSError" in out
    assert len(calls) == len(fetch_models.MODELS) - 1
    assert fetch_models.main(["--check"]) == 1  # --check reports the missing model


def test_suite_writes_committed_manifest(tmp_path, monkeypatch):
    from attacks import suite

    monkeypatch.setattr(suite, "FAMILY_SIZES", {k: 1 for k in suite.FAMILY_SIZES})
    out, man = tmp_path / "attacks", tmp_path / "docs" / "suite_manifest.json"
    suite.main(["--out", str(out), "--dev-worlds", "1", "--test-worlds", "1", "--bench-limit", "1",
                "--manifest", str(man)])
    assert json.loads(man.read_text()) == json.loads((out / "manifest.json").read_text())
