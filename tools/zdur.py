from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import ClassVar

from tools.base import BaseCompressor, CompressResult, DecompressResult, Fidelity


class ZdurCompressor(BaseCompressor):
    """
    zDUR uses a similarity-tree algorithm; reads are reordered during compression
    but all sequence and quality data is preserved.

    Requires a non-commercial license key (free for academics).
    On first run, zDUR prompts interactively for the key and caches it locally.
    Request a license at https://github.com/MGI-EU/zDUR

    Install: bash scripts/install_zdur.sh
    """

    name = "zdur"
    fidelity = Fidelity.RECORD_REORDERED
    conda_deps: ClassVar[list[str]] = []
    install_steps: ClassVar[list[str]] = ["bash /app/scripts/install_zdur.sh"]
    license_note = (
        "Non-commercial license required (free for academics). "
        "Run `zdur` once interactively to register your key. "
        "See https://github.com/MGI-EU/zDUR"
    )

    def compress(self, fwd_reads, rev_reads, output_prefix, num_threads=1, **kwargs) -> CompressResult:
        output_file = Path(str(output_prefix) + ".zdur")
        cmd = [
            "zdur", "c-simtree",
            "--i1", str(fwd_reads),
            "--threads", str(num_threads),
            "-o", str(output_file),
        ]
        if rev_reads is not None:
            cmd += ["--i2", str(rev_reads)]
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
            "zdur", "d",
            "--input", str(arc),
            "--threads", str(num_threads),
            "--o1", str(out_r1),
            "--o2", str(out_r2),
        ]
        t0 = time.monotonic()
        subprocess.check_call(cmd)
        output_files = [f for f in [out_r1, out_r2] if f.exists() and f.stat().st_size > 0]
        return DecompressResult(output_files=output_files, elapsed_seconds=time.monotonic() - t0)

    def get_version(self) -> str:
        try:
            r = subprocess.run(["zdur", "--version"], capture_output=True, text=True)
            return (r.stdout or r.stderr).strip().splitlines()[0]
        except Exception:
            return ""
