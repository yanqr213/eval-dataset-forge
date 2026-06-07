from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval_dataset_forge.core import (  # noqa: E402
    DatasetError,
    build_dataset,
    dataset_stats,
    read_records,
    split_records,
    validate_records,
    write_records,
)


class CoreTests(unittest.TestCase):
    def sample_records(self):
        return [
            {
                "id": "a",
                "prompt": " Prompt A ",
                "expected": "Answer A",
                "metadata": {"category": "qa"},
                "tags": ["smoke", "qa", "qa"],
            },
            {
                "id": "b",
                "prompt": "Prompt B",
                "expected": "Answer B",
                "metadata": {"category": "qa"},
                "tags": "qa,short",
            },
            {
                "id": "a",
                "prompt": "Prompt A duplicate",
                "expected": "Answer A duplicate",
            },
        ]

    def test_validate_reports_duplicate_ids(self):
        valid, errors = validate_records(self.sample_records())
        self.assertEqual(len(valid), 2)
        self.assertEqual(len(errors), 1)
        self.assertIn("duplicate id 'a'", errors[0])

    def test_build_dedupes_and_normalizes_tags(self):
        built, report, errors = build_dataset(self.sample_records(), dedupe_key="id")
        self.assertEqual(errors, [])
        self.assertEqual(len(built), 2)
        self.assertEqual(built[0]["prompt"], "Prompt A")
        self.assertEqual(built[0]["tags"], ["qa", "smoke"])
        self.assertEqual(report.duplicate_count, 1)

    def test_stable_shuffle_seed(self):
        records = [{"id": str(i), "prompt": f"p{i}", "expected": f"e{i}"} for i in range(10)]
        first, _, _ = build_dataset(records, shuffle=True, seed=7)
        second, _, _ = build_dataset(records, shuffle=True, seed=7)
        self.assertEqual([item["id"] for item in first], [item["id"] for item in second])
        self.assertNotEqual([item["id"] for item in first], [item["id"] for item in records])

    def test_split_is_stable_and_complete(self):
        records = [{"id": str(i), "prompt": f"p{i}", "expected": f"e{i}"} for i in range(10)]
        splits = split_records(records, train_ratio=0.6, validation_ratio=0.2, test_ratio=0.2, seed=11)
        self.assertEqual({name: len(items) for name, items in splits.items()}, {"train": 6, "validation": 2, "test": 2})
        self.assertEqual(sum(len(items) for items in splits.values()), 10)

    def test_split_rejects_bad_ratios(self):
        with self.assertRaises(DatasetError):
            split_records([], train_ratio=0.7, validation_ratio=0.2, test_ratio=0.2)

    def test_jsonl_and_csv_round_trip(self):
        records, _, _ = build_dataset(self.sample_records(), dedupe_key="id")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            jsonl_path = tmp_path / "data.jsonl"
            csv_path = tmp_path / "data.csv"
            write_records(records, jsonl_path)
            write_records(records, csv_path)
            self.assertEqual(len(read_records(jsonl_path)), 2)
            self.assertEqual(read_records(csv_path)[1]["id"], "b")

    def test_stats_counts_tags_and_duplicates(self):
        stats = dataset_stats(self.sample_records())
        self.assertEqual(stats["records"], 3)
        self.assertEqual(stats["duplicate_ids"], 1)
        self.assertEqual(stats["tags"]["qa"], 2)


if __name__ == "__main__":
    unittest.main()
