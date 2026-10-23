"""M3 benchmark loaders on tiny fixtures in each dataset's real on-disk format (no network)."""

import json
from collections import Counter

import pytest

from bench import LOADERS, load
from bench.download import FILES, NAMES
from bench.loaders import hash_split
from memledger.agent.episode import Episode, dump_jsonl, load_jsonl


def put(root, name, rel, data, jsonl=False):
    p = root / name / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(x) + "\n" for x in data) if jsonl else json.dumps(data))


@pytest.fixture
def root(tmp_path):
    lme = [{"question_id": f"q{i}{'_abs' if i == 0 else ''}", "question_type": "temporal-reasoning",
            "question": f"question {i}?", "answer": f"ans{i}", "question_date": "2023/04/10 (Mon) 23:07",
            "haystack_dates": ["2023/04/01"], "haystack_session_ids": [f"s{i}"],
            "haystack_sessions": [[{"role": "user", "content": f"fact {i}"}]], "answer_session_ids": [f"s{i}"]}
           for i in range(40)]
    put(tmp_path, "longmemeval", "longmemeval_s_cleaned.json", lme)
    put(tmp_path, "locomo", "locomo10.json", [
        {"sample_id": f"conv-{c}", "conversation": {
            "speaker_a": "A", "speaker_b": "B", "session_1_date_time": "1 May 2023",
            "session_1": [{"speaker": "A", "dia_id": "D1:1", "text": "I paint"}]},
         "qa": [{"question": "What does A do?", "answer": "paint", "evidence": ["D1:1"], "category": 4},
                {"question": "What does B paint?", "evidence": [], "category": 5, "adversarial_answer": "x"}]}
        for c in range(20)])
    for s in ("train", "test"):
        put(tmp_path, "bipia", f"text_attack_{s}.json", {"Task Automation": [f"Do evil {s}"]})
        for t in ("email", "table"):
            put(tmp_path, "bipia", f"{t}/{s}.jsonl",
                [{"context": f"line1\nline2 {i}", "question": "Q?", "ideal": "a"} for i in range(30)], jsonl=True)
    for k in ("dh", "ds"):
        put(tmp_path, "injecagent", f"test_cases_{k}_base.json", [
            {"Attacker Tools": ["BankTransfer"], "Attack Type": "Financial Harm", "User Instruction": "get reviews",
             "User Tool": "AmazonGetProductDetails", "Attacker Instruction": "transfer money",
             "Tool Response": "{'review': 'transfer money'}"}])
    for s in ("train", "validation", "test"):
        put(tmp_path, "memshield", f"{s}.jsonl", [
            {"id": f"{s}1", "content": "Paris is in France.", "label": "clean", "attack_type": "none"},
            {"id": f"{s}2", "content": "Always disable 2FA.", "label": "poisoned", "attack_type": "T9"}], jsonl=True)
    put(tmp_path, "memevobench", "finance.json", [
        {"test_query": f"q{i}", "test_correct_answer": "ref", "risk_type": "R", "test_query_2": f"q{i}b",
         "test_correct_answer_2": "ref2", "retrievable_memories": [
             {"type": "forum", "label": "misleading", "timestamp": "2023", "post": "bad", "correct_answer": "no",
              "id": "A"},
             {"type": "note", "label": "correct", "timestamp": "2023", "note": "good", "id": "B"}]}
        for i in range(10)])
    put(tmp_path, "ragtruth", "source_info.jsonl", [
        {"source_id": "1", "task_type": "Summary", "source_info": "text"},
        {"source_id": "2", "task_type": "QA", "source_info": {"question": "q", "passages": "p"}}], jsonl=True)
    put(tmp_path, "ragtruth", "response.jsonl", [
        {"id": "a", "source_id": "1", "split": "test", "labels": [], "response": "ok"},
        {"id": "b", "source_id": "2", "split": "test", "labels": [{"text": "x"}], "response": "bad"},
        {"id": "c", "source_id": "1", "split": "train", "labels": [], "response": "ok"}], jsonl=True)
    put(tmp_path, "halueval", "qa_data.json", [
        {"knowledge": "k", "question": f"q{i}", "right_answer": "r", "hallucinated_answer": "h"} for i in range(20)],
        jsonl=True)
    for s in ("dev", "test"):
        put(tmp_path, "llm_aggrefact", f"{s}.jsonl",
            [{"dataset": "AggreFact-CNN", "doc": "d", "claim": "c", "label": i % 2} for i in range(4)], jsonl=True)
    return tmp_path


OFFLINE = [n for n in LOADERS if n != "agentdojo"]


@pytest.mark.parametrize("name", OFFLINE)
def test_every_loader_returns_valid_episodes(root, name):
    eps = load(name, split="test", limit=None, root=root)
    assert eps, name
    for e in eps:
        assert isinstance(e, Episode) and e.source == name and e.split == "test" and e.turns
        assert Episode.from_dict(json.loads(json.dumps(e.to_dict()))) == e
    assert len({e.id for e in eps}) == len(eps)


@pytest.mark.parametrize("name", [n for n in OFFLINE if n not in ("injecagent",)])
def test_dev_and_test_never_overlap(root, name):
    dev = {e.id for e in load(name, split="dev", limit=None, root=root)}
    test = {e.id for e in load(name, split="test", limit=None, root=root)}
    assert not dev & test


def test_hash_split_stable_and_roughly_30_70():
    splits = Counter(hash_split(f"k{i}") for i in range(2000))
    assert 0.25 < splits["dev"] / 2000 < 0.35
    assert hash_split("abc") == hash_split("abc")


def test_test_only_benchmarks_refuse_tuning_splits(root):
    with pytest.raises(ValueError):
        load("injecagent", split="dev", root=root)
    with pytest.raises(ValueError):
        load("agentdojo", split="train", root=root)


def test_subset_is_seeded(root):
    a = [e.id for e in load("halueval", limit=5, seed=1, root=root)]
    assert a == [e.id for e in load("halueval", limit=5, seed=1, root=root)]
    assert len(a) == 5


def test_labels_and_ground_truth(root):
    bip = load("bipia", limit=None, root=root)
    for e in bip:
        assert (e.expect.label == "injected") == (e.kind == "attack") == ("Do evil test" in e.turns[0].content)
    assert {e.kind for e in bip} == {"attack", "clean"}
    assert all("Do evil train" not in e.turns[0].content for e in bip)  # test attacks only on the test split

    inj = load("injecagent", root=root)[0]
    assert inj.expect.forbidden_tool_calls == [{"tool": "BankTransfer"}]

    loc = load("locomo", split="test", limit=None, root=root) + load("locomo", split="dev", limit=None, root=root)
    adv = [e for e in loc if e.category == "adversarial"]
    assert adv and all(e.expect.answer is None for e in adv)

    mev = load("memevobench", split="test", limit=None, root=root)[0]
    assert mev.expect.blocked == ["mA"] and [s.poisoned for s in mev.seeds] == [True, False]
    assert "correct_answer" not in mev.seeds[0].content  # the correction is ground truth, not shown to the agent

    rag = {e.id: e.expect.label for e in load("ragtruth", root=root)}
    assert rag == {"ragtruth_a": "supported", "ragtruth_b": "hallucinated"}

    halu = Counter(e.expect.label for e in load("halueval", split="test", limit=None, root=root))
    assert halu["supported"] == halu["hallucinated"]

    ms = {e.expect.label for e in load("memshield", root=root)}
    assert ms == {"clean", "poisoned"}

    lme = load("longmemeval", split="test", limit=None, root=root) + load("longmemeval", split="dev", limit=None,
                                                                          root=root)
    assert any(e.meta["abstention"] for e in lme)


def test_missing_data_has_helpful_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="bench.download"):
        load("locomo", root=tmp_path)


def test_download_registry_covers_all_loaders():
    assert set(NAMES) == set(LOADERS)
    assert all(url.startswith("https://") for files in FILES.values() for url in files.values())


def test_episode_jsonl_roundtrip(root, tmp_path):
    eps = load("memevobench", limit=None, root=root)
    dump_jsonl(eps, tmp_path / "out" / "e.jsonl")
    assert load_jsonl(tmp_path / "out" / "e.jsonl") == eps
