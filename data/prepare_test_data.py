#!/usr/bin/env python3
"""
Prepare test data for the FASTQ and BAM/CRAM compression benchmarks.

Downloads FASTQ files from SRA, downloads the GRCh38 human reference,
aligns reads with BWA-MEM2, and produces sorted+indexed BAM files.

Setup:
  conda env create -f data/environment.yml
  conda activate fastq-compression-data

Usage:
  python data/prepare_test_data.py [options]

  # FASTQ only (no reference download or alignment):
  python data/prepare_test_data.py --skip-alignment

  # FASTQ + BAM for WES sample (default):
  python data/prepare_test_data.py -j 8

  # Also include the large WGS sample (~600 GB total disk):
  python data/prepare_test_data.py --include-wgs -j 16
"""
from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SAMPLES: dict[str, dict] = {
    "SRR2962693": {
        "description": "WES — Illumina HiSeq 2500, human whole-exome (~25 GB total)",
    },
    "SRR8861483": {
        "description": "WGS — Illumina NovaSeq 6000, human whole-genome (~600 GB total)",
        "large": True,
    },
}

# UCSC hg38 primary assembly (soft-masked); stable URL
REFERENCE_URL = "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/hg38.fa.gz"
REFERENCE_GZ = "hg38.fa.gz"
REFERENCE_FA = "hg38.fa"


def _run(cmd: list[str], **kwargs) -> None:
    log.info("+ %s", " ".join(str(c) for c in cmd))
    subprocess.check_call(cmd, **kwargs)


def _check_tools(skip_alignment: bool) -> None:
    required = ["prefetch", "fasterq-dump"]
    if not skip_alignment:
        required += ["bwa-mem2", "samtools"]
    missing = [t for t in required if shutil.which(t) is None]
    if missing:
        log.error("Missing required tools: %s", ", ".join(missing))
        log.error("Run: conda env create -f data/environment.yml && conda activate fastq-compression-data")
        sys.exit(1)


def _gzip_cmd() -> str:
    return "pigz" if shutil.which("pigz") else "gzip"


def download_fastq(accession: str, output_dir: Path, num_threads: int) -> tuple[Path, Path]:
    r1 = output_dir / f"{accession}_1.fastq.gz"
    r2 = output_dir / f"{accession}_2.fastq.gz"
    if r1.exists() and r2.exists():
        log.info("[%s] FASTQ already present — skipping", accession)
        return r1, r2

    sra_cache = output_dir / accession
    if not sra_cache.exists():
        log.info("[%s] Prefetching from SRA...", accession)
        _run(["prefetch", accession, "--output-directory", str(output_dir)])

    log.info("[%s] Extracting FASTQ with %d threads...", accession, num_threads)
    _run([
        "fasterq-dump", accession,
        "--split-files",
        "--threads", str(num_threads),
        "--outdir", str(output_dir),
        "--temp", str(output_dir),
    ])

    for raw in [output_dir / f"{accession}_1.fastq", output_dir / f"{accession}_2.fastq"]:
        if raw.exists():
            log.info("Compressing %s...", raw.name)
            _run([_gzip_cmd(), "-f", str(raw)])

    return r1, r2


def download_reference(output_dir: Path) -> Path:
    ref_gz = output_dir / REFERENCE_GZ
    ref_fa = output_dir / REFERENCE_FA
    if ref_fa.exists():
        log.info("Reference genome already present — skipping download")
        return ref_fa
    if not ref_gz.exists():
        log.info("Downloading GRCh38/hg38 primary assembly (~900 MB compressed)...")
        _run(["wget", "-c", "-O", str(ref_gz), REFERENCE_URL])
    log.info("Decompressing reference (this will produce a ~3 GB file)...")
    _run([_gzip_cmd(), "-d", "-k", str(ref_gz)])
    return ref_fa


def build_bwa_index(ref_fa: Path) -> None:
    # bwa-mem2 index produces ref.bwt.2bit.64 as the main index file
    index_marker = ref_fa.parent / (ref_fa.name + ".bwt.2bit.64")
    if index_marker.exists():
        log.info("BWA-MEM2 index already present — skipping")
        return
    log.info("Building BWA-MEM2 index (~20 min, requires ~30 GB RAM and ~30 GB disk)...")
    _run(["bwa-mem2", "index", str(ref_fa)])


def align_sample(
    accession: str,
    r1: Path,
    r2: Path,
    ref_fa: Path,
    output_dir: Path,
    num_threads: int,
) -> Path:
    bam = output_dir / f"{accession}.bam"
    if bam.exists():
        log.info("[%s] BAM already present — skipping alignment", accession)
        return bam

    log.info("[%s] Aligning with BWA-MEM2 and sorting...", accession)
    rg = f"@RG\\tID:{accession}\\tSM:{accession}\\tPL:ILLUMINA"
    align_cmd = [
        "bwa-mem2", "mem",
        "-t", str(num_threads),
        "-R", rg,
        str(ref_fa), str(r1), str(r2),
    ]
    sort_cmd = ["samtools", "sort", "-@", str(num_threads), "-o", str(bam)]
    align_proc = subprocess.Popen(align_cmd, stdout=subprocess.PIPE)
    subprocess.check_call(sort_cmd, stdin=align_proc.stdout)
    if align_proc.wait() != 0:
        raise subprocess.CalledProcessError(align_proc.returncode, align_cmd)

    log.info("[%s] Indexing BAM...", accession)
    _run(["samtools", "index", "-@", str(num_threads), str(bam)])
    return bam


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--output-dir", type=Path, default=Path(__file__).parent,
        help="Directory for all downloaded and generated files (default: data/)",
    )
    parser.add_argument(
        "--include-wgs", action="store_true",
        help="Also download and align the large WGS sample (~600 GB disk, several hours)",
    )
    parser.add_argument(
        "--skip-alignment", action="store_true",
        help="Download FASTQ only; skip reference download and alignment",
    )
    parser.add_argument(
        "-j", "--num-threads", type=int, default=8,
        help="Threads for fasterq-dump, BWA-MEM2, and samtools (default: 8)",
    )
    args = parser.parse_args()

    _check_tools(args.skip_alignment)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    accessions = ["SRR2962693"]
    if args.include_wgs:
        log.warning(
            "WGS sample SRR8861483 requires ~600 GB disk and many hours to download and align."
        )
        accessions.append("SRR8861483")

    # Step 1: download FASTQ
    sample_reads: dict[str, tuple[Path, Path]] = {}
    for acc in accessions:
        log.info("=== %s: %s ===", acc, SAMPLES[acc]["description"])
        sample_reads[acc] = download_fastq(acc, args.output_dir, args.num_threads)

    if args.skip_alignment:
        log.info("Done (--skip-alignment). FASTQ files are in %s", args.output_dir)
        return

    # Step 2: download reference + build index
    ref_fa = download_reference(args.output_dir)
    build_bwa_index(ref_fa)

    # Step 3: align each sample
    for acc, (r1, r2) in sample_reads.items():
        align_sample(acc, r1, r2, ref_fa, args.output_dir, args.num_threads)

    log.info("All done. Files in %s", args.output_dir)
    log.info("Run the benchmark with:")
    log.info("  python run_benchmark.py -1 data/%s_1.fastq.gz -2 data/%s_2.fastq.gz",
             accessions[0], accessions[0])


if __name__ == "__main__":
    main()
