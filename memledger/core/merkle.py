"""Slide 14: Merkle anchor."""

from __future__ import annotations

import hashlib


def _h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _node(left: str, right: str) -> str:
    return _h(bytes.fromhex(left) + bytes.fromhex(right))


def _levels(hashes: list[str]) -> list[list[str]]:
    level = [_h(bytes.fromhex(x)) for x in sorted(hashes)]
    levels = [level]
    while len(level) > 1:
        if len(level) % 2:
            level = level + [level[-1]]
        level = [_node(level[i], level[i + 1]) for i in range(0, len(level), 2)]
        levels.append(level)
    return levels


def merkle_root(hashes: list[str]) -> str:
    if not hashes:
        return _h(b"")
    return _levels(hashes)[-1][0]


def merkle_proof(hashes: list[str], target: str) -> list[tuple[str, str]]:
    """Sibling hashes from leaf to root, each tagged 'L' or 'R' (side of the sibling)."""
    ordered = sorted(hashes)
    if target not in ordered:
        raise ValueError("target not in hashes")
    idx = ordered.index(target)
    proof = []
    for level in _levels(hashes)[:-1]:
        padded = level + [level[-1]] if len(level) % 2 else level
        sib = idx ^ 1
        proof.append((padded[sib], "L" if sib < idx else "R"))
        idx //= 2
    return proof


def verify_proof(target: str, proof: list[tuple[str, str]], root: str) -> bool:
    cur = _h(bytes.fromhex(target))
    for sibling, side in proof:
        cur = _node(sibling, cur) if side == "L" else _node(cur, sibling)
    return cur == root
