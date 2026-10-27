import pytest

from memledger.store import InMemoryIndex


def test_team_isolation_and_ranking():
    ix = InMemoryIndex()
    ix.add("a", "1", "the cat sat on the mat")
    ix.add("a", "2", "dogs bark loudly")
    ix.add("b", "3", "cat cat cat")
    res = ix.query(["a"], "cat mat")
    assert [i for i, _ in res] == ["1"]
    res = ix.query(["a", "b"], "cat")
    assert {i for i, _ in res} == {"1", "3"}
    assert res[0][1] >= res[1][1]
    assert ix.query(["c"], "cat") == []


def test_k_limit_and_zero_skipped():
    ix = InMemoryIndex()
    for i in range(5):
        ix.add("a", str(i), f"word{i} common")
    assert len(ix.query(["a"], "common", k=3)) == 3
    assert ix.query(["a"], "unrelated") == []


def test_chroma_index():
    pytest.importorskip("chromadb")
    from memledger.store import ChromaIndex

    def embed(texts):
        return [[float("cat" in t), float("dog" in t), 0.1] for t in texts]

    ix = ChromaIndex(embed=embed)
    ix.add("a", "1", "cat")
    ix.add("a", "2", "dog")
    ix.add("b", "3", "cat")
    res = ix.query(["a"], "cat", k=2)
    assert res[0][0] == "1"
    assert "3" not in [i for i, _ in res]
