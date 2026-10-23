"""Signed registry (slide 9): sign/verify, refusal of unsigned or altered files (I9), admin role, binding (I10)."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from memledger.core.types import Session
from memledger.registry import (
    Entry,
    Registry,
    RegistryError,
    bind_params,
    default_registry,
    set_default_registry,
    sign_entries,
    signing,
)
from memledger.registry.__main__ import main as cli
from memledger.registry.schema import SchemaError

ADMIN = Session("root", "shared", "registry-admin", 3)
ALICE = Session("alice", "team_a", "researcher", 1)
LOW = Session("intern", "team_a", "intern", 0)

ENTRIES = [
    Entry("Acme Ltd/account", "1234", owner="finance"),
    Entry("Acme Ltd/email", "ap@acme.example", owner="finance"),
    Entry("Globex/account", "5555", confidentiality=2),
]


@pytest.fixture
def key():
    return signing.generate()


@pytest.fixture
def reg_file(tmp_path, key):
    path = tmp_path / "registry.json"
    signing.save_public_key(key.public_key(), tmp_path / "pub.pem")
    path.write_text(json.dumps(sign_entries(ENTRIES, key, ADMIN)))
    return path


def test_sign_and_read(reg_file, key):
    reg = Registry.load(reg_file, key.public_key())
    assert reg.get("Acme Ltd", "account") == "1234"
    assert reg.get("acme  ltd", "ACCOUNT") == "1234"  # subject/field matching is case and space insensitive
    assert reg("Acme Ltd", "email") == "ap@acme.example"  # callable = M3's RegistryLookup
    assert reg.get_key("Acme Ltd/account") == "1234"
    assert reg.get("Initech", "account") is None
    assert reg.verify()


def test_unsigned_registry_refused(tmp_path, key):
    doc = sign_entries(ENTRIES, key, ADMIN)
    del doc["signature"]
    path = tmp_path / "r.json"
    path.write_text(json.dumps(doc))
    with pytest.raises(RegistryError, match="unsigned"):
        Registry.load(path, key.public_key())


def test_altered_registry_refused(reg_file, key):
    doc = json.loads(reg_file.read_text())
    doc["entries"][0]["value"] = "9876"
    reg_file.write_text(json.dumps(doc))
    with pytest.raises(RegistryError, match="signature"):
        Registry.load(reg_file, key.public_key())


def test_wrong_key_refused(reg_file):
    with pytest.raises(RegistryError):
        Registry.load(reg_file, signing.generate().public_key())


def test_garbage_refused(tmp_path, key):
    path = tmp_path / "r.json"
    path.write_text("not json")
    with pytest.raises(RegistryError):
        Registry.load(path, key.public_key())
    with pytest.raises(RegistryError):
        Registry.load(tmp_path / "missing.json", key.public_key())


def test_edit_after_load_detected_on_read(reg_file, key):
    """Slide 9: the signature is checked on every read, not only at load time."""
    reg = Registry.load(reg_file, key.public_key())
    assert reg.get("Acme Ltd", "account") == "1234"
    doc = json.loads(reg_file.read_text())
    doc["entries"][0]["value"] = "9876"
    reg_file.write_text(json.dumps(doc))
    with pytest.raises(RegistryError):
        reg.get("Acme Ltd", "account")


def test_resigned_update_is_picked_up(reg_file, key):
    reg = Registry.load(reg_file, key.public_key())
    reg_file.write_text(json.dumps(sign_entries([Entry("Acme Ltd/account", "4321")], key, ADMIN)))
    assert reg.get("Acme Ltd", "account") == "4321"


def test_only_registry_admin_can_sign(key):
    with pytest.raises(PermissionError):
        sign_entries(ENTRIES, key, ALICE)


def test_valid_from_history():
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    entries = [Entry("Acme Ltd/account", "1111", valid_from=t0),
               Entry("Acme Ltd/account", "2222", valid_from=t0 + timedelta(days=30)),
               Entry("Acme Ltd/account", "3333", valid_from=datetime(2999, 1, 1, tzinfo=UTC))]
    key = signing.generate()
    reg = Registry.from_doc(sign_entries(entries, key, ADMIN), key.public_key())
    assert reg.get("Acme Ltd", "account", at=t0 + timedelta(days=1)) == "1111"
    assert reg.get("Acme Ltd", "account") == "2222"  # future entry not yet valid
    assert reg.get("Acme Ltd", "account", at=t0 - timedelta(days=1)) is None
    assert [e.value for e in reg.current()] == ["2222"]


def test_confidentiality_respects_clearance(reg_file, key):
    reg = Registry.load(reg_file, key.public_key())
    assert reg.get("Globex", "account", session=LOW) is None
    assert reg.get("Globex", "account", session=ADMIN) == "5555"
    assert reg.get("Acme Ltd", "account", session=LOW) == "1234"


@pytest.mark.parametrize("bad", [
    {"key": "no-field", "value": "1"},
    {"key": "Acme/account", "value": ""},
    {"key": "Acme/account", "value": "1", "confidentiality": -1},
    {"key": "Acme/account", "value": "1", "valid_from": "2026-01-01T00:00:00"},  # no timezone
    {"key": "Acme/account", "value": "1", "colour": "red"},
    "just a string",
])
def test_schema_rejects_bad_entries(bad):
    with pytest.raises(SchemaError):
        Entry.from_dict(bad)


def test_duplicate_entries_refused(key):
    with pytest.raises(SchemaError):
        sign_entries([Entry("Acme Ltd/account", "1"), Entry("acme ltd/account", "2")], key, ADMIN)


def test_entry_round_trip():
    e = Entry("Acme Ltd/account", "1234", 1, "finance", datetime(2026, 5, 1, tzinfo=UTC))
    assert Entry.from_dict(e.to_dict()) == e
    assert (e.subject, e.field) == ("Acme Ltd", "account")


# ---- binding (I10)
def test_bind_params_overrides_model_value():
    reg = Registry.from_mapping({"Acme Ltd": {"account": "1234"}})
    out = bind_params("send_payment", {"vendor": "Acme Ltd", "amount": 10.0, "account": "9876"}, ALICE, reg)
    assert out == {"vendor": "Acme Ltd", "amount": 10.0, "account": "1234"}


def test_bind_params_fails_closed():
    reg = Registry.from_mapping({"Acme Ltd": {"account": "1234"}})
    assert bind_params("send_payment", {"vendor": "Evil Corp", "account": "9876"}, ALICE, reg)["account"] is None
    assert bind_params("send_payment", {"account": "9876"}, ALICE, reg)["account"] is None
    set_default_registry(None)
    assert bind_params("send_payment", {"vendor": "Acme Ltd", "account": "9876"}, ALICE)["account"] is None


def test_bind_params_leaves_other_tools_alone():
    params = {"to": "x@y.z", "subject": "hi", "body": "b"}
    assert bind_params("send_email", params, ALICE, Registry.from_mapping({})) == params


def test_default_registry_install_and_env(reg_file, key, monkeypatch, tmp_path):
    reg = Registry.from_mapping({"Acme Ltd": {"account": "1234"}})
    set_default_registry(reg)
    try:
        assert default_registry() is reg
        assert bind_params("send_payment", {"vendor": "Acme Ltd"}, ALICE)["account"] == "1234"
        set_default_registry(None)
        monkeypatch.setenv("MEMLEDGER_REGISTRY", str(reg_file))
        monkeypatch.setenv("MEMLEDGER_REGISTRY_PUBKEY", str(tmp_path / "pub.pem"))
        assert default_registry().get("Acme Ltd", "email") == "ap@acme.example"
    finally:
        set_default_registry(None)


# ---- CLI
def test_cli_end_to_end(tmp_path, capsys):
    prefix = tmp_path / "reg"
    entries = tmp_path / "entries.json"
    entries.write_text(json.dumps([e.to_dict() for e in ENTRIES]))
    out = tmp_path / "registry.json"
    assert cli(["keygen", "--out", str(prefix)]) == 0
    assert (tmp_path / "reg.key").stat().st_mode & 0o077 == 0  # private key not readable by others
    assert cli(["keygen", "--out", str(prefix)]) == 1  # never overwrites a key
    base = ["sign", str(entries), "--key", f"{prefix}.key", "--out", str(out), "--user", "root"]
    assert cli(base + ["--role", "researcher"]) == 1
    assert not out.exists()
    assert cli(base + ["--role", "registry-admin"]) == 0
    assert cli(["verify", str(out), "--pub", f"{prefix}.pub"]) == 0
    capsys.readouterr()
    assert cli(["get", str(out), "Acme Ltd/account", "--pub", f"{prefix}.pub"]) == 0
    assert capsys.readouterr().out.strip() == "1234"
    assert cli(["get", str(out), "Nobody/account", "--pub", f"{prefix}.pub"]) == 1
    out.write_text(out.read_text().replace("1234", "9876"))
    assert cli(["verify", str(out), "--pub", f"{prefix}.pub"]) == 1
    assert cli(["get", str(out), "Acme Ltd/account", "--pub", f"{prefix}.pub"]) == 1
