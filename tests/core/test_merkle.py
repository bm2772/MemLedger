import hashlib

import pytest

from memledger.core.merkle import merkle_proof, merkle_root, verify_proof


def hs(n):
    return [hashlib.sha256(str(i).encode()).hexdigest() for i in range(n)]


def test_empty_root():
    assert merkle_root([]) == hashlib.sha256(b"").hexdigest()


def test_single_leaf_root_is_leaf_hash():
    h = hs(1)[0]
    assert merkle_root([h]) == hashlib.sha256(b"\x00" + bytes.fromhex(h)).hexdigest()


def test_duplicated_last_leaf_does_not_share_a_root():
    """CVE-2012-2459 pattern: an odd level must not duplicate its last node."""
    a, b, c, d = hs(4)
    assert merkle_root([a, b, c]) != merkle_root([a, b, c, d])
    assert merkle_root([a, b, c]) == merkle_root([a, b, c, c])  # a set: duplicates are one leaf
    assert merkle_root([a, b]) != merkle_root([b]) and merkle_root([a]) != a


@pytest.mark.parametrize("n", [1, 2, 3, 5, 6, 7, 9])
def test_proofs_verify_for_all_leaves(n):
    leaves = hs(n)
    root = merkle_root(leaves)
    for h in leaves:
        assert verify_proof(h, merkle_proof(leaves, h), root)


def test_wrong_root_or_target_fails():
    leaves = hs(3)
    root = merkle_root(leaves)
    proof = merkle_proof(leaves, leaves[0])
    assert not verify_proof(leaves[0], proof, merkle_root(hs(4)))
    assert not verify_proof(hs(9)[8], proof, root)


def test_order_independent():
    leaves = hs(5)
    assert merkle_root(leaves) == merkle_root(list(reversed(leaves)))


def test_proof_for_missing_leaf_raises():
    with pytest.raises(ValueError):
        merkle_proof(hs(2), hs(5)[4])
