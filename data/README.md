# Test Data

Place FASTQ and BAM files here before running benchmarks. These files are not committed to the
repository due to their size.

## Quick start

```bash
# Create the data-prep conda environment
conda env create -f data/environment.yml
conda activate fastq-compression-data

# Download WES FASTQ + reference + aligned BAM (~25 GB, ~1-2 hours)
python data/prepare_test_data.py -j 8

# FASTQ only (no alignment, no reference download):
python data/prepare_test_data.py --skip-alignment -j 8

# Also include the large WGS sample (~600 GB, many hours):
python data/prepare_test_data.py --include-wgs -j 16
```

The script is idempotent — re-running it skips any step whose output already exists.

## Test samples

| Accession | Type | Instrument | Approx. disk |
|-----------|------|------------|--------------|
| [SRR2962693](https://www.ncbi.nlm.nih.gov/sra/?term=SRR2962693) | WES | Illumina HiSeq 2500 | ~25 GB (FASTQ + BAM) |
| [SRR8861483](https://www.ncbi.nlm.nih.gov/sra/?term=SRR8861483) | WGS | Illumina NovaSeq 6000 | ~600 GB (FASTQ + BAM) |

The two samples cover older multi-bit quality encoding (HiSeq) and Illumina's newer 2-bit binned
quality encoding (NovaSeq), which significantly affects compression ratios.

## Reference genome

The script downloads **GRCh38/hg38** (UCSC soft-masked primary assembly, ~3 GB uncompressed) and
builds a BWA-MEM2 index (~30 GB additional disk, ~20 min with 8 threads).

## What gets generated

After running `prepare_test_data.py` this directory will contain:

```
data/
  SRR2962693_1.fastq.gz     # forward reads
  SRR2962693_2.fastq.gz     # reverse reads
  SRR2962693.bam            # sorted, indexed BAM
  SRR2962693.bam.bai
  hg38.fa                   # reference genome
  hg38.fa.gz                # compressed reference (kept for space efficiency)
  hg38.fa.bwt.2bit.64       # BWA-MEM2 index files
  ...
```

## Running the benchmark

```bash
# FASTQ benchmark
python run_benchmark.py \
  -1 data/SRR2962693_1.fastq.gz \
  -2 data/SRR2962693_2.fastq.gz \
  -j 8

# (BAM/CRAM benchmark tooling coming soon)
```
