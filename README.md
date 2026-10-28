# JP Format Bench

**125 questions that check whether an AI gets Japanese dates, holidays, business days, Corporate Numbers and character width right.**

Every answer is computed by code in `jpfb/rules.py` (Python standard library only), so you can re-check any of them. No answer is written by hand or by an AI.

| Category | Items | What it checks |
|---|---|---|
| `to_wareki` | 25 | Western date → Japanese era (令和元年5月1日). Includes every era boundary |
| `from_wareki` | 25 | Japanese era → YYYY-MM-DD, including dates that do not exist (平成31年5月1日 → INVALID) |
| `holiday` | 25 | National holidays in 2025–2026, including 振替休日 and 国民の休日 (2026-09-22) |
| `business_days` | 20 | "N business days after X", skipping weekends and holidays |
| `corporate_number` | 20 | Check digit of the 13-digit Corporate Number / invoice number (T + 13 digits) |
| `width` | 10 | Unicode NFKC: full-width ASCII → half-width, half-width katakana → full-width |

## Run it

```bash
python -m jpfb.prompt data/jp_format_bench_v1.jsonl --lang en > prompt.txt   # paste into any AI, or send by API
# save the AI's reply as answers.jsonl  ({"id": "...", "answer": "..."} per line)
python -m jpfb.score data/jp_format_bench_v1.jsonl answers.jsonl
```

Output:

```
accuracy 87.2% (109/125)
  business_days      14/20
  ...
```

`--json` prints every wrong item with the expected answer.

## Results

No model results are published yet. We only publish numbers we measured ourselves, with the date, model name and settings. Send a pull request with your `answers.jsonl` and the exact model/version if you ran it.

## Scope and limits

- Eras: Showa, Heisei, Reiwa (from 1926-12-25)
- Holidays: the dataset uses 2025 and 2026 only (officially announced). The rules cover 2022–2030; tests compare 2025 and 2026 with the Cabinet Office lists
- Business days: Monday–Friday minus national holidays. Year-end company closures are not counted as holidays
- Corporate Number: check digit only. It does not tell you whether the company exists

Related work: [Can Language Models Handle a Non-Gregorian Calendar?](https://arxiv.org/abs/2509.04432) (wareki only). This bench adds holidays, business days, Corporate Numbers and width.

To make an agent pass these, give it a rule-based tool instead of asking it to guess. [nexus-ja-data](https://github.com/ayatrader/nexus-ja-data) is one such MCP server (MIT).

Python 3.9+, no dependencies, no network access. MIT license.

---

# JP Format Bench(日本語)

**AIが日本の和暦・祝日・営業日・法人番号・全角半角を正しく扱えるかを測る125問。**

答えはすべて `jpfb/rules.py`(標準ライブラリだけ)のコードで決めています。人やAIが手で書いた答えはありません。誰でも同じ答えを再現できます。

- 和暦: 昭和・平成・令和の境目(昭和64年1月7日/平成元年1月8日 など)と、存在しない日付(平成31年5月1日)
- 祝日: 2025〜2026年。振替休日と国民の休日(2026年9月22日)を含む。内閣府の公表一覧とテストで照合
- 営業日: 土日祝を除いてN営業日後
- 法人番号・インボイス登録番号: チェックデジット(国税庁の計算式)
- 全角半角: Unicode NFKC

使い方は上の「Run it」。各AIの結果は、自分で測った数字だけを日付・モデル名つきで載せます(まだありません)。

ライセンス: MIT
