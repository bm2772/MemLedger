"""Ed25519 keys and canonical signing for the registry (slide 9). Key files are never committed (*.key, *.pem)."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def canonical(doc: dict) -> bytes:
    """Deterministic bytes for signing: sorted keys, no whitespace, UTF-8."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sign(payload: bytes, key: Ed25519PrivateKey) -> str:
    return base64.b64encode(key.sign(payload)).decode()


def verify(payload: bytes, signature_b64: str, key: Ed25519PublicKey) -> bool:
    try:
        key.verify(base64.b64decode(signature_b64, validate=True), payload)
    except (InvalidSignature, ValueError, TypeError):
        return False
    return True


def generate() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def save_private_key(key: Ed25519PrivateKey, path: str | Path) -> None:
    """Writes a PKCS8 PEM readable only by the owner; refuses to overwrite an existing key."""
    data = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                             serialization.NoEncryption())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)


def save_public_key(key: Ed25519PublicKey, path: str | Path) -> None:
    Path(path).write_bytes(key.public_bytes(serialization.Encoding.PEM,
                                            serialization.PublicFormat.SubjectPublicKeyInfo))


def load_private_key(path: str | Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError(f"{path} is not an Ed25519 private key")
    return key


def load_public_key(path: str | Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(Path(path).read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError(f"{path} is not an Ed25519 public key")
    return key
