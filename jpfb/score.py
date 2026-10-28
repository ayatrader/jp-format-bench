"""Score answers against the benchmark.

answers file: JSON Lines, one object per line: {"id": "holiday-001", "answer": "振替休日"}
python -m jpfb.score data/jp_format_bench_v1.jsonl answers.jsonl [--json]
"""
from __future__ import annotations

import argparse
import json
import unicodedata
from collections import defaultdict


def _norm(s) -> str:
    s = unicodedata.normalize("NFC", str(s)).strip()
    return s.strip("`\"'「」 ").upper() if s.isascii() else s.strip("`\"'「」 ")


def load_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def score(bench: list[dict], answers: list[dict]) -> dict:
    given = {a["id"]: a.get("answer", "") for a in answers}
    per = defaultdict(lambda: [0, 0])
    wrong = []
    for item in bench:
        cat = item["category"]
        per[cat][1] += 1
        exp = item["answer"]
        got = given.get(item["id"])
        # width answers are compared exactly (normalization is the task)
        ok = got is not None and ((got.strip() == exp) if cat == "width" else _norm(got) == _norm(exp))
        if ok:
            per[cat][0] += 1
        else:
            wrong.append({"id": item["id"], "expected": exp, "got": got})
    total_ok = sum(v[0] for v in per.values())
    total = sum(v[1] for v in per.values())
    return {"total": total, "correct": total_ok, "accuracy": round(total_ok / total, 4) if total else 0.0,
            "by_category": {k: {"correct": v[0], "total": v[1]} for k, v in sorted(per.items())},
            "wrong": wrong}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Score answers for JP Format Bench")
    p.add_argument("bench")
    p.add_argument("answers")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    r = score(load_jsonl(a.bench), load_jsonl(a.answers))
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"accuracy {r['accuracy']:.1%} ({r['correct']}/{r['total']})")
        for k, v in r["by_category"].items():
            print(f"  {k:18s} {v['correct']}/{v['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
