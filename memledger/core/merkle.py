"""Slide 14: Merkle anchor.

Leaves are the sorted, de-duplicated item hashes. Leaf and inner-node hashes are domain-separated (0x00 / 0x01) and an
odd last node is carried up unchanged (RFC 6962 style), so no two different leaf sets share a root: the duplicated-
last-leaf pattern ([a, b, c] and [a, b, c, c] with one root, CVE-2012-2459) cannot occur.
"""

from __future__ import annotations

import hashlib


def _h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _leaf(x: str) -> str:
    return _h(b"\x00" + bytes.fromhex(x))


def _node(left: str, right: str) -> str:
    return _h(b"\x01" + bytes.fromhex(left) + bytes.fromhex(right))


def _levels(hashes: list[str]) -> list[list[str]]:
    level = [_leaf(x) for x in sorted(set(hashes))]
    levels = [level]
    while len(level) > 1:
        nxt = [_node(level[i], level[i + 1]) for i in range(0, len(level) - 1, 2)]
        if len(level) % 2:
            nxt.append(level[-1])  # carried up, not duplicated
        level = nxt
        levels.append(level)
    return levels


def merkle_root(hashes: list[str]) -> str:
    if not hashes:
        return _h(b"")
    return _levels(hashes)[-1][0]


def merkle_proof(hashes: list[str], target: str) -> list[tuple[str, str]]:
    """Sibling hashes from leaf to root, each tagged 'L' or 'R' (side of the sibling); carried-up levels add none."""
    ordered = sorted(set(hashes))
    if target not in ordered:
        raise ValueError("target not in hashes")
    idx = ordered.index(target)
    proof = []
    for level in _levels(hashes)[:-1]:
        sib = idx ^ 1
        if sib < len(level):
            proof.append((level[sib], "L" if sib < idx else "R"))
        idx //= 2
    return proof


def verify_proof(target: str, proof: list[tuple[str, str]], root: str) -> bool:
    cur = _leaf(target)
    for sibling, side in proof:
        cur = _node(sibling, cur) if side == "L" else _node(cur, sibling)
    return cur == root
