from __future__ import annotations

import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import ClassVar


class Fidelity(str, Enum):
    LOSSLESS = "lossless"                  # bit-identical round trip
    RECORD_REORDERED = "record-reordered"  # all data preserved, read order may differ
    ID_LOSSY = "id-lossy"                  # seq+qual preserved, IDs stripped/replaced
    QUALITY_LOSSY = "quality-lossy"        # seq preserved, quality scores may change
    LOSSY = "lossy"                        # any sequence-level data loss


@dataclass
class CompressResult:
    output_files: list[Path]
    elapsed_seconds: float
    tool_version: str = ""


@dataclass
class DecompressResult:
    output_files: list[Path]
    elapsed_seconds: float


class BaseCompressor(ABC):
    name: ClassVar[str]
    fidelity: ClassVar[Fidelity]
    conda_deps: ClassVar[list[str]] = []
    conda_channels: ClassVar[list[str]] = ["bioconda", "conda-forge", "defaults"]
    install_steps: ClassVar[list[str]] = []
    license_note: ClassVar[str] = ""
    _executable: ClassVar[str] = ""  # override if differs from name

    @abstractmethod
    def compress(
        self,
        fwd_reads: Path,
        rev_reads: Path | None,
        output_prefix: Path,
        num_threads: int = 1,
        **kwargs,
    ) -> CompressResult: ...

    @abstractmethod
    def decompress(
        self,
        archive: list[Path],
        output_prefix: Path,
        num_threads: int = 1,
        **kwargs,
    ) -> DecompressResult: ...

    def get_version(self) -> str:
        return ""

    @property
    def executable(self) -> str:
        return self._executable or self.name

    def is_available(self) -> bool:
        return shutil.which(self.executable) is not None
