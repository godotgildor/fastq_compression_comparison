from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path
from typing import ClassVar

from tools.base import BaseCompressor, CompressResult, DecompressResult, Fidelity


class RepaqCompressor(BaseCompressor):
    name = "repaq"
    fidelity = Fidelity.LOSSLESS
    conda_deps: ClassVar[list[str]] = ["repaq>=0.3"]

    def compress(self, fwd_reads, rev_reads, output_prefix, num_threads=1, **kwargs) -> CompressResult:
        output_file = Path(str(output_prefix) + ".rfq")
        cmd = ["repaq", "-c", "--stdout", "-i", str(fwd_reads)]
        if rev_reads is not None:
            cmd += ["-I", str(rev_reads)]
        t0 = time.monotonic()
        with open(output_file, "wb") as fh:
            subprocess.check_call(cmd, stdout=fh)
        return CompressResult(
            output_files=[output_file],
            elapsed_seconds=time.monotonic() - t0,
            tool_version=self.get_version(),
        )

    def decompress(self, archive, output_prefix, num_threads=1, **kwargs) -> DecompressResult:
        arc = archive[0] if isinstance(archive, list) else archive
        out_r1 = Path(str(output_prefix) + "_1.fastq")
        out_r2 = Path(str(output_prefix) + "_2.fastq")
        t0 = time.monotonic()
        subprocess.check_call(["repaq", "-d", "-i", str(arc), "-o", str(out_r1), "-O", str(out_r2)])
        output_files = [f for f in [out_r1, out_r2] if f.exists() and f.stat().st_size > 0]
        return DecompressResult(output_files=output_files, elapsed_seconds=time.monotonic() - t0)

    def get_version(self) -> str:
        try:
            r = subprocess.run(["repaq", "--version"], capture_output=True, text=True)
            return (r.stdout or r.stderr).strip().splitlines()[0]
        except Exception:
            return ""


class RepaqXzCompressor(BaseCompressor):
    name = "repaq-xz"
    fidelity = Fidelity.LOSSLESS
    conda_deps: ClassVar[list[str]] = ["repaq>=0.3", "xz"]
    _executable = "repaq"

    def compress(self, fwd_reads, rev_reads, output_prefix, num_threads=1, **kwargs) -> CompressResult:
        output_file = Path(str(output_prefix) + ".rfq.xz")
        repaq_cmd = ["repaq", "-c", "--stdout", "-i", str(fwd_reads)]
        if rev_reads is not None:
            repaq_cmd += ["-I", str(rev_reads)]
        xz_cmd = ["xz", "-T", str(num_threads), "--lzma2=dict=1000000000", "-z", "-c"]
        t0 = time.monotonic()
        with open(output_file, "wb") as fh:
            repaq_proc = subprocess.Popen(repaq_cmd, stdout=subprocess.PIPE)
            subprocess.check_call(xz_cmd, stdin=repaq_proc.stdout, stdout=fh)
        return CompressResult(
            output_files=[output_file],
            elapsed_seconds=time.monotonic() - t0,
            tool_version=RepaqCompressor().get_version(),
        )

    def decompress(self, archive, output_prefix, num_threads=1, **kwargs) -> DecompressResult:
        arc = archive[0] if isinstance(archive, list) else archive
        out_r1 = Path(str(output_prefix) + "_1.fastq")
        out_r2 = Path(str(output_prefix) + "_2.fastq")
        t0 = time.monotonic()
        with tempfile.NamedTemporaryFile(suffix=".rfq", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            subprocess.check_call(["xz", "-d", "-T", str(num_threads), "-k", "-c", str(arc)],
                                  stdout=tmp_path.open("wb"))
            subprocess.check_call(["repaq", "-d", "-i", str(tmp_path),
                                   "-o", str(out_r1), "-O", str(out_r2)])
        finally:
            tmp_path.unlink(missing_ok=True)
        output_files = [f for f in [out_r1, out_r2] if f.exists() and f.stat().st_size > 0]
        return DecompressResult(output_files=output_files, elapsed_seconds=time.monotonic() - t0)
