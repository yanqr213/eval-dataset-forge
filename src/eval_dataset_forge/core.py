from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


REQUIRED_FIELDS = ("id", "prompt", "expected")
OPTIONAL_FIELDS = ("metadata", "tags")
SUPPORTED_FORMATS = {"json", "jsonl", "csv"}


class DatasetError(ValueError):
    """Raised when input data cannot be converted into a valid eval dataset."""


@dataclass(frozen=True)
class BuildReport:
    input_count: int
    output_count: int
    duplicate_count: int
    invalid_count: int


def detect_format(path: Path, explicit_format: str | None = None) -> str:
    if explicit_format:
        fmt = explicit_format.lower()
    else:
        suffix = path.suffix.lower().lstrip(".")
        fmt = "jsonl" if suffix == "ndjson" else suffix
    if fmt not in SUPPORTED_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_FORMATS))
        raise DatasetError(f"Unsupported format '{fmt}'. Use one of: {supported}.")
    return fmt


def read_records(path: Path, input_format: str | None = None) -> list[dict[str, Any]]:
    fmt = detect_format(path, input_format)
    if fmt == "json":
        return _read_json(path)
    if fmt == "jsonl":
        return _read_jsonl(path)
    return _read_csv(path)


def _read_json(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetError(f"{path}: invalid JSON at line {exc.lineno}: {exc.msg}") from exc

    if isinstance(raw, dict) and isinstance(raw.get("records"), list):
        raw = raw["records"]
    if not isinstance(raw, list):
        raise DatasetError(f"{path}: JSON input must be a list or an object with a 'records' list.")
    return _ensure_object_list(raw, path)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetError(f"{path}:{line_number}: invalid JSONL record: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise DatasetError(f"{path}:{line_number}: JSONL record must be an object.")
        records.append(value)
    return records


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise DatasetError(f"{path}: CSV input must include a header row.")
        return [dict(row) for row in reader]


def _ensure_object_list(values: list[Any], path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, value in enumerate(values, start=1):
        if not isinstance(value, dict):
            raise DatasetError(f"{path}: record {index} must be an object.")
        records.append(value)
    return records


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value is None:
            normalized[field] = ""
        elif isinstance(value, str):
            normalized[field] = value.strip()
        else:
            normalized[field] = json.dumps(value, ensure_ascii=False, sort_keys=True)

    metadata = record.get("metadata", {})
    if isinstance(metadata, str):
        metadata = _parse_jsonish(metadata, default={})
    if metadata in (None, ""):
        metadata = {}
    if not isinstance(metadata, dict):
        raise DatasetError("metadata must be an object when provided.")
    normalized["metadata"] = metadata

    tags = record.get("tags", [])
    if isinstance(tags, str):
        tags = _parse_tags(tags)
    if tags in (None, ""):
        tags = []
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise DatasetError("tags must be a list of strings when provided.")
    normalized["tags"] = sorted({tag.strip() for tag in tags if tag.strip()})

    return normalized


def _parse_jsonish(value: str, default: Any) -> Any:
    stripped = value.strip()
    if not stripped:
        return default
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return default


def _parse_tags(value: str) -> list[str]:
    parsed = _parse_jsonish(value, default=None)
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [part.strip() for part in value.split(",") if part.strip()]


def validate_records(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    valid: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_ids: set[str] = set()

    for index, record in enumerate(records, start=1):
        try:
            normalized = normalize_record(record)
        except DatasetError as exc:
            errors.append(f"record {index}: {exc}")
            continue

        missing = [field for field in REQUIRED_FIELDS if not normalized[field]]
        if missing:
            errors.append(f"record {index}: missing required field(s): {', '.join(missing)}")
            continue
        if normalized["id"] in seen_ids:
            errors.append(f"record {index}: duplicate id '{normalized['id']}'")
            continue
        seen_ids.add(normalized["id"])
        valid.append(normalized)

    return valid, errors


def dedupe_records(records: Iterable[dict[str, Any]], key: str = "id") -> tuple[list[dict[str, Any]], int]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicates = 0

    for record in records:
        normalized = normalize_record(record)
        if key == "content":
            dedupe_key = _content_hash(normalized)
        else:
            dedupe_key = str(normalized.get(key, ""))
        if dedupe_key in seen:
            duplicates += 1
            continue
        seen.add(dedupe_key)
        deduped.append(normalized)

    return deduped, duplicates


def _content_hash(record: dict[str, Any]) -> str:
    payload = {"prompt": record["prompt"], "expected": record["expected"]}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_dataset(
    records: Iterable[dict[str, Any]],
    *,
    dedupe_key: str = "id",
    shuffle: bool = False,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], BuildReport, list[str]]:
    input_records = list(records)
    normalized: list[dict[str, Any]] = []
    validation_errors: list[str] = []

    for index, record in enumerate(input_records, start=1):
        try:
            item = normalize_record(record)
        except DatasetError as exc:
            validation_errors.append(f"record {index}: {exc}")
            continue
        missing = [field for field in REQUIRED_FIELDS if not item[field]]
        if missing:
            validation_errors.append(f"record {index}: missing required field(s): {', '.join(missing)}")
            continue
        normalized.append(item)

    deduped, duplicate_count = dedupe_records(normalized, key=dedupe_key)
    if shuffle:
        rng = random.Random(seed)
        rng.shuffle(deduped)

    report = BuildReport(
        input_count=len(input_records),
        output_count=len(deduped),
        duplicate_count=duplicate_count,
        invalid_count=len(validation_errors),
    )
    return deduped, report, validation_errors


def split_records(
    records: list[dict[str, Any]],
    *,
    train_ratio: float,
    validation_ratio: float,
    test_ratio: float,
    seed: int = 42,
) -> dict[str, list[dict[str, Any]]]:
    ratios = (train_ratio, validation_ratio, test_ratio)
    if any(ratio < 0 for ratio in ratios):
        raise DatasetError("Split ratios must be non-negative.")
    if not 0.999 <= sum(ratios) <= 1.001:
        raise DatasetError("Split ratios must sum to 1.0.")

    shuffled = list(records)
    random.Random(seed).shuffle(shuffled)
    total = len(shuffled)
    train_end = int(total * train_ratio)
    validation_end = train_end + int(total * validation_ratio)
    return {
        "train": shuffled[:train_end],
        "validation": shuffled[train_end:validation_end],
        "test": shuffled[validation_end:],
    }


def write_records(records: Iterable[dict[str, Any]], path: Path, output_format: str | None = None) -> None:
    fmt = detect_format(path, output_format)
    path.parent.mkdir(parents=True, exist_ok=True)
    records_list = list(records)
    if fmt == "json":
        path.write_text(json.dumps(records_list, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif fmt == "jsonl":
        lines = [json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records_list]
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    else:
        _write_csv(records_list, path)


def _write_csv(records: list[dict[str, Any]], path: Path) -> None:
    fields = list(REQUIRED_FIELDS) + list(OPTIONAL_FIELDS)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["metadata"] = json.dumps(row.get("metadata", {}), ensure_ascii=False, sort_keys=True)
            row["tags"] = json.dumps(row.get("tags", []), ensure_ascii=False)
            writer.writerow({field: row.get(field, "") for field in fields})


def dataset_stats(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    normalized = [normalize_record(record) for record in records]
    tag_counts: Counter[str] = Counter()
    metadata_keys: Counter[str] = Counter()
    prompt_lengths: list[int] = []

    for record in normalized:
        tag_counts.update(record["tags"])
        metadata_keys.update(record["metadata"].keys())
        prompt_lengths.append(len(record["prompt"]))

    duplicate_ids = sum(count - 1 for count in Counter(record["id"] for record in normalized).values() if count > 1)
    return {
        "records": len(normalized),
        "duplicate_ids": duplicate_ids,
        "avg_prompt_chars": round(sum(prompt_lengths) / len(prompt_lengths), 2) if prompt_lengths else 0,
        "tags": dict(sorted(tag_counts.items())),
        "metadata_keys": dict(sorted(metadata_keys.items())),
    }
