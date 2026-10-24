"""Who is calling: bearer tokens mapped to Sessions (identity comes from login, never from the model).

Production: set $MEMLEDGER_USERS to a JSON file
    {"<token>": {"user_id": "ria", "team": "team_a", "role": "researcher", "clearance": 1}, ...}
and every request needs `Authorization: Bearer <token>`.

Without it the server runs in open mode for local use: the UI picks one of DEMO_USERS with the X-MemLedger-User
header. Open mode is refused unless the server binds to localhost (web/__main__.py).
"""

from __future__ import annotations

import hmac
import json
import os
from dataclasses import asdict
from pathlib import Path

from memledger.core.types import Session
from memledger.registry import ADMIN_ROLE

DEMO_USERS: dict[str, Session] = {
    "ria": Session("ria", "team_a", "researcher", 1),
    "fin": Session("fin", "team_a", "finance", 1),
    "bo": Session("bo", "team_b", "analyst", 1),
    "admin": Session("admin", "team_a", ADMIN_ROLE, 3),
}


class Unauthorized(Exception):
    pass


def session_dict(s: Session) -> dict:
    return {**asdict(s), "admin": s.role == ADMIN_ROLE}


class Auth:
    def __init__(self, tokens: dict[str, Session] | None = None) -> None:
        self.tokens = tokens  # None = open mode

    @classmethod
    def from_env(cls) -> Auth:
        path = os.environ.get("MEMLEDGER_USERS")
        if not path:
            return cls(None)
        raw = json.loads(Path(path).read_text())
        return cls({tok: Session(u["user_id"], u["team"], u["role"], int(u["clearance"])) for tok, u in raw.items()})

    @property
    def open(self) -> bool:
        return self.tokens is None

    def session(self, authorization: str | None, demo_user: str | None) -> Session:
        if self.tokens is None:
            return DEMO_USERS.get(demo_user or "", DEMO_USERS["ria"])
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() == "bearer":
            for known, s in self.tokens.items():  # constant-time compare against every token
                if hmac.compare_digest(known.encode(), token.encode()):
                    return s
        raise Unauthorized("missing or unknown bearer token")
