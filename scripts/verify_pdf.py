#!/usr/bin/env python3
"""Render every PDF page and write a deterministic audit plus contact sheet."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--dpi", default=96, type=int)
    parser.add_argument("--columns", default=4, type=int)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat near-blank pages as blocking failures instead of warnings.",
    )
    return parser.parse_args()


def require_command(name: str) -> str:
    """Return a required executable path or fail with a useful message."""
    command = shutil.which(name)
    if not command:
        raise RuntimeError(f"Required command was not found: {name}")
    return command


def run_text(command: list[str]) -> str:
    """Run a command and return decoded standard output."""
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout


def parse_pdfinfo(raw_info: str) -> dict[str, str]:
    """Convert pdfinfo output into a simple key/value mapping."""
    parsed: dict[str, str] = {}
    for line in raw_info.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", maxsplit=1)
        parsed[key.strip()] = value.strip()
    return parsed


def page_sort_key(path: Path) -> int:
    """Sort rendered page files numerically instead of lexicographically."""
    match = re.search(r"-(\d+)\.png$", path.name)
    return int(match.group(1)) if match else 0


def ink_ratio(image: Image.Image) -> float:
    """Estimate the share of pixels that differ meaningfully from white."""
    rgb = image.convert("RGB")
    white = Image.new("RGB", rgb.size, "white")
    difference = ImageChops.difference(rgb, white).convert("L")
    histogram = difference.histogram()
    ink_pixels = sum(histogram[12:])
    return ink_pixels / max(1, rgb.width * rgb.height)


def render_pages(pdf: Path, output_dir: Path, dpi: int) -> list[Path]:
    """Render all PDF pages to PNG files, replacing any previous render."""
    page_dir = output_dir / "pages"
    if page_dir.exists():
        shutil.rmtree(page_dir)
    page_dir.mkdir(parents=True)
    prefix = page_dir / "page"
    subprocess.run(
        [require_command("pdftoppm"), "-png", "-r", str(dpi), str(pdf), str(prefix)],
        check=True,
    )
    return sorted(page_dir.glob("page-*.png"), key=page_sort_key)


def build_contact_sheet(pages: list[Path], output: Path, columns: int) -> None:
    """Build a labeled contact sheet from rendered pages."""
    if not pages:
        raise RuntimeError("No pages were rendered")
    thumbs: list[Image.Image] = []
    for page in pages:
        image = Image.open(page).convert("RGB")
        image.thumbnail((360, 510))
        thumbs.append(image.copy())

    cell_width = max(image.width for image in thumbs) + 24
    cell_height = max(image.height for image in thumbs) + 48
    rows = (len(thumbs) + columns - 1) // columns
    sheet = Image.new("RGB", (cell_width * columns, cell_height * rows), "#dbe3ea")
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(thumbs):
        x_pos = (index % columns) * cell_width + (cell_width - image.width) // 2
        y_pos = (index // columns) * cell_height + 28
        sheet.paste(image, (x_pos, y_pos))
        draw.text((x_pos, y_pos - 20), f"Page {index + 1}", fill="#172033")
    sheet.save(output)


def evaluate_result(
    reported_pages: int,
    rendered_pages: int,
    text: str,
    near_blank_pages: list[int],
    strict: bool,
) -> tuple[list[str], list[str]]:
    """Return blocking issues and non-blocking warnings for a finished audit."""
    blocking: list[str] = []
    warnings: list[str] = []

    if reported_pages != rendered_pages:
        blocking.append(
            f"page count mismatch: pdfinfo reports {reported_pages}, rendered {rendered_pages}",
        )

    replacement_characters = text.count("\ufffd")
    if replacement_characters:
        blocking.append(f"extracted text contains {replacement_characters} replacement characters")

    if near_blank_pages:
        message = f"near-blank pages: {', '.join(str(page) for page in near_blank_pages)}"
        if strict:
            blocking.append(message)
        else:
            warnings.append(message)

    return blocking, warnings


def audit(pdf: Path, output_dir: Path, dpi: int, columns: int, strict: bool) -> dict[str, Any]:
    """Run structural, text, and rendered-page checks."""
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    output_dir.mkdir(parents=True, exist_ok=True)
    info = parse_pdfinfo(run_text([require_command("pdfinfo"), str(pdf)]))

    with tempfile.NamedTemporaryFile(suffix=".txt") as temp_text:
        subprocess.run([require_command("pdftotext"), str(pdf), temp_text.name], check=True)
        text = Path(temp_text.name).read_text(encoding="utf-8", errors="replace")

    pages = render_pages(pdf, output_dir, dpi)
    page_checks: list[dict[str, Any]] = []
    for index, page in enumerate(pages, start=1):
        with Image.open(page) as image:
            ratio = round(ink_ratio(image), 6)
            page_checks.append(
                {
                    "page": index,
                    "width_px": image.width,
                    "height_px": image.height,
                    "ink_ratio": ratio,
                    "near_blank": ratio < 0.002,
                }
            )

    contact_sheet = output_dir / "contact-sheet.png"
    build_contact_sheet(pages, contact_sheet, columns)
    reported_pages = int(info.get("Pages", "0") or "0")
    near_blank_pages = [item["page"] for item in page_checks if item["near_blank"]]
    blocking, warnings = evaluate_result(
        reported_pages,
        len(pages),
        text,
        near_blank_pages,
        strict,
    )
    result: dict[str, Any] = {
        "pdf": str(pdf.resolve()),
        "pdfinfo": info,
        "reported_page_count": reported_pages,
        "rendered_page_count": len(pages),
        "page_count_matches": reported_pages == len(pages),
        "text_characters": len(text),
        "replacement_characters": text.count("\ufffd"),
        "near_blank_pages": near_blank_pages,
        "blocking_issues": blocking,
        "warnings": warnings,
        "ok": not blocking,
        "strict": strict,
        "pages": page_checks,
        "contact_sheet": str(contact_sheet.resolve()),
    }
    audit_file = output_dir / "pdf-audit.json"
    audit_file.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    """Run the PDF audit and print its summary."""
    args = parse_args()
    if args.dpi <= 0 or args.columns <= 0:
        raise SystemExit("--dpi and --columns must be positive")
    result = audit(args.pdf, args.output_dir, args.dpi, args.columns, args.strict)
    summary = {
        "ok": result["ok"],
        "blocking_issues": result["blocking_issues"],
        "warnings": result["warnings"],
        "page_count_matches": result["page_count_matches"],
        "rendered_page_count": result["rendered_page_count"],
        "replacement_characters": result["replacement_characters"],
        "near_blank_pages": result["near_blank_pages"],
        "contact_sheet": result["contact_sheet"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
