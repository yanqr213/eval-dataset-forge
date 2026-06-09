from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import (
    DatasetError,
    build_dataset,
    create_dataset_card,
    dataset_stats,
    read_records,
    render_dataset_card,
    split_records,
    validate_records,
    write_records,
)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except DatasetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eval-dataset-forge",
        description="Build validated LLM evaluation datasets from JSON, JSONL, or CSV templates.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate an input dataset template.")
    add_input_args(validate)
    validate.set_defaults(func=cmd_validate)

    build = subparsers.add_parser("build", help="Validate, dedupe, optionally shuffle, and export a dataset.")
    add_input_args(build)
    build.add_argument("-o", "--output", required=True, type=Path, help="Output path (.json, .jsonl, .csv).")
    build.add_argument("--output-format", choices=("json", "jsonl", "csv"), help="Override output format.")
    build.add_argument("--dedupe-key", choices=("id", "content"), default="id", help="Deduplication strategy.")
    build.add_argument("--shuffle", action="store_true", help="Shuffle records with a stable seed.")
    build.add_argument("--seed", type=int, default=42, help="Stable random seed for shuffle.")
    build.add_argument("--strict", action="store_true", help="Fail if any invalid rows are skipped.")
    build.set_defaults(func=cmd_build)

    split = subparsers.add_parser("split", help="Build and split a dataset into train/validation/test files.")
    add_input_args(split)
    split.add_argument("-o", "--output-dir", required=True, type=Path, help="Directory for split files.")
    split.add_argument("--format", choices=("json", "jsonl", "csv"), default="jsonl", help="Split output format.")
    split.add_argument("--train", type=float, default=0.8, help="Train split ratio.")
    split.add_argument("--validation", type=float, default=0.1, help="Validation split ratio.")
    split.add_argument("--test", type=float, default=0.1, help="Test split ratio.")
    split.add_argument("--dedupe-key", choices=("id", "content"), default="id", help="Deduplication strategy.")
    split.add_argument("--seed", type=int, default=42, help="Stable random seed for split.")
    split.add_argument("--strict", action="store_true", help="Fail if any invalid rows are skipped.")
    split.set_defaults(func=cmd_split)

    stats = subparsers.add_parser("stats", help="Print dataset statistics as JSON.")
    add_input_args(stats)
    stats.set_defaults(func=cmd_stats)

    card = subparsers.add_parser("card", help="Generate a reviewable dataset card or JSON manifest.")
    add_input_args(card)
    card.add_argument("--format", choices=("markdown", "json"), default="markdown", help="Dataset card output format.")
    card.add_argument("--output", type=Path, help="Write the dataset card to this path instead of stdout.")
    card.add_argument("--name", default="", help="Human-readable dataset name.")
    card.add_argument("--purpose", default="", help="Dataset purpose or eval workflow.")
    card.add_argument("--owner", default="", help="Owning team or reviewer.")
    card.add_argument("--license", default="", help="Dataset license or sharing policy.")
    card.add_argument("--dedupe-key", choices=("id", "content"), default="id", help="Deduplication strategy for manifest hash.")
    card.add_argument("--check", action="store_true", help="Exit 1 when the generated card contains warnings.")
    card.set_defaults(func=cmd_card)
    return parser


def add_input_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("input", type=Path, help="Input path (.json, .jsonl, .csv).")
    parser.add_argument("--input-format", choices=("json", "jsonl", "csv"), help="Override input format.")


def cmd_validate(args: argparse.Namespace) -> int:
    records = read_records(args.input, args.input_format)
    valid, errors = validate_records(records)
    for error in errors:
        print(error, file=sys.stderr)
    summary = {"valid": len(valid), "invalid": len(errors)}
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 1 if errors else 0


def cmd_build(args: argparse.Namespace) -> int:
    records = read_records(args.input, args.input_format)
    built, report, errors = build_dataset(
        records,
        dedupe_key=args.dedupe_key,
        shuffle=args.shuffle,
        seed=args.seed,
    )
    if args.strict and errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    write_records(built, args.output, args.output_format)
    print(json.dumps(report.__dict__, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    records = read_records(args.input, args.input_format)
    built, report, errors = build_dataset(records, dedupe_key=args.dedupe_key)
    if args.strict and errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    splits = split_records(
        built,
        train_ratio=args.train,
        validation_ratio=args.validation,
        test_ratio=args.test,
        seed=args.seed,
    )
    for name, split in splits.items():
        write_records(split, args.output_dir / f"{name}.{args.format}", args.format)
    payload = report.__dict__ | {f"{name}_count": len(split) for name, split in splits.items()}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    records = read_records(args.input, args.input_format)
    print(json.dumps(dataset_stats(records), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def cmd_card(args: argparse.Namespace) -> int:
    records = read_records(args.input, args.input_format)
    card = create_dataset_card(
        records,
        dataset_name=args.name,
        source_path=str(args.input),
        purpose=args.purpose,
        owner=args.owner,
        license_name=args.license,
        dedupe_key=args.dedupe_key,
    )
    rendered = render_dataset_card(card, args.format)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if args.check and card["warnings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
