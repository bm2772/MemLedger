"""bench/hallucination_eval.py: the hallucination check on RAGTruth / HaluEval (slide 13), offline with fixtures."""

from bench import load
from bench.hallucination_eval import at, auroc, best_threshold, evaluate, judge, markdown, scores, tuned
from memledger.guards.hallucination import HallucinationCheck
from tests.test_bench import root  # noqa: F401  (tiny on-disk benchmark fixtures)


def row(label, score, threshold=0.5, dataset="d"):
    return {"id": f"{label}{score}", "dataset": dataset, "group": "g", "label": label, "score": score,
            "rejected": score < threshold, "ms": 1.0}


def test_scores_treat_hallucinated_as_positive():
    rows = [row("hallucinated", 0.1), row("hallucinated", 0.9), row("supported", 0.2), row("supported", 0.8)]
    s = scores(rows)
    assert (s["tp"], s["fn"], s["fp"], s["tn"]) == (1, 1, 1, 1) and s["f1"] == 0.5
    assert s["precision"]["x"] == 1 and s["precision"]["n"] == 2 and s["false_rejection"]["n"] == 2


def test_auroc_and_threshold_choice():
    rows = [row("hallucinated", 0.1), row("hallucinated", 0.3), row("supported", 0.4), row("supported", 0.9)]
    assert auroc(rows) == 1.0 and auroc(rows[:2]) is None
    assert best_threshold(rows) == 0.4  # separates them; of the ties, the one nearest the production 0.5
    assert [r["rejected"] for r in at(rows, 0.4)] == [True, True, False, False]  # as the check: score < threshold


def test_tuned_threshold_comes_from_dev_rows_only():
    dev = [row("hallucinated", 0.1), row("supported", 0.2)]
    test = [row("hallucinated", 0.25), row("supported", 0.9)]
    res = {"d": {"all": scores(test)}}
    tuned(res, test, dev)
    assert res["d"]["tuned"]["threshold"] == 0.2 and res["d"]["tuned"]["dev_n"] == 2
    assert res["d"]["tuned"]["fn"] == 1  # 0.25 passes at the dev threshold


def test_halueval_answer_is_the_memory_and_the_question_its_context(root):  # noqa: F811
    ep = load("halueval", "test", 1, root=root)[0]
    assert ep.steps[0].text in ("r", "h") and [s.content for s in ep.seeds] == ["k", f"Question: {ep.meta['question']}"]


def test_evaluate_runs_the_production_check_and_resumes_from_its_log(root, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("MEMLEDGER_DATA", str(root))
    check = HallucinationCheck(scorer=lambda doc, claim: 0.9 if claim.lower() in doc.lower() else 0.1)
    log = tmp_path / "test.jsonl"
    res, rows = evaluate(["ragtruth"], "test", None, 0, check, log=log)
    assert len(rows) == 2 and len(log.read_text().splitlines()) == 2
    assert res["ragtruth"]["all"]["n"] == 2 and set(res["ragtruth"]["by_group"]) == {"QA", "Summary"}
    calls = []
    _, rows2 = evaluate(["ragtruth"], "test", None, 0, lambda *a: calls.append(a), log=log)  # nothing re-judged
    assert rows2 == rows and not calls and len(log.read_text().splitlines()) == 2
    md = markdown(res, {"split": "test", "scorer": "x", "threshold": 0.5, "chunk_words": 350, "limit": None, "seed": 0})
    assert "| ragtruth | 2 (1) |" in md
    assert judge(check, load("ragtruth", "test", None, root=root)[0])["dataset"] == "ragtruth"
