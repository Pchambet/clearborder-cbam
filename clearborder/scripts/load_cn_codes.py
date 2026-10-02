#!/usr/bin/env python3
"""Load the sample CN nomenclature (data/cn_codes_sample.json) into the database."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, init_db
from app.models import CNCode

SAMPLE = Path(__file__).parent.parent / "data" / "cn_codes_sample.json"


def load_cn_codes(path: Path = SAMPLE) -> int:
    """Insert codes that are not in the database yet; return how many were added."""
    init_db()
    codes = json.loads(path.read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        added = 0
        for item in codes:
            code = item["code"].replace(" ", "")
            if db.query(CNCode).filter(CNCode.code == code).first() is None:
                db.add(CNCode(code=code, description=item.get("description", ""), level=4))
                added += 1
        db.commit()
        print(f"Loaded {added} CN codes (total: {db.query(CNCode).count()})")
        return added
    finally:
        db.close()


if __name__ == "__main__":
    load_cn_codes()
