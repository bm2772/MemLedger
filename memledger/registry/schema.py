"""Registry entry schema (slides 8, 9): protected facts that have exactly one correct value.

An entry's key is "<subject>/<field>", e.g. "Acme Ltd/account". Several entries may share a key with different
valid_from times; the latest one that has started is the current value (history is kept, nothing is overwritten).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
FIELDS = ("key", "value", "confidentiality", "owner", "valid_from")


class SchemaError(ValueError):
    pass


def norm_subject(subject: str) -> str:
    return " ".join(subject.lower().split())


@dataclass(frozen=True)
class Entry:
    key: str
    value: str
    confidentiality: int = 0
    owner: str = ""
    valid_from: datetime = EPOCH

    @property
    def subject(self) -> str:
        return self.key.rpartition("/")[0]

    @property
    def field(self) -> str:
        return self.key.rpartition("/")[2]

    def to_dict(self) -> dict:
        return {"key": self.key, "value": self.value, "confidentiality": self.confidentiality,
                "owner": self.owner, "valid_from": self.valid_from.isoformat()}

    @classmethod
    def from_dict(cls, d: object) -> Entry:
        if not isinstance(d, dict):
            raise SchemaError(f"entry must be an object, got {type(d).__name__}")
        missing, extra = set(FIELDS) - set(d), set(d) - set(FIELDS)
        if missing - {"confidentiality", "owner", "valid_from"} or extra:
            raise SchemaError(f"entry fields must be {FIELDS}; missing {sorted(missing)}, unknown {sorted(extra)}")
        key, value = d["key"], d["value"]
        if not isinstance(key, str) or "/" not in key or not all(p.strip() for p in key.rpartition("/")[::2]):
            raise SchemaError(f"key must be '<subject>/<field>', got {key!r}")
        if not isinstance(value, str) or not value.strip():
            raise SchemaError(f"{key}: value must be a non-empty string")
        conf = d.get("confidentiality", 0)
        if not isinstance(conf, int) or isinstance(conf, bool) or conf < 0:
            raise SchemaError(f"{key}: confidentiality must be an int >= 0")
        owner = d.get("owner", "")
        if not isinstance(owner, str):
            raise SchemaError(f"{key}: owner must be a string")
        vf = d.get("valid_from")
        try:
            valid_from = EPOCH if vf is None else datetime.fromisoformat(vf)
        except (TypeError, ValueError) as e:
            raise SchemaError(f"{key}: valid_from must be an ISO-8601 time") from e
        if valid_from.tzinfo is None:
            raise SchemaError(f"{key}: valid_from needs a timezone")
        return cls(key.strip(), value, conf, owner, valid_from)


def check_unique(entries: list[Entry]) -> None:
    seen: set[tuple[str, str, datetime]] = set()
    for e in entries:
        k = (norm_subject(e.subject), e.field.lower(), e.valid_from)
        if k in seen:
            raise SchemaError(f"duplicate entry {e.key} at {e.valid_from.isoformat()}")
        seen.add(k)
