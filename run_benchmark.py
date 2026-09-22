#!/usr/bin/env python3
"""Benchmark FASTQ compression tools and write JSON results per (tool, sample)."""
from __future__ import annotations

import argparse
import json
import logging
import multiprocessing
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from benchmarks.verify import VerificationResult, verify
from tools import get_all_compressor_classes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

_FASTQ_SUFFIXES = (".fastq.gz", ".fastq", ".fq.gz", ".fq")


def _sample_name(path: Path) -> str:
    name = path.name
    for suf in _FASTQ_SUFFIXES:
        name = name.removesuffix(suf)
    return name


def _total_size(*paths: Path | None) -> int:
    return sum(p.stat().st_size for p in paths if p is not None and p.exists())


def _write_result(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2, default=str)
    log.info("Result written → %s", path)


def run_benchmark(
    fwd_reads: Path,
    rev_reads: Path | None,
    output_dir: Path,
    tool_names: list[str] | None = None,
    num_threads: int = multiprocessing.cpu_count(),
) -> None:
    sample = _sample_name(fwd_reads)
    original_size = _total_size(fwd_reads, rev_reads)

    compressor_classes = get_all_compressor_classes()
    if tool_names:
        compressor_classes = [c for c in compressor_classes if c.name in tool_names]

    for CompressorClass in compressor_classes:
        compressor = CompressorClass()
        log.info("[%s] starting on %s", compressor.name, sample)
        result_path = output_dir / f"{compressor.name}__{sample}.json"

        if not compressor.is_available():
            log.warning("[%s] not found in environment — skipping", compressor.name)
            continue

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            prefix = tmp / sample

            try:
                compress_result = compressor.compress(
                    fwd_reads=fwd_reads,
                    rev_reads=rev_reads,
                    output_prefix=prefix,
                    num_threads=num_threads,
                )
            except Exception as exc:
                log.error("[%s] compression failed: %s", compressor.name, exc)
                _write_result(result_path, {
                    "tool": compressor.name, "sample": sample,
                    "status": "compression_failed", "error": str(exc),
                })
                continue

            compressed_size = _total_size(*compress_result.output_files)
            log.info(
                "[%s] compressed %.2f GB → %.2f GB in %.1fs",
                compressor.name, original_size / 1e9, compressed_size / 1e9,
                compress_result.elapsed_seconds,
            )

            try:
                decompress_result = compressor.decompress(
                    archive=compress_result.output_files,
                    output_prefix=tmp / f"{sample}_decomp",
                    num_threads=num_threads,
                )
            except Exception as exc:
                log.error("[%s] decompression failed: %s", compressor.name, exc)
                _write_result(result_path, {
                    "tool": compressor.name, "sample": sample,
                    "status": "decompression_failed", "error": str(exc),
                    "original_size_bytes": original_size,
                    "compressed_size_bytes": compressed_size,
                    "compression_time_seconds": compress_result.elapsed_seconds,
                })
                continue

            decomp_fwd = decompress_result.output_files[0] if decompress_result.output_files else None
            decomp_rev = decompress_result.output_files[1] if len(decompress_result.output_files) > 1 else None

            ver_result, ver_msg = verify(
                fidelity=CompressorClass.fidelity,
                original_fwd=fwd_reads,
                original_rev=rev_reads,
                decompressed_fwd=decomp_fwd,
                decompressed_rev=decomp_rev,
            )
            if ver_result == VerificationResult.FAIL:
                log.warning("[%s] fidelity check FAILED: %s", compressor.name, ver_msg)
            else:
                log.info("[%s] fidelity check: %s", compressor.name, ver_result)

            ratio = original_size / compressed_size if compressed_size else None
            _write_result(result_path, {
                "tool": compressor.name,
                "sample": sample,
                "status": "success",
                "fidelity_claimed": CompressorClass.fidelity,
                "fidelity_verified": ver_result,
                "fidelity_verification_message": ver_msg or None,
                "original_size_bytes": original_size,
                "compressed_size_bytes": compressed_size,
                "compression_ratio": round(ratio, 3) if ratio else None,
                "compression_time_seconds": round(compress_result.elapsed_seconds, 1),
                "decompression_time_seconds": round(decompress_result.elapsed_seconds, 1),
                "tool_version": compress_result.tool_version or None,
                "num_threads": num_threads,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-1", "--fwd-reads", type=Path, required=True,
                        help="Forward reads FASTQ (or FASTQ.gz)")
    parser.add_argument("-2", "--rev-reads", type=Path,
                        help="Reverse reads FASTQ (optional)")
    parser.add_argument("--tools", nargs="+",
                        help="Tools to run (default: all available)")
    parser.add_argument("--output-dir", type=Path, default=Path("benchmarks/results"),
                        help="Directory for JSON result files")
    parser.add_argument("-j", "--num-threads", type=int, default=multiprocessing.cpu_count())
    args = parser.parse_args()

    run_benchmark(
        fwd_reads=args.fwd_reads,
        rev_reads=args.rev_reads,
        output_dir=args.output_dir,
        tool_names=args.tools,
        num_threads=args.num_threads,
    )


if __name__ == "__main__":
    main()
