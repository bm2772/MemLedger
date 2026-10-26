"""memshield decision threshold: chosen on validation at training time, read back by MemshieldCheck (slide 11)."""

import json

from memledger.guards.memshield import MemshieldCheck, model_threshold
from memledger.guards.train.train_memshield import pick_threshold


def test_pick_threshold_max_recall_within_false_rejection_budget():
    y = [0] * 20 + [1] * 5
    s = [i / 100 for i in range(20)] + [0.9, 0.8, 0.185, 0.1, 0.05]
    # one clean entry above 0.185 is 1/20 = 5% false rejections: allowed; 0.1 would add more
    assert pick_threshold(y, s, max_fpr=0.05) == 0.185
    assert pick_threshold(y, s, max_fpr=0.0) == 0.8


def test_pick_threshold_without_clean_entries_takes_lowest():
    assert pick_threshold([1, 1], [0.3, 0.7]) == 0.3


def test_model_threshold_file(tmp_path):
    assert model_threshold(str(tmp_path)) == 0.5
    (tmp_path / "threshold.json").write_text(json.dumps({"threshold": 0.12}))
    assert model_threshold(str(tmp_path)) == 0.12


def test_check_uses_classifier_threshold():
    def clf(text: str) -> float:
        return 0.2
    assert MemshieldCheck(classifier=clf).threshold == 0.5
    clf.threshold = 0.1  # type: ignore[attr-defined]
    assert MemshieldCheck(classifier=clf).threshold == 0.1
    assert MemshieldCheck(classifier=clf, threshold=0.3).threshold == 0.3


def test_pick_threshold_rejects_nan_scores():
    import pytest
    with pytest.raises(ValueError, match="NaN"):
        pick_threshold([0, 1], [float("nan"), 0.9])


def test_threshold_floor_and_seed_selection_on_calibration_data():
    from memledger.guards.train.train_memshield import select_seed

    y, s = [0, 0, 0, 1, 1], [0.001, 0.002, 0.003, 0.0025, 0.0028]  # badly calibrated: everything near 0
    assert pick_threshold(y, s, max_fpr=0.4) < 0.5 and pick_threshold(y, s, max_fpr=0.4, floor=0.5) == 0.5
    runs = [{"seed": 13, "calibration": {"recall": 0.90, "false_rejection": 0.04, "f1": 0.8}},
            {"seed": 14, "calibration": {"recall": 0.95, "false_rejection": 0.05, "f1": 0.7}},
            {"seed": 15, "calibration": {"recall": 0.95, "false_rejection": 0.02, "f1": 0.6}}]
    assert select_seed(runs)["seed"] == 15  # recall first, then fewer false rejections
