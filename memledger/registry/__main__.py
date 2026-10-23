"""CLI for the signed registry (slide 9).

    python -m memledger.registry keygen --out keys/registry          # keys/registry.key (secret) + .pub
    python -m memledger.registry sign entries.json --key keys/registry.key --out registry.json \
        --user alice --role registry-admin
    python -m memledger.registry verify registry.json --pub keys/registry.pub
    python -m memledger.registry get registry.json --pub keys/registry.pub "Acme Ltd/account"

entries.json is a JSON list of {key, value, confidentiality?, owner?, valid_from?}. --user/--role stand in for
company SSO (stub); signing is refused unless the role is 'registry-admin'. Exit code 1 on any refusal.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from memledger.core.types import Session
from memledger.registry import signing
from memledger.registry.registry import Registry, RegistryError, sign_entries, write_signed
from memledger.registry.schema import Entry, SchemaError


def _keygen(a: argparse.Namespace) -> int:
    key = signing.generate()
    signing.save_private_key(key, f"{a.out}.key")
    signing.save_public_key(key.public_key(), f"{a.out}.pub")
    print(f"wrote {a.out}.key (keep secret, never commit) and {a.out}.pub")
    return 0


def _sign(a: argparse.Namespace) -> int:
    raw = json.loads(Path(a.entries).read_text())
    entries = [Entry.from_dict(e) for e in (raw["entries"] if isinstance(raw, dict) else raw)]
    doc = sign_entries(entries, signing.load_private_key(a.key), Session(a.user, "shared", a.role, 0))
    write_signed(doc, a.out)
    print(f"signed {len(entries)} entries -> {a.out}")
    return 0


def _verify(a: argparse.Namespace) -> int:
    reg = Registry.load(a.registry, a.pub)
    print(f"OK: {len(reg.entries())} entries, signature valid")
    return 0


def _get(a: argparse.Namespace) -> int:
    value = Registry.load(a.registry, a.pub).get_key(a.key)
    if value is None:
        print(f"no current value for {a.key!r}", file=sys.stderr)
        return 1
    print(value)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m memledger.registry", description="Signed company registry")
    sub = p.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keygen", help="create an Ed25519 key pair")
    k.add_argument("--out", required=True, help="path prefix; writes <out>.key and <out>.pub")
    s = sub.add_parser("sign", help="sign a list of entries")
    s.add_argument("entries")
    s.add_argument("--key", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--user", required=True)
    s.add_argument("--role", required=True)
    v = sub.add_parser("verify", help="check a signed registry")
    v.add_argument("registry")
    v.add_argument("--pub", required=True)
    g = sub.add_parser("get", help="print the current value of '<subject>/<field>'")
    g.add_argument("registry")
    g.add_argument("key")
    g.add_argument("--pub", required=True)
    a = p.parse_args(argv)
    try:
        return {"keygen": _keygen, "sign": _sign, "verify": _verify, "get": _get}[a.cmd](a)
    except (RegistryError, SchemaError, PermissionError, ValueError, TypeError, OSError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
