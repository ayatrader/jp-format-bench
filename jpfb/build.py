"""Generate the benchmark file deterministically (same seed -> same file).

python -m jpfb.build > data/jp_format_bench_v1.jsonl
"""
from __future__ import annotations

import datetime as _dt
import json
import random
import sys

from . import rules

VERSION = "1.0"
SEED = 20261028
WD_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _rand_date(rng: random.Random, lo: _dt.date, hi: _dt.date) -> _dt.date:
    return lo + _dt.timedelta(days=rng.randrange((hi - lo).days + 1))


def _items() -> list[dict]:
    rng = random.Random(SEED)
    out: list[dict] = []

    def add(cat, q_en, q_ja, answer, fmt):
        out.append({"id": f"{cat}-{sum(1 for o in out if o['category'] == cat) + 1:03d}",
                    "category": cat, "question_en": q_en, "question_ja": q_ja,
                    "answer": answer, "answer_format": fmt})

    # 1. Western -> wareki. Include every era boundary on purpose.
    edge = [_dt.date(1989, 1, 7), _dt.date(1989, 1, 8), _dt.date(2019, 4, 30), _dt.date(2019, 5, 1),
            _dt.date(2019, 12, 31), _dt.date(2020, 1, 1), _dt.date(1926, 12, 25), _dt.date(1927, 1, 1)]
    dates = edge + [_rand_date(rng, _dt.date(1927, 1, 1), _dt.date(2030, 12, 31)) for _ in range(17)]
    for d in dates:
        add("to_wareki", f"Write {d.isoformat()} as a Japanese era (wareki) date.",
            f"{d.year}年{d.month}月{d.day}日を和暦で書いてください。",
            rules.to_wareki(d), "e.g. 令和元年5月1日 (use 元 for year 1, no leading zeros)")

    # 2. Wareki -> western, including dates that do not exist.
    for _ in range(18):
        d = _rand_date(rng, _dt.date(1927, 1, 1), _dt.date(2030, 12, 31))
        w = rules.to_wareki(d)
        add("from_wareki", f"Convert the Japanese date {w} to YYYY-MM-DD.",
            f"{w}を西暦(YYYY-MM-DD)にしてください。", d.isoformat(),
            "YYYY-MM-DD, or INVALID if the date does not exist")
    for w in ["平成31年5月1日", "昭和64年1月8日", "令和元年4月30日", "平成元年1月7日"]:
        add("from_wareki", f"Convert the Japanese date {w} to YYYY-MM-DD.",
            f"{w}を西暦(YYYY-MM-DD)にしてください。", "INVALID",
            "YYYY-MM-DD, or INVALID if the date does not exist")
    for w, iso in [("昭和64年1月7日", "1989-01-07"), ("平成31年4月30日", "2019-04-30"), ("令和元年5月1日", "2019-05-01")]:
        add("from_wareki", f"Convert the Japanese date {w} to YYYY-MM-DD.",
            f"{w}を西暦(YYYY-MM-DD)にしてください。", iso,
            "YYYY-MM-DD, or INVALID if the date does not exist")

    # 3. Holidays (2025-2026 only: officially announced years).
    hol = {**rules.national_holidays(2025), **rules.national_holidays(2026)}
    picks = sorted(hol)
    rng.shuffle(picks)
    forced = [_dt.date(2026, 9, 22), _dt.date(2026, 5, 6), _dt.date(2025, 11, 24)]  # 国民の休日・振替休日
    chosen = forced + [d for d in picks if d not in forced][:12]
    non = []
    while len(non) < 10:
        d = _rand_date(rng, _dt.date(2025, 1, 1), _dt.date(2026, 12, 31))
        if d not in hol and d not in non:
            non.append(d)
    for d in sorted(chosen + non):
        ans = hol.get(d, "NONE")
        add("holiday", f"Is {d.isoformat()} a national holiday in Japan (including substitute holidays)? Give its Japanese name.",
            f"{d.year}年{d.month}月{d.day}日は日本の祝日・休日(振替休日・国民の休日を含む)ですか。名前を答えてください。",
            ans, "the Japanese name (e.g. 振替休日), or NONE")

    # 4. Business days (Mon-Fri, excluding national holidays).
    for _ in range(20):
        d = _rand_date(rng, _dt.date(2025, 1, 1), _dt.date(2026, 11, 30))
        n = rng.choice([1, 2, 3, 5, 10])
        add("business_days",
            f"Starting from {d.isoformat()} ({WD_EN[d.weekday()]}), what date is {n} Japanese business day(s) later? "
            "Business days are Monday-Friday excluding Japanese national holidays; the start day is not counted.",
            f"{d.year}年{d.month}月{d.day}日から{n}営業日後は何日ですか。営業日は月〜金で日本の祝日・休日を除きます。起点の日は数えません。",
            rules.add_business_days(d, n).isoformat(), "YYYY-MM-DD")

    # 5. Corporate Number / invoice registration number check digit.
    for i in range(20):
        base = "".join(str(rng.randrange(10)) for _ in range(12))
        good = f"{rules.corporate_check_digit(base)}{base}"
        if i % 2:
            wrong = (int(good[0]) + rng.randrange(1, 9)) % 10
            num = f"{wrong}{base}"
        else:
            num = good
        if i % 4 == 0:
            num = "T" + num
        add("corporate_number",
            f"Is {num} a valid Japanese Corporate Number (or qualified invoice issuer number) by its check digit?",
            f"{num} は法人番号(適格請求書発行事業者の登録番号)としてチェックデジットが正しいですか。",
            "VALID" if rules.is_valid_corporate_number(num) else "INVALID", "VALID or INVALID")

    # 6. Width normalization.
    for s in ["ＡＢＣ１２３", "ｶﾌﾞｼｷｶﾞｲｼｬ", "東京都千代田区１－２－３", "ﾃﾞｰﾀ　ﾏﾈｰｼﾞｬｰ", "ＴＥＬ：０３－１２３４－５６７８",
              "（株）ﾅｸｻｽ", "ﾊﾟｰｸﾊｲﾂ１０１号室", "Ｅメール：ｉｎｆｏ＠ｅｘａｍｐｌｅ．ｊｐ", "ｳﾞｧｲｵﾘﾝ", "合計￥１，２８０"]:
        add("width",
            f"Normalize this text with Unicode NFKC (full-width ASCII to half-width, half-width katakana to full-width): {s}",
            f"次の文字列をUnicode NFKCで正規化してください(全角英数→半角、半角カナ→全角): {s}",
            rules.normalize_width(s), "the normalized string only")
    return out


def main() -> int:
    for item in _items():
        item["version"] = VERSION
        sys.stdout.write(json.dumps(item, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
