#!/usr/bin/env python3
"""Generate README.md by combining the static template with benchmark results."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
TEMPLATE = Path(__file__).parent / "README_template.md"
RESULTS_DIR = ROOT / "benchmarks" / "results"
README = ROOT / "README.md"


def _load_results(results_dir: Path) -> list[dict]:
    return [
        json.loads(p.read_text())
        for p in sorted(results_dir.glob("*.json"))
    ]


def _fmt_bytes(n: int | None) -> str:
    if n is None:
        return "N/A"
    if n >= 1e9:
        return f"{n / 1e9:.1f} GB"
    if n >= 1e6:
        return f"{n / 1e6:.0f} MB"
    return f"{n / 1e3:.0f} KB"


def _fmt_seconds(s: float | None) -> str:
    if s is None:
        return "N/A"
    if s >= 3600:
        return f"{s / 3600:.1f}h"
    if s >= 60:
        return f"{s / 60:.0f}m"
    return f"{s:.0f}s"


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return ""
    col_widths = [
        max(len(h), max(len(r) for r in col))
        for h, col in zip(headers, zip(*rows))
    ]
    col_widths = [max(w, len(h)) for w, h in zip(col_widths, headers)]

    def fmt_row(cells):
        return "| " + " | ".join(c.ljust(w) for c, w in zip(cells, col_widths)) + " |"

    sep = "| " + " | ".join("-" * w for w in col_widths) + " |"
    return "\n".join([fmt_row(headers), sep] + [fmt_row(r) for r in rows])


def _tools_table() -> str:
    sys.path.insert(0, str(ROOT))
    from tools import get_all_compressor_classes

    headers = ["Tool", "Fidelity", "Conda Package", "License"]
    rows = []
    for cls in sorted(get_all_compressor_classes(), key=lambda c: c.name):
        pkg = ", ".join(f"`{d}`" for d in cls.conda_deps) if cls.conda_deps else "_source build_"
        rows.append([cls.name, cls.fidelity, pkg, cls.license_note or "—"])
    return _md_table(headers, rows)


def _results_section(results: list[dict]) -> str:
    if not results:
        return "_No results yet. Run `python run_benchmark.py` to generate._\n"

    samples = sorted({r["sample"] for r in results})
    sections: list[str] = []

    for sample in samples:
        sr = [r for r in results if r["sample"] == sample and r.get("status") == "success"]
        if not sr:
            continue
        orig = sr[0]["original_size_bytes"]
        sections.append(f"### {sample}\n\nOriginal size: **{_fmt_bytes(orig)}**\n")

        headers = ["Tool", "Fidelity", "Compressed", "Ratio", "Compress", "Decompress", "Verified"]
        rows = sorted(sr, key=lambda r: r.get("compression_ratio") or 0, reverse=True)
        table_rows = [
            [
                r["tool"],
                r.get("fidelity_claimed", ""),
                _fmt_bytes(r.get("compressed_size_bytes")),
                f"{r['compression_ratio']:.2f}×" if r.get("compression_ratio") else "N/A",
                _fmt_seconds(r.get("compression_time_seconds")),
                _fmt_seconds(r.get("decompression_time_seconds")),
                r.get("fidelity_verified", ""),
            ]
            for r in rows
        ]
        sections.append(_md_table(headers, table_rows))
        sections.append("")

    return "\n".join(sections)


def generate(
    results_dir: Path = RESULTS_DIR,
    template: Path = TEMPLATE,
    output: Path = README,
) -> None:
    results = _load_results(results_dir)
    text = template.read_text()
    text = text.replace("<!-- TOOLS_TABLE -->", _tools_table())
    text = text.replace("<!-- RESULTS_SECTION -->", _results_section(results))
    output.write_text(text)
    print(f"Wrote {output}")


if __name__ == "__main__":
    generate()
