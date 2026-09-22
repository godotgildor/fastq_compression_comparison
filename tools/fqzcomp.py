from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import ClassVar

from tools.base import BaseCompressor, CompressResult, DecompressResult, Fidelity


class FqzcompCompressor(BaseCompressor):
    """Quality-lossy: N bases have their quality score set to 0 on decompression."""

    name = "fqzcomp"
    fidelity = Fidelity.QUALITY_LOSSY
    conda_deps: ClassVar[list[str]] = ["fqzcomp>=4.6"]

    def _compress_one(self, reads: Path, output_file: Path) -> None:
        if reads.suffix == ".gz":
            src = subprocess.Popen(["zcat", str(reads)], stdout=subprocess.PIPE)
        else:
            src = subprocess.Popen(["cat", str(reads)], stdout=subprocess.PIPE)
        # -n2 -s7+ -b -q3 are recommended parameters for Illumina data per fqzcomp docs
        subprocess.check_call(
            ["fqzcomp", "-n2", "-s7+", "-b", "-q3", "/dev/stdin", str(output_file)],
            stdin=src.stdout,
        )

    def compress(self, fwd_reads, rev_reads, output_prefix, num_threads=1, **kwargs) -> CompressResult:
        out_r1 = Path(str(output_prefix) + "_1.fqz")
        t0 = time.monotonic()
        self._compress_one(fwd_reads, out_r1)
        output_files = [out_r1]
        if rev_reads is not None:
            out_r2 = Path(str(output_prefix) + "_2.fqz")
            self._compress_one(rev_reads, out_r2)
            output_files.append(out_r2)
        return CompressResult(
            output_files=output_files,
            elapsed_seconds=time.monotonic() - t0,
            tool_version=self.get_version(),
        )

    def decompress(self, archive, output_prefix, num_threads=1, **kwargs) -> DecompressResult:
        archives = archive if isinstance(archive, list) else [archive]
        output_files = []
        t0 = time.monotonic()
        for i, arc in enumerate(archives, start=1):
            out = Path(str(output_prefix) + f"_{i}.fastq")
            subprocess.check_call(["fqzcomp", "-d", str(arc), str(out)])
            output_files.append(out)
        return DecompressResult(output_files=output_files, elapsed_seconds=time.monotonic() - t0)
