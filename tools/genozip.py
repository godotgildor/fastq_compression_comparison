from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import ClassVar

from tools.base import BaseCompressor, CompressResult, DecompressResult, Fidelity


class GenozipCompressor(BaseCompressor):
    name = "genozip"
    fidelity = Fidelity.LOSSLESS
    conda_deps: ClassVar[list[str]] = ["genozip>=15"]
    conda_channels: ClassVar[list[str]] = ["conda-forge", "bioconda", "defaults"]
    license_note = (
        "Commercial — free for academic/student use. "
        "Install: `conda install -c conda-forge genozip`. "
        "See https://genozip.com/installing for full instructions and license registration."
    )

    def compress(
        self,
        fwd_reads,
        rev_reads,
        output_prefix,
        num_threads=1,
        reference: Path | None = None,
        **kwargs,
    ) -> CompressResult:
        output_file = Path(str(output_prefix) + ".genozip")
        cmd = ["genozip", str(fwd_reads)]
        if rev_reads:
            cmd += [str(rev_reads), "--pair"]
        cmd += ["--threads", str(num_threads), "--best", "--output", str(output_file)]
        if reference:
            cmd += ["--reference", str(reference)]
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
        cmd = ["genounzip", str(arc), "--output", str(out_r1), "--threads", str(num_threads)]
        t0 = time.monotonic()
        subprocess.check_call(cmd)
        output_files = [f for f in [out_r1, out_r2] if f.exists() and f.stat().st_size > 0]
        return DecompressResult(output_files=output_files, elapsed_seconds=time.monotonic() - t0)

    def get_version(self) -> str:
        try:
            r = subprocess.run(["genozip", "--version"], capture_output=True, text=True)
            return (r.stdout or r.stderr).strip().splitlines()[0]
        except Exception:
            return ""


class GenozipOptimizedCompressor(GenozipCompressor):
    """Uses --optimize: maximizes compression but alters quality scores."""

    name = "genozip-optimize"
    fidelity = Fidelity.QUALITY_LOSSY

    def compress(
        self,
        fwd_reads,
        rev_reads,
        output_prefix,
        num_threads=1,
        reference: Path | None = None,
        **kwargs,
    ) -> CompressResult:
        output_file = Path(str(output_prefix) + ".genozip")
        cmd = ["genozip", str(fwd_reads)]
        if rev_reads:
            cmd += [str(rev_reads), "--pair"]
        cmd += ["--threads", str(num_threads), "--optimize", "--output", str(output_file)]
        if reference:
            cmd += ["--reference", str(reference)]
        t0 = time.monotonic()
        subprocess.check_call(cmd)
        return CompressResult(
            output_files=[output_file],
            elapsed_seconds=time.monotonic() - t0,
            tool_version=self.get_version(),
        )
