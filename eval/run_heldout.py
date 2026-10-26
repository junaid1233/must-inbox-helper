"""Measure the classifier on the held-out set.

The 40 messages were written by a separate agent that never saw the keyword rules,
so they aren't tailored to them. This is a measurement, not a pass/fail test: it
reports accuracy and, more importantly, how many messages were *confidently wrong*
(wrong category AND not flagged for human attention).

Run from the repo root:  backend/.venv/Scripts/python eval/run_heldout.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.batch import process_batch  # noqa: E402
from app.providers.mock import MockProvider  # noqa: E402

items = json.loads((ROOT / "eval" / "heldout_messages.json").read_text(encoding="utf-8"))
resp = process_batch([{"message_id": i["id"], "text": i["text"]} for i in items], MockProvider())
got = {r.message_id: r for r in resp.results}

correct = unclear_miss = flagged_wrong = confidently_wrong = 0
confusion: Counter = Counter()
for item in items:
    r = got[item["id"]]
    ok = r.intent.value == item["intent"]
    correct += ok
    if ok:
        mark = "ok   "
    elif r.intent.value == "other_or_unclear":
        mark, unclear_miss = "MISS ", unclear_miss + 1
    elif r.needs_human_attention:
        mark, flagged_wrong = "WRONG", flagged_wrong + 1
    else:
        mark, confidently_wrong = "WRONG!", confidently_wrong + 1
    if not ok:
        confusion[(item["intent"], r.intent.value)] += 1
    print(f"{mark:<6} {item['id']} expected={item['intent']:<22} got={r.intent.value:<22} "
          f"{r.confidence:<6} attention={r.needs_human_attention}")

n = len(items)
print(f"\naccuracy: {correct}/{n} ({correct / n:.0%})")
print(f"missed -> other_or_unclear (safe, flagged): {unclear_miss}")
print(f"wrong category, flagged for attention: {flagged_wrong}")
print(f"wrong category, NOT flagged (confidently wrong): {confidently_wrong}")
print("most common confusions:", confusion.most_common(5))
