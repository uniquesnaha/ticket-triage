"""Command-line triage: read a ticket CSV, write one JSON object per input row (JSON Lines).

Usage (from backend/):
    python -m app.cli ../data/project_1.csv                  # JSONL to stdout
    python -m app.cli ../data/project_1.csv -o results.jsonl
    python -m app.cli ../data/project_1.csv --format json    # single JSON array

Credentials come from the environment (GROQ_API_KEY, or a .env file); nothing is hard-coded.
Logs go to stderr so stdout stays machine-readable.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import sys
from collections import Counter
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.triage.csv_loader import CSVFormatError, decode_csv_bytes, parse_tickets_csv
from app.triage.pipeline import process_batch

EXIT_OK = 0
EXIT_INPUT_ERROR = 2


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Triage support tickets from a CSV (columns: ticket_id, text).",
    )
    parser.add_argument("csv_path", type=Path, help="Input CSV file")
    parser.add_argument("-o", "--output", type=Path, help="Output file (default: stdout)")
    parser.add_argument(
        "--format",
        choices=("jsonl", "json"),
        default="jsonl",
        help="jsonl = one JSON object per line (default); json = a single JSON array",
    )
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    if not settings.llm_configured:
        print(
            "warning: GROQ_API_KEY is not set; every ticket will fall back to manual review.",
            file=sys.stderr,
        )

    try:
        parsed = parse_tickets_csv(
            decode_csv_bytes(args.csv_path.read_bytes()),
            max_text_length=settings.max_ticket_length,
        )
    except OSError as exc:
        print(f"error: cannot read {args.csv_path}: {exc.strerror}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    except CSVFormatError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    results = await process_batch(
        [p.ticket for p in parsed],
        settings.model_name,
        input_warnings=[p.warnings for p in parsed],
    )

    records = [r.model_dump(mode="json") for r in results]
    if args.format == "jsonl":
        body = "".join(json.dumps(rec, ensure_ascii=False) + "\n" for rec in records)
    else:
        body = json.dumps(records, ensure_ascii=False, indent=2) + "\n"

    if args.output:
        args.output.write_text(body, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(body)

    review = sum(r.needs_human_review for r in results)
    fallbacks = sum(r.is_llm_fallback for r in results)
    by_priority = dict(Counter(r.priority.value for r in results))
    print(
        f"triaged {len(results)} tickets | needs_human_review={review} | "
        f"model_not_used={fallbacks} | by_priority={by_priority}",
        file=sys.stderr,
    )
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    configure_logging(stream=sys.stderr)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
