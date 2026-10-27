"""Workspaces: one persistent memory (SQLite store + signing keys + signed registry) built as one of the 5 versions.

On disk, under $MEMLEDGER_DATA_DIR/<id>/:
    meta.json        name, version, web pages the agent may read
    store.sqlite     the append-only provenance store (memledger/store/sqlite.py)
    ledger.key       Ed25519 key that signs the Merkle roots (slide 14); without it roots cannot be re-verified
    registry.key     Ed25519 key of the company registry; registry.json is the signed document (slides 8, 9)
    activity.jsonl   who did what through the console (append-only)

The service is rebuilt from these files on start and whenever the registry changes; the vector index is rebuilt
from the stored claims. data_dir=None keeps everything in memory (tests).
"""

from __future__ import annotations

import json
import re
import secrets
import shutil
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from memledger.core.factory import build_service
from memledger.core.service import LedgerService
from memledger.core.types import Session
from memledger.registry import Entry, Registry, require_admin, sign_entries, signing
from memledger.store.index import InMemoryIndex
from memledger.store.sqlite import SQLiteStore

VERSIONS = ["full", "full_no_registry", "write_checks", "provenance", "baseline"]
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Workspace:
    def __init__(self, ws_id: str, meta: dict, root: Path | None, models: dict[str, Any]) -> None:
        self.id, self.meta, self.root, self.models = ws_id, meta, root, models
        self.lock = threading.RLock()  # one SQLite connection per workspace; FastAPI runs sync routes in threads
        self.store = SQLiteStore(str(root / "store.sqlite") if root else ":memory:")
        self.ledger_key = self._key("ledger.key")
        self.registry_key = self._key("registry.key")
        self.registry_doc: dict | None = self._read_json("registry.json")
        self.activity: list[dict] = self._read_activity()
        self.service = self._build()

    # ---- files
    def _key(self, name: str):
        if self.root is None:
            return signing.generate()
        path = self.root / name
        if not path.exists():
            signing.save_private_key(signing.generate(), path)
        return signing.load_private_key(path)

    def _read_json(self, name: str) -> dict | None:
        path = self.root / name if self.root else None
        return json.loads(path.read_text()) if path and path.exists() else None

    def _write_json(self, name: str, doc: dict) -> None:
        if self.root is not None:
            tmp = self.root / f".{name}.tmp"
            tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
            tmp.replace(self.root / name)

    def _read_activity(self) -> list[dict]:
        path = self.root / "activity.jsonl" if self.root else None
        if not path or not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    # ---- service
    @property
    def version(self) -> str:
        return self.meta["version"]

    @property
    def registry(self) -> Registry | None:
        if self.registry_doc is None:
            return None
        return Registry.from_doc(self.registry_doc, self.registry_key.public_key())

    def _build(self) -> LedgerService:
        index = InMemoryIndex()
        for c in self.store.list_claims():
            index.add(c.labels.team, c.id, c.text)
        reg = None  # full_no_registry runs without the registry (slide 17)
        if self.version == "full":
            reg = self.registry or Registry.from_mapping({})  # an empty registry protects nothing but is valid
        svc = build_service(self.version, registry=reg, store=self.store, index=index, **self.models)
        svc.signing_key, svc.public_key = self.ledger_key, self.ledger_key.public_key()  # roots survive restarts
        return svc

    def log(self, session: Session, action: str, **detail: Any) -> dict:
        row = {"at": _now(), "user": session.user_id, "team": session.team, "action": action, **detail}
        self.activity.append(row)
        if self.root is not None:
            with (self.root / "activity.jsonl").open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    # ---- registry (admin only; history is kept, the newest valid_from wins)
    def registry_entries(self) -> list[Entry]:
        reg = self.registry
        return reg.entries() if reg else []

    def set_registry_value(self, session: Session, subject: str, field: str, value: str,
                           confidentiality: int = 0) -> Entry:
        require_admin(session)
        entry = Entry(f"{subject.strip()}/{field.strip()}", value.strip(), confidentiality, session.user_id,
                      datetime.now(UTC))
        self.registry_doc = sign_entries([*self.registry_entries(), entry], self.registry_key, session)
        self._write_json("registry.json", self.registry_doc)
        self._swap_registry()
        return entry

    def _swap_registry(self) -> None:
        """Point the running service's registry check and action gate at the new signed registry. The service is not
        rebuilt: that would drop session taint (I3/I4) and the approval queue, i.e. clear taint without a person."""
        if self.version != "full":
            return
        reg = self.registry
        for c in self.service.checks:
            if type(c).__name__ == "RegistryCheck":
                c.registry = reg
        if self.service.gate is not None and getattr(self.service.gate, "registry", None) is not None:
            self.service.gate.registry = reg

    def set_web_page(self, url: str, content: str) -> None:
        self.meta.setdefault("web_pages", {})[url] = content
        self._write_json("meta.json", self.meta)

    def summary(self) -> dict:
        return {"id": self.id, "name": self.meta["name"], "version": self.version,
                "created_at": self.meta["created_at"], "description": self.meta.get("description", "")}


class Workspaces:
    """All workspaces of one server. data_dir=None keeps them in memory."""

    def __init__(self, data_dir: str | Path | None, models: dict[str, Any] | None = None) -> None:
        self.dir = Path(data_dir) if data_dir else None
        self.models = models or {}
        self.lock = threading.Lock()
        self.items: dict[str, Workspace] = {}
        if self.dir is not None:
            self.dir.mkdir(parents=True, exist_ok=True)
            for meta_path in sorted(self.dir.glob("*/meta.json")):
                ws_id = meta_path.parent.name
                self.items[ws_id] = Workspace(ws_id, json.loads(meta_path.read_text()), meta_path.parent, self.models)

    def list(self) -> list[Workspace]:
        return sorted(self.items.values(), key=lambda w: w.meta["created_at"])

    def get(self, ws_id: str) -> Workspace:
        return self.items[ws_id]

    def create(self, name: str, version: str = "full", description: str = "") -> Workspace:
        if version not in VERSIONS:
            raise ValueError(f"unknown version {version!r}; choose from {VERSIONS}")
        name = name.strip() or "Untitled workspace"
        with self.lock:
            base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "ws"
            ws_id = base if base not in self.items and _ID.match(base) else f"{base}-{secrets.token_hex(3)}"
            root = None
            if self.dir is not None:
                root = self.dir / ws_id
                root.mkdir()
            meta = {"name": name, "version": version, "description": description, "created_at": _now(),
                    "web_pages": {}}
            ws = Workspace(ws_id, meta, root, self.models)
            ws._write_json("meta.json", meta)
            self.items[ws_id] = ws
            return ws

    def delete(self, ws_id: str) -> None:
        with self.lock:
            ws = self.items.pop(ws_id)
            ws.store.conn.close()
            if ws.root is not None:
                shutil.rmtree(ws.root)
