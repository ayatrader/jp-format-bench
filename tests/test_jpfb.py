import datetime as dt
import io
import json
import pathlib
import sys
import unittest
from contextlib import redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jpfb import build, rules, score  # noqa: E402

D = dt.date

# Officially announced lists (Cabinet Office). Written by hand, independent of rules.py.
OFFICIAL_2025 = {
    D(2025, 1, 1): "元日", D(2025, 1, 13): "成人の日", D(2025, 2, 11): "建国記念の日",
    D(2025, 2, 23): "天皇誕生日", D(2025, 2, 24): "振替休日", D(2025, 3, 20): "春分の日",
    D(2025, 4, 29): "昭和の日", D(2025, 5, 3): "憲法記念日", D(2025, 5, 4): "みどりの日",
    D(2025, 5, 5): "こどもの日", D(2025, 5, 6): "振替休日", D(2025, 7, 21): "海の日",
    D(2025, 8, 11): "山の日", D(2025, 9, 15): "敬老の日", D(2025, 9, 23): "秋分の日",
    D(2025, 10, 13): "スポーツの日", D(2025, 11, 3): "文化の日", D(2025, 11, 23): "勤労感謝の日",
    D(2025, 11, 24): "振替休日",
}
OFFICIAL_2026 = {
    D(2026, 1, 1): "元日", D(2026, 1, 12): "成人の日", D(2026, 2, 11): "建国記念の日",
    D(2026, 2, 23): "天皇誕生日", D(2026, 3, 20): "春分の日", D(2026, 4, 29): "昭和の日",
    D(2026, 5, 3): "憲法記念日", D(2026, 5, 4): "みどりの日", D(2026, 5, 5): "こどもの日",
    D(2026, 5, 6): "振替休日", D(2026, 7, 20): "海の日", D(2026, 8, 11): "山の日",
    D(2026, 9, 21): "敬老の日", D(2026, 9, 22): "国民の休日", D(2026, 9, 23): "秋分の日",
    D(2026, 10, 12): "スポーツの日", D(2026, 11, 3): "文化の日", D(2026, 11, 23): "勤労感謝の日",
}


class TestRules(unittest.TestCase):
    def test_holidays_match_official(self):
        self.assertEqual(rules.national_holidays(2025), OFFICIAL_2025)
        self.assertEqual(rules.national_holidays(2026), OFFICIAL_2026)

    def test_holiday_years_limited(self):
        with self.assertRaises(ValueError):
            rules.national_holidays(2019)

    def test_era_boundaries(self):
        self.assertEqual(rules.to_wareki(D(1989, 1, 7)), "昭和64年1月7日")
        self.assertEqual(rules.to_wareki(D(1989, 1, 8)), "平成元年1月8日")
        self.assertEqual(rules.to_wareki(D(2019, 4, 30)), "平成31年4月30日")
        self.assertEqual(rules.to_wareki(D(2019, 5, 1)), "令和元年5月1日")
        self.assertEqual(rules.to_wareki(D(2026, 10, 28)), "令和8年10月28日")
        self.assertEqual(rules.from_wareki("令和", 8, 10, 28), D(2026, 10, 28))
        for args in [("平成", 31, 5, 1), ("昭和", 64, 1, 8), ("令和", 1, 4, 30)]:
            with self.assertRaises(ValueError):
                rules.from_wareki(*args)

    def test_business_days(self):
        # Fri 2026-09-18 -> Mon 21, Tue 22, Wed 23 are holidays -> Thu 24
        self.assertEqual(rules.add_business_days(D(2026, 9, 18), 1), D(2026, 9, 24))
        self.assertEqual(rules.add_business_days(D(2025, 5, 2), 1), D(2025, 5, 7))

    def test_corporate_number(self):
        # National Tax Agency's own Corporate Number
        self.assertTrue(rules.is_valid_corporate_number("7000012050002"))
        self.assertTrue(rules.is_valid_corporate_number("T7000012050002"))
        self.assertFalse(rules.is_valid_corporate_number("8000012050002"))
        self.assertFalse(rules.is_valid_corporate_number("700001205000"))

    def test_width(self):
        self.assertEqual(rules.normalize_width("ｶﾌﾞｼｷｶﾞｲｼｬ ＡＢＣ"), "カブシキガイシャ ABC")


class TestBench(unittest.TestCase):
    def setUp(self):
        self.items = build._items()

    def test_deterministic(self):
        self.assertEqual(self.items, build._items())

    def test_shipped_file_is_current(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            build.main()
        shipped = (ROOT / "data" / "jp_format_bench_v1.jsonl").read_text(encoding="utf-8")
        self.assertEqual(shipped, buf.getvalue())

    def test_shape(self):
        ids = [i["id"] for i in self.items]
        self.assertEqual(len(ids), len(set(ids)))
        cats = {i["category"] for i in self.items}
        self.assertEqual(cats, {"to_wareki", "from_wareki", "holiday", "business_days", "corporate_number", "width"})
        self.assertGreaterEqual(len(self.items), 120)

    def test_holiday_items_use_official_years_only(self):
        for i in self.items:
            if i["category"] in ("holiday",):
                self.assertTrue(i["question_en"].split()[1].startswith(("2025", "2026")))

    def test_score_perfect_and_partial(self):
        perfect = [{"id": i["id"], "answer": i["answer"]} for i in self.items]
        r = score.score(self.items, perfect)
        self.assertEqual(r["accuracy"], 1.0)
        r2 = score.score(self.items, perfect[:-10])
        self.assertEqual(r2["correct"], len(self.items) - 10)
        self.assertEqual(len(r2["wrong"]), 10)

    def test_score_tolerates_case_and_quotes(self):
        item = [{"id": "x", "category": "corporate_number", "answer": "VALID"}]
        self.assertEqual(score.score(item, [{"id": "x", "answer": " valid "}])["correct"], 1)
        self.assertEqual(score.score(item, [{"id": "x", "answer": "INVALID"}])["correct"], 0)


if __name__ == "__main__":
    unittest.main()
