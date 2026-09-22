from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import ClassVar

from tools.base import BaseCompressor, CompressResult, DecompressResult, Fidelity


class SpringCompressor(BaseCompressor):
    name = "spring"
    fidelity = Fidelity.LOSSLESS
    conda_deps: ClassVar[list[str]] = ["spring>=1.1"]
    license_note = "Free for non-commercial use"

    def compress(self, fwd_reads, rev_reads, output_prefix, num_threads=1, **kwargs) -> CompressResult:
        output_file = Path(str(output_prefix) + ".spring")
        cmd = ["spring", "-c", "-o", str(output_file), "-t", str(num_threads)]
        if fwd_reads.suffix == ".gz":
            cmd.append("-g")
        cmd += ["-i", str(fwd_reads)]
        if rev_reads is not None:
            cmd.append(str(rev_reads))
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
        cmd = ["spring", "-d", "-i", str(arc), "-o", str(out_r1), "-o2", str(out_r2), "-t", str(num_threads)]
        t0 = time.monotonic()
        subprocess.check_call(cmd)
        output_files = [f for f in [out_r1, out_r2] if f.exists() and f.stat().st_size > 0]
        return DecompressResult(output_files=output_files, elapsed_seconds=time.monotonic() - t0)

    def get_version(self) -> str:
        try:
            r = subprocess.run(["spring", "--version"], capture_output=True, text=True)
            return (r.stdout or r.stderr).strip().splitlines()[0]
        except Exception:
            return ""


class SpringNoIdsCompressor(SpringCompressor):
    name = "spring-no-ids"
    fidelity = Fidelity.ID_LOSSY

    def compress(self, fwd_reads, rev_reads, output_prefix, num_threads=1, **kwargs) -> CompressResult:
        output_file = Path(str(output_prefix) + ".spring")
        cmd = ["spring", "-c", "--no-ids", "-o", str(output_file), "-t", str(num_threads)]
        if fwd_reads.suffix == ".gz":
            cmd.append("-g")
        cmd += ["-i", str(fwd_reads)]
        if rev_reads is not None:
            cmd.append(str(rev_reads))
        t0 = time.monotonic()
        subprocess.check_call(cmd)
        return CompressResult(
            output_files=[output_file],
            elapsed_seconds=time.monotonic() - t0,
            tool_version=self.get_version(),
        )
