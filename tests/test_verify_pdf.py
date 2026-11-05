from __future__ import annotations

import sys
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from verify_pdf import evaluate_result, ink_ratio, page_sort_key, parse_pdfinfo


class VerifyPdfTests(unittest.TestCase):
    def test_parse_pdfinfo(self) -> None:
        parsed = parse_pdfinfo("Pages:           3\nPage size:       595 x 842 pts\n")
        self.assertEqual(parsed["Pages"], "3")
        self.assertEqual(parsed["Page size"], "595 x 842 pts")

    def test_page_sort_key_is_numeric(self) -> None:
        self.assertLess(page_sort_key(Path("page-2.png")), page_sort_key(Path("page-10.png")))
        self.assertEqual(page_sort_key(Path("page-01.png")), 1)

    def test_ink_ratio_white_is_zero(self) -> None:
        self.assertEqual(ink_ratio(Image.new("RGB", (10, 10), "white")), 0.0)

    def test_ink_ratio_black_is_one(self) -> None:
        self.assertEqual(ink_ratio(Image.new("RGB", (10, 10), "black")), 1.0)

    def test_page_count_mismatch_blocks(self) -> None:
        blocking, warnings = evaluate_result(2, 1, "text", [], strict=False)
        self.assertEqual(len(blocking), 1)
        self.assertIn("page count mismatch", blocking[0])
        self.assertEqual(warnings, [])

    def test_replacement_characters_block(self) -> None:
        blocking, _ = evaluate_result(1, 1, "ok\ufffd", [], strict=False)
        self.assertEqual(len(blocking), 1)
        self.assertIn("replacement characters", blocking[0])

    def test_near_blank_pages_warn_by_default(self) -> None:
        blocking, warnings = evaluate_result(1, 1, "text", [1], strict=False)
        self.assertEqual(blocking, [])
        self.assertEqual(warnings, ["near-blank pages: 1"])

    def test_near_blank_pages_block_in_strict_mode(self) -> None:
        blocking, warnings = evaluate_result(1, 1, "text", [1], strict=True)
        self.assertEqual(blocking, ["near-blank pages: 1"])
        self.assertEqual(warnings, [])

    def test_healthy_audit_has_no_findings(self) -> None:
        blocking, warnings = evaluate_result(3, 3, "text", [], strict=True)
        self.assertEqual(blocking, [])
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
