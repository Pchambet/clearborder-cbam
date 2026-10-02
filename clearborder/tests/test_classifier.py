"""Tests for CN code suggestions: keyword heuristic and trained model."""

from pathlib import Path

import pytest

from app import classifier
from app.classifier import _keyword_classify, classify, train_classifier


class TestKeywordClassify:
    """Heuristic used when no model has been trained."""

    @pytest.mark.parametrize(
        ("description", "expected"),
        [
            ("tôle acier laminée à chaud", "7208"),
            ("hot-rolled steel coil", "7208"),
            ("tube soudé en acier", "7306"),
            ("welded steel pipe", "7306"),
            ("ciment portland", "2523"),
            ("urea fertilizer", "3102"),
        ],
    )
    def test_top_suggestion(self, description, expected):
        assert _keyword_classify(description, top_k=3)[0]["code"] == expected

    def test_unknown_description_returns_nothing(self):
        assert _keyword_classify("xyz unknown product", top_k=3) == []

    def test_keywords_match_word_starts_only(self):
        # "rod" must not match inside "product"; "tubes" must match "tube"
        assert _keyword_classify("imported product", top_k=3) == []
        assert _keyword_classify("steel tubes", top_k=1)[0]["code"] == "7306"

    def test_top_k_respected(self):
        assert len(_keyword_classify("acier laminé plaque feuille tube", top_k=2)) == 2

    def test_scores_are_keyword_fractions(self):
        # 2 of the 4 cement keywords match
        assert _keyword_classify("portland cement", top_k=1)[0]["confidence"] == 0.5


class TestClassify:
    """Public entry point: model if present, heuristic otherwise."""

    def test_falls_back_to_keywords_without_model(self, tmp_path):
        result = classify("tôle acier", top_k=3, model_path=tmp_path / "missing.pkl")
        assert result == _keyword_classify("tôle acier", top_k=3)

    def test_default_path_is_isolated_in_tests(self):
        # conftest redirects MODEL_PATH so the test suite never writes into models/
        repo_model = Path(classifier.__file__).parent.parent / "models" / "cn_classifier.pkl"
        assert repo_model != classifier.MODEL_PATH


class TestTrainClassifier:
    """Training writes a model that classify() then uses."""

    def test_requires_minimum_samples(self, tmp_path):
        result = train_classifier(["a", "b"], ["7208", "7208"], model_path=tmp_path / "m.pkl")
        assert "error" in result
        assert not (tmp_path / "m.pkl").exists()

    def test_trained_model_recovers_training_labels(self, tmp_path):
        path = tmp_path / "m.pkl"
        descriptions = [
            "hot-rolled steel plate",
            "hot-rolled steel sheet",
            "hot-rolled steel coil",
            "welded steel tube",
            "welded steel pipe",
            "welded hollow section",
            "portland cement",
            "grey portland cement",
            "white portland cement",
        ]
        codes = ["7208"] * 3 + ["7306"] * 3 + ["2523"] * 3
        metrics = train_classifier(descriptions, codes, model_path=path)
        assert metrics["n_samples"] == 9
        assert metrics["n_classes"] == 3
        assert 0.0 <= metrics["accuracy"] <= 1.0

        suggestions = classify("portland cement in bags", top_k=3, model_path=path)
        assert suggestions[0]["code"] == "2523"
        assert len(suggestions) == 3
        assert sum(s["confidence"] for s in suggestions) == pytest.approx(1.0, abs=1e-3)
