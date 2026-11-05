#!/usr/bin/env python3
"""Build the deterministic dist/academic-paper-zh-pdf.skill package."""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "academic-paper-zh-pdf"
FILES = (
    "SKILL.md",
    "references/translation-quality.md",
    "scripts/build_pdf.mjs",
    "scripts/verify_pdf.py",
    "assets/paper.css",
)
DIRECTORIES = ("", "references", "scripts", "assets")
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def build(output: Path) -> bytes:
    """Write the archive and return its bytes."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for directory in DIRECTORIES:
            entry = f"{PACKAGE}/{directory}/" if directory else f"{PACKAGE}/"
            info = zipfile.ZipInfo(entry, FIXED_TIMESTAMP)
            info.create_system = 3
            info.external_attr = (0o40755 << 16) | 0x10
            archive.writestr(info, b"")
        for relative in FILES:
            info = zipfile.ZipInfo(f"{PACKAGE}/{relative}", FIXED_TIMESTAMP)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (ROOT / relative).read_bytes())
    return output.read_bytes()


def main() -> int:
    """Build the package, or check that the checked-in copy is current."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "academic-paper-zh-pdf.skill",
        help="Archive path (default: dist/academic-paper-zh-pdf.skill)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the checked-in archive differs from the current sources.",
    )
    args = parser.parse_args()

    if args.check:
        if not args.output.is_file():
            print(f"error: archive not found: {args.output}", file=sys.stderr)
            return 1
        with tempfile.TemporaryDirectory() as temp_dir:
            expected = build(Path(temp_dir) / "expected.skill")
        actual = args.output.read_bytes()
        if expected != actual:
            print(
                f"error: {args.output} is out of date; run python3 scripts/build_skill.py",
                file=sys.stderr,
            )
            return 1
        print(f"{args.output} is up to date")
        return 0

    data = build(args.output)
    print(f"{args.output} ({len(data)} bytes)")
    print(f"sha256 {hashlib.sha256(data).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
