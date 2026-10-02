"""CN code suggestions from a free-text product description.

Two tiers, both deliberately simple:

1. If a model has been trained (``train_classifier``), a TF-IDF + logistic
   regression pipeline ranks the CN headings it has seen.
2. Otherwise a keyword heuristic covers the six CBAM headings of the demo data.
   Its scores are keyword-match fractions, not probabilities, and it returns
   nothing rather than guessing when no keyword matches.

Neither tier has been evaluated on a real labelled corpus; suggestions are meant
to be reviewed by a customs specialist, never filed as-is.
"""

import pickle
import re
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "models" / "cn_classifier.pkl"

# French and English keywords, so the demo works with either language.
KEYWORDS: dict[str, list[str]] = {
    "7208": ["acier", "steel", "laminé", "hot-rolled", "tôle", "plate", "sheet", "coil"],
    "7306": ["tube", "tuyau", "pipe", "soudé", "welded", "creux", "hollow"],
    "7606": ["aluminium", "aluminum", "alu", "plaque", "plate", "feuille", "sheet"],
    "2523": ["ciment", "cement", "portland", "clinker"],
    "3102": ["engrais", "fertiliser", "fertilizer", "azoté", "nitrogen", "urée", "urea"],
    "7213": ["barre", "bar", "rod", "fil machine", "wire rod"],
}


def train_classifier(
    descriptions: list[str], codes: list[str], model_path: Path | None = None
) -> dict:
    """Fit TF-IDF + logistic regression on (description, CN code) pairs and save it.

    Returns cross-validated accuracy (indicative only on small samples), sample and
    class counts, or {"error": ...} when there are fewer than five examples.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.pipeline import Pipeline

    if len(descriptions) < 5:
        return {"error": "At least 5 labelled examples are required"}

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
            ("clf", LogisticRegression(max_iter=500)),
        ]
    )
    scores = cross_val_score(pipeline, descriptions, codes, cv=min(3, len(descriptions) - 1))
    pipeline.fit(descriptions, codes)

    path = model_path or MODEL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump({"pipeline": pipeline}, f)

    return {
        "accuracy": round(float(scores.mean()), 4),
        "n_samples": len(descriptions),
        "n_classes": len(set(codes)),
    }


def classify(description: str, top_k: int = 3, model_path: Path | None = None) -> list[dict]:
    """Return up to ``top_k`` suggestions [{"code": str, "confidence": float}, ...]."""
    path = model_path or MODEL_PATH
    if not path.exists():
        return _keyword_classify(description, top_k)

    # The model file is produced locally by train_classifier; never load untrusted pickles.
    with open(path, "rb") as f:
        pipeline = pickle.load(f)["pipeline"]
    probs = pipeline.predict_proba([description])[0]
    ranked = sorted(zip(pipeline.classes_, probs, strict=True), key=lambda x: -x[1])
    return [{"code": str(code), "confidence": round(float(p), 4)} for code, p in ranked[:top_k]]


def _keyword_classify(description: str, top_k: int) -> list[dict]:
    """Rank headings by the fraction of their keywords found in the description.

    Keywords match at the start of a word, so "tubes" matches "tube" (and
    "laminée" matches "laminé") but "product" does not match "rod".
    """
    text = description.lower()
    scores = []
    for code, keywords in KEYWORDS.items():
        hits = sum(re.search(rf"\b{re.escape(kw)}", text) is not None for kw in keywords)
        if hits:
            scores.append({"code": code, "confidence": round(hits / len(keywords), 4)})
    scores.sort(key=lambda s: s["confidence"], reverse=True)
    return scores[:top_k]
