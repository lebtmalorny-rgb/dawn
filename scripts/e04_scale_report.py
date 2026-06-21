#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_SRC = _REPO_ROOT / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

from cloud_ui.inventory.scale_report import (  # noqa: E402
    DEFAULT_OUTPUT_PATH,
    ScaleProfile,
    generate_scale_report,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate E04 synthetic scale evidence.")
    parser.add_argument("--instances", type=int, default=10_000)
    parser.add_argument("--hypervisors", type=int, default=1_000)
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--max-page-size", type=int, default=200)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--sync-chunk-size", type=int, default=500)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Markdown report path, relative to the current working directory by default.",
    )
    args = parser.parse_args(argv)

    report = generate_scale_report(
        ScaleProfile(
            instance_count=args.instances,
            hypervisor_count=args.hypervisors,
            page_size=args.page_size,
            max_page_size=args.max_page_size,
            sample_iterations=args.iterations,
            sync_chunk_size=args.sync_chunk_size,
        ),
        output_path=args.output,
    )
    print(f"Wrote {args.output}")
    print(f"status={report.sync.status} success={report.success}")
    for scenario in report.scenarios:
        print(
            f"{scenario.name}: p95={scenario.p95_seconds:.6f}s "
            f"sql_max={scenario.query_count_max}"
        )
    return 0 if report.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
