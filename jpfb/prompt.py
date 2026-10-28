"""Print the questions as one prompt you can paste into any AI chat, or as JSONL for API runs.

python -m jpfb.prompt data/jp_format_bench_v1.jsonl --lang en > prompt.txt
The AI should reply with JSON Lines: {"id": "...", "answer": "..."}
"""
from __future__ import annotations

import argparse
import json

from .score import load_jsonl

HEAD = {
    "en": "Answer every question. Reply ONLY with JSON Lines, one per question: {\"id\": \"<id>\", \"answer\": \"<answer>\"}. Follow the answer format exactly. Do not use tools or code.\n",
    "ja": "すべての質問に答えてください。返答は1問1行のJSON Linesだけ: {\"id\": \"<id>\", \"answer\": \"<答え>\"}。答えの形式どおりに書くこと。道具やコードは使わないこと。\n",
}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("bench")
    p.add_argument("--lang", choices=["en", "ja"], default="en")
    p.add_argument("--category")
    a = p.parse_args(argv)
    print(HEAD[a.lang])
    for i in load_jsonl(a.bench):
        if a.category and i["category"] != a.category:
            continue
        q = i["question_en"] if a.lang == "en" else i["question_ja"]
        print(json.dumps({"id": i["id"], "question": q, "answer_format": i["answer_format"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
