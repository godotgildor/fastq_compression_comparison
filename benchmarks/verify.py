"""Verify fidelity of compression round-trips by comparing FASTQ content."""
from __future__ import annotations

import gzip
from enum import Enum
from pathlib import Path
from typing import Iterator


class VerificationResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


def _open_fastq(path: Path):
    return gzip.open(path, "rt") if path.suffix == ".gz" else open(path)


def _iter_records(path: Path) -> Iterator[tuple[str, str, str]]:
    """Yield (header, seq, qual) for each record."""
    with _open_fastq(path) as fh:
        while True:
            header = fh.readline()
            if not header:
                break
            seq = fh.readline().strip()
            fh.readline()  # +
            qual = fh.readline().strip()
            yield header.strip(), seq, qual


def _read_by_id(path: Path) -> dict[str, tuple[str, str]]:
    """Read FASTQ into {normalized_read_id: (seq, qual)}."""
    records = {}
    for header, seq, qual in _iter_records(path):
        read_id = header.lstrip("@").split()[0].rstrip("/12")
        records[read_id] = (seq, qual)
    return records


def _verify_lossless(original: Path, decompressed: Path) -> tuple[VerificationResult, str]:
    orig = _read_by_id(original)
    decomp = _read_by_id(decompressed)
    if orig == decomp:
        return VerificationResult.PASS, ""
    missing = set(orig) - set(decomp)
    extra = set(decomp) - set(orig)
    if missing or extra:
        return VerificationResult.FAIL, f"Read ID mismatch: {len(missing)} missing, {len(extra)} extra"
    diffs = [rid for rid in orig if orig[rid] != decomp[rid]]
    return VerificationResult.FAIL, f"{len(diffs)}/{len(orig)} records differ"


def _verify_record_reordered(original: Path, decompressed: Path) -> tuple[VerificationResult, str]:
    """All seq+qual preserved but order may differ; compare by read ID."""
    return _verify_lossless(original, decompressed)


def _verify_positional(
    original: Path,
    decompressed: Path,
    check_qual: bool,
) -> tuple[VerificationResult, str]:
    """Compare records positionally (for id-lossy and quality-lossy tools)."""
    mismatches = 0
    total = 0
    for (_, seq_o, qual_o), (_, seq_d, qual_d) in zip(
        _iter_records(original), _iter_records(decompressed)
    ):
        total += 1
        if seq_o != seq_d:
            mismatches += 1
        elif check_qual and qual_o != qual_d:
            mismatches += 1
    if mismatches:
        what = "seq or qual" if check_qual else "sequence"
        return VerificationResult.FAIL, f"{mismatches}/{total} records differ in {what}"
    return VerificationResult.PASS, ""


def verify(
    fidelity: str,
    original_fwd: Path,
    original_rev: Path | None,
    decompressed_fwd: Path | None,
    decompressed_rev: Path | None,
) -> tuple[VerificationResult, str]:
    from tools.base import Fidelity

    if decompressed_fwd is None:
        return VerificationResult.FAIL, "No decompressed forward reads produced"

    dispatch = {
        Fidelity.LOSSLESS: lambda o, d: _verify_lossless(o, d),
        Fidelity.RECORD_REORDERED: lambda o, d: _verify_record_reordered(o, d),
        Fidelity.ID_LOSSY: lambda o, d: _verify_positional(o, d, check_qual=True),
        Fidelity.QUALITY_LOSSY: lambda o, d: _verify_positional(o, d, check_qual=False),
        Fidelity.LOSSY: lambda o, d: (VerificationResult.SKIP, "fidelity=lossy, skipping"),
    }

    fn = dispatch.get(fidelity)
    if fn is None:
        return VerificationResult.SKIP, f"Unknown fidelity: {fidelity}"

    result, msg = fn(original_fwd, decompressed_fwd)
    if result != VerificationResult.PASS:
        return result, f"R1: {msg}"

    if original_rev and decompressed_rev:
        result, msg = fn(original_rev, decompressed_rev)
        if result != VerificationResult.PASS:
            return result, f"R2: {msg}"

    return VerificationResult.PASS, ""
