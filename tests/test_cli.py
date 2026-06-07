from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval_dataset_forge.cli import main  # noqa: E402


class CliTests(unittest.TestCase):
    def write_input(self, path: Path) -> Path:
        payload = [
            {"id": "one", "prompt": "A", "expected": "B", "tags": "qa,smoke"},
            {"id": "two", "prompt": "C", "expected": "D", "metadata": {"kind": "unit"}},
            {"id": "one", "prompt": "duplicate", "expected": "duplicate"},
            {"id": "", "prompt": "missing", "expected": "bad"},
        ]
        input_path = path / "input.json"
        input_path.write_text(json.dumps(payload), encoding="utf-8")
        return input_path

    def run_cli(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_validate_returns_nonzero_for_invalid_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, out, err = self.run_cli(["validate", str(self.write_input(Path(tmp)))])
            self.assertEqual(result, 1)
            self.assertIn('"invalid": 2', out)
            self.assertIn("duplicate id", err)

    def test_build_writes_jsonl_and_skips_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "out.jsonl"
            result, out, _ = self.run_cli(["build", str(self.write_input(tmp_path)), "-o", str(output), "--shuffle", "--seed", "3"])
            self.assertEqual(result, 0)
            self.assertTrue(output.exists())
            self.assertEqual(len(output.read_text(encoding="utf-8").splitlines()), 2)
            self.assertIn('"output_count": 2', out)

    def test_build_strict_returns_nonzero_for_invalid_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "out.jsonl"
            result, _, err = self.run_cli(["build", str(self.write_input(tmp_path)), "-o", str(output), "--strict"])
            self.assertEqual(result, 1)
            self.assertFalse(output.exists())
            self.assertIn("missing required", err)

    def test_split_writes_three_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output_dir = tmp_path / "splits"
            result, out, _ = self.run_cli(
                [
                    "split",
                    str(self.write_input(tmp_path)),
                    "-o",
                    str(output_dir),
                    "--train",
                    "0.5",
                    "--validation",
                    "0.25",
                    "--test",
                    "0.25",
                ]
            )
            self.assertEqual(result, 0)
            self.assertTrue((output_dir / "train.jsonl").exists())
            self.assertTrue((output_dir / "validation.jsonl").exists())
            self.assertTrue((output_dir / "test.jsonl").exists())
            self.assertIn('"test_count"', out)

    def test_stats_outputs_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, out, _ = self.run_cli(["stats", str(self.write_input(Path(tmp)))])
            self.assertEqual(result, 0)
            parsed = json.loads(out)
            self.assertEqual(parsed["records"], 4)
            self.assertEqual(parsed["duplicate_ids"], 1)


if __name__ == "__main__":
    unittest.main()
