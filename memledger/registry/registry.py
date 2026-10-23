"""The signed company registry (slides 8, 9; property I9).

File format (JSON):
    {"format": "memledger-registry/1", "signed_by": <user>, "signed_at": <iso>, "entries": [Entry...],
     "signature": <base64 Ed25519 over the canonical JSON of every other field>}

The signature is checked when the file is loaded and again on every read; if the file on disk changes it is
re-verified before any value is returned. An unsigned, altered or malformed registry raises RegistryError and no
value from it is ever returned. Only a Session with role 'registry-admin' may sign (SSO is a stub for the MVP).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from memledger.core.types import Session, now
from memledger.registry import signing
from memledger.registry.schema import Entry, SchemaError, check_unique, norm_subject

FORMAT = "memledger-registry/1"
ADMIN_ROLE = "registry-admin"
SYSTEM_ADMIN = Session("registry-system", "shared", ADMIN_ROLE, 0)  # for registries built in tests/episodes


class RegistryError(Exception):
    """The registry is unsigned, altered or malformed; refuse it (I9)."""


def require_admin(session: Session) -> None:
    """Admin-role check stub: the role comes from the login Session, never from the model."""
    if session.role != ADMIN_ROLE:
        raise PermissionError(f"user {session.user_id!r} (role {session.role!r}) may not change the registry")


def sign_entries(entries: list[Entry], key: Ed25519PrivateKey, session: Session) -> dict:
    require_admin(session)
    check_unique(entries)
    doc = {"format": FORMAT, "signed_by": session.user_id, "signed_at": now().isoformat(),
           "entries": [e.to_dict() for e in entries]}
    return {**doc, "signature": signing.sign(signing.canonical(doc), key)}


def _parse(raw: bytes, key: Ed25519PublicKey) -> tuple[bytes, str, list[Entry]]:
    try:
        doc = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise RegistryError(f"registry is not valid JSON: {e}") from e
    if not isinstance(doc, dict):
        raise RegistryError("registry must be a JSON object")
    sig = doc.pop("signature", None)
    if not isinstance(sig, str) or not sig:
        raise RegistryError("registry is unsigned")
    payload = signing.canonical(doc)
    if not signing.verify(payload, sig, key):
        raise RegistryError("registry signature is invalid (file altered or signed with another key)")
    if doc.get("format") != FORMAT or not isinstance(doc.get("entries"), list):
        raise RegistryError(f"unsupported registry format {doc.get('format')!r}")
    try:
        entries = [Entry.from_dict(e) for e in doc["entries"]]
        check_unique(entries)
    except SchemaError as e:
        raise RegistryError(f"registry schema error: {e}") from e
    return payload, sig, entries


class Registry:
    """Read-only view of a verified registry. Instances are callable as M3's RegistryLookup(subject, field)."""

    def __init__(self, raw: bytes, public_key: Ed25519PublicKey, path: str | Path | None = None) -> None:
        self.public_key = public_key
        self.path = Path(path) if path else None
        self._raw = raw
        self._payload, self._sig, self._entries = _parse(raw, public_key)

    # ---- construction
    @classmethod
    def load(cls, path: str | Path, public_key: Ed25519PublicKey | str | Path) -> Registry:
        if not isinstance(public_key, Ed25519PublicKey):
            public_key = signing.load_public_key(public_key)
        try:
            raw = Path(path).read_bytes()
        except OSError as e:
            raise RegistryError(f"cannot read registry {path}: {e}") from e
        return cls(raw, public_key, path)

    @classmethod
    def from_doc(cls, doc: dict, public_key: Ed25519PublicKey) -> Registry:
        return cls(json.dumps(doc).encode(), public_key)

    @classmethod
    def from_mapping(cls, mapping: dict[str, dict[str, str]], key: Ed25519PrivateKey | None = None,
                     session: Session = SYSTEM_ADMIN) -> Registry:
        """{"Acme Ltd": {"account": "1234"}} -> a freshly signed registry (episodes, tests, demo)."""
        key = key or signing.generate()
        entries = [Entry(f"{subject}/{field}", str(value)) for subject, fields in mapping.items()
                   for field, value in fields.items()]
        return cls.from_doc(sign_entries(entries, key, session), key.public_key())

    # ---- verification on every read
    def _verified(self) -> list[Entry]:
        if self.path is not None:
            try:
                raw = self.path.read_bytes()
            except OSError as e:
                raise RegistryError(f"registry file unreadable: {e}") from e
            if raw != self._raw:  # changed on disk: re-verify, refuse if broken
                self._payload, self._sig, self._entries = _parse(raw, self.public_key)
                self._raw = raw
        if not signing.verify(self._payload, self._sig, self.public_key):
            raise RegistryError("registry signature is invalid")
        return self._entries

    def verify(self) -> bool:
        self._verified()
        return True

    # ---- reads
    def entries(self) -> list[Entry]:
        return list(self._verified())

    def lookup(self, subject: str, field: str, at: datetime | None = None,
               session: Session | None = None) -> Entry | None:
        """Current entry for subject/field (case-insensitive), or None. A session above its clearance gets None."""
        at = at or now()
        s, f = norm_subject(subject), field.strip().lower()
        live = [e for e in self._verified()
                if norm_subject(e.subject) == s and e.field.lower() == f and e.valid_from <= at]
        if not live:
            return None
        entry = max(live, key=lambda e: e.valid_from)
        if session is not None and entry.confidentiality > session.clearance:
            return None
        return entry

    def get(self, subject: str, field: str, at: datetime | None = None, session: Session | None = None) -> str | None:
        e = self.lookup(subject, field, at, session)
        return e.value if e else None

    def get_key(self, key: str, at: datetime | None = None, session: Session | None = None) -> str | None:
        subject, _, field = key.rpartition("/")
        return self.get(subject, field, at, session) if subject else None

    def current(self, at: datetime | None = None) -> list[Entry]:
        """The current entry for every key."""
        keys = {(norm_subject(e.subject), e.field.lower()): e for e in self._verified()}
        return [e for e in (self.lookup(v.subject, v.field, at) for v in keys.values()) if e is not None]

    def __call__(self, subject: str, field: str) -> str | None:
        return self.get(subject, field)


def write_signed(doc: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
