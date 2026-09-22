from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import ClassVar

from tools.base import BaseCompressor, CompressResult, DecompressResult, Fidelity


class UbamCompressor(BaseCompressor):
    """Unmapped BAM via samtools import. Read order will differ from original."""

    name = "ubam"
    fidelity = Fidelity.RECORD_REORDERED
    conda_deps: ClassVar[list[str]] = ["samtools>=1.16"]
    _executable = "samtools"

    def compress(self, fwd_reads, rev_reads, output_prefix, num_threads=1, **kwargs) -> CompressResult:
        output_file = Path(str(output_prefix) + ".bam")
        cmd = ["samtools", "import", "-@", str(num_threads), "-o", str(output_file)]
        if rev_reads:
            cmd += ["-1", str(fwd_reads), "-2", str(rev_reads)]
        else:
            cmd.append(str(fwd_reads))
        t0 = time.monotonic()
        subprocess.check_call(cmd)
        return CompressResult(
            output_files=[output_file],
            elapsed_seconds=time.monotonic() - t0,
            tool_version=self.get_version(),
        )

    def decompress(self, archive, output_prefix, num_threads=1, **kwargs) -> DecompressResult:
        arc = archive[0] if isinstance(archive, list) else archive
        out_r1 = Path(str(output_prefix) + "_1.fastq")
        out_r2 = Path(str(output_prefix) + "_2.fastq")
        cmd = [
            "samtools", "fastq", "-@", str(num_threads), "-N",
            "-1", str(out_r1), "-2", str(out_r2),
            "-0", "/dev/null", "-s", "/dev/null",
            str(arc),
        ]
        t0 = time.monotonic()
        subprocess.check_call(cmd)
        output_files = [f for f in [out_r1, out_r2] if f.exists() and f.stat().st_size > 0]
        return DecompressResult(output_files=output_files, elapsed_seconds=time.monotonic() - t0)

    def get_version(self) -> str:
        try:
            r = subprocess.run(["samtools", "--version"], capture_output=True, text=True)
            return r.stdout.splitlines()[0]
        except Exception:
            return ""
