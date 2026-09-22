from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import ClassVar

from tools.base import BaseCompressor, CompressResult, DecompressResult, Fidelity

_FASTQ_RE = r"(.fq|.fastq)(.gz)?$"


class PetageneCompressor(BaseCompressor):
    """
    Requires manual installation: download PetaSuite from petagene.com and
    run `petasuite_install_corpus human` before use. No conda package available.
    """

    name = "petagene"
    fidelity = Fidelity.LOSSLESS
    conda_deps: ClassVar[list[str]] = []
    install_steps: ClassVar[list[str]] = []
    license_note = (
        "Proprietary (PetaGene/Illumina). Requires a license. "
        "Download PetaSuite from petagene.com and run `petasuite_install_corpus human` before use."
    )
    _executable = "petasuite"

    def compress(self, fwd_reads, rev_reads, output_prefix, num_threads=1, **kwargs) -> CompressResult:
        cmd = ["petasuite", "-c", "-t", str(num_threads)]
        out_r1 = Path(re.sub(_FASTQ_RE, ".fasterq", fwd_reads.name))
        t0 = time.monotonic()
        subprocess.check_call(cmd + [str(fwd_reads)])
        output_files = [out_r1]
        if rev_reads is not None:
            subprocess.check_call(cmd + [str(rev_reads)])
            output_files.append(Path(re.sub(_FASTQ_RE, ".fasterq", rev_reads.name)))
        return CompressResult(
            output_files=output_files,
            elapsed_seconds=time.monotonic() - t0,
        )

    def decompress(self, archive, output_prefix, num_threads=1, **kwargs) -> DecompressResult:
        archives = archive if isinstance(archive, list) else [archive]
        output_files = []
        t0 = time.monotonic()
        for arc in archives:
            subprocess.check_call(["petasuite", "-d", "-t", str(num_threads), str(arc)])
            # petasuite restores original .fastq.gz extension
            out = Path(str(arc).removesuffix(".fasterq") + ".fastq.gz")
            if out.exists():
                output_files.append(out)
        return DecompressResult(output_files=output_files, elapsed_seconds=time.monotonic() - t0)
