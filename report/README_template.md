> **Note:** The [Tools evaluated](#tools-evaluated) and [Results](#results) sections of this README are
> auto-generated from files in `benchmarks/results/`. To regenerate after a new benchmark run, execute
> `python report/generate.py`.

# Comparison of FASTQ compression algorithms

## Background
Next generation sequencing (NGS) experiments produce a tremendous amount of raw data that will
be used in further downstream analysis. Typically, the raw data from an instrument is stored in
[FASTQ](https://en.wikipedia.org/wiki/FASTQ_format) format, a raw text format where each base read
is represented by 2 bytes — a byte for the nucleotide and a second byte for the quality score.

In raw text format these files are quite hefty. Sequencing the whole human genome at 30× coverage
yields approximately 180 GB of raw FASTQ. A naïve binary encoding of the same information (2 bits for
base + ~6 bits for quality) should achieve roughly 50% of the text size, and tools that exploit
properties of genomic data can do considerably better.

This repository provides a standardized benchmarking harness for evaluating FASTQ compression tools:
reproducible environment setup, a common runner, automatic fidelity verification, and machine-readable
results that feed directly into this README.

## Fidelity classes

| Class | Meaning |
|-------|---------|
| `lossless` | Bit-identical round trip |
| `record-reordered` | All data preserved; read order may differ (e.g. reads sorted by name) |
| `id-lossy` | Sequences and quality scores preserved; record IDs stripped or replaced |
| `quality-lossy` | Sequences preserved; quality scores may be altered |
| `lossy` | Any sequence-level data loss |

Fidelity claims are **verified automatically** after each decompression run. A `FAIL` in the verified
column means the tool did not meet its claimed fidelity on the test data.

## Tools evaluated

<!-- TOOLS_TABLE -->

### Notable tools not included in this benchmark

**Illumina DRAGEN ORA** — Illumina acquired PetaGene in 2022 and integrated their technology into
DRAGEN as [ORA (Optimized Reference-based Algorithm) compression](https://www.illumina.com/products/by-type/informatics-products/dragen-bio-it-platform.html),
which claims up to 5× compression over uncompressed FASTQ. ORA is now the default output format on
instruments running DRAGEN. A standalone decompressor (`orad`) is freely available from Illumina, but
the compressor itself requires DRAGEN hardware or a cloud license, making it impossible to include in
an open benchmark. The `petagene` entry in this repo reflects the pre-acquisition standalone PetaSuite
product; that product is no longer actively maintained.

## Test data

See [`data/README.md`](data/README.md) for instructions on downloading the reference datasets.

## Running the benchmark

```bash
# Build the Docker image (from repo root)
docker build -f docker/Dockerfile -t fastq-compression-benchmark .

# Run all tools on a sample
docker run --rm \
  -v /path/to/data:/data \
  -v $(pwd)/benchmarks/results:/app/benchmarks/results \
  fastq-compression-benchmark \
  -1 /data/SRR2962693_1.fastq.gz \
  -2 /data/SRR2962693_2.fastq.gz \
  -j 8

# Regenerate README after new results land
python report/generate.py
```

To run only specific tools:

```bash
docker run ... fastq-compression-benchmark -1 ... -2 ... --tools spring repaq genozip
```

## Adding a new tool

1. Create `tools/<toolname>.py` implementing `BaseCompressor` (see `tools/base.py`).
2. Set `conda_deps` (and `conda_channels` if non-bioconda) as class variables.
3. For tools requiring a source build, populate `install_steps` with the shell commands.
4. Rebuild the Docker image — `make_env.py` picks up the new deps automatically.

## Results

<!-- RESULTS_SECTION -->

## Discussion

The results above reflect lossless (or claimed-lossless) compression only unless otherwise noted.
In practice, several tools offer lossy quality-score compression that can significantly improve ratios
at modest impact on downstream variant calling; see the `quality-lossy` rows for an indication of
the additional savings available.

### Storage break-even analysis

For archival purposes the key question is how long you need to store the data for the compression
savings to justify the compute cost. At approximately current AWS spot pricing for a compute-optimized
instance and S3 standard storage, Spring-compressed WGS (≈15 GB vs 33 GB gzipped) breaks even at
roughly **5–10 months** of storage. For cold storage (Glacier), the break-even extends to **2–4 years**.

### Caveats

- Timing measurements reflect single runs on the specific instances noted; wall-clock times will vary.
- FaStore was evaluated in earlier versions of this benchmark but was dropped: the tool is no longer
  maintained (last commit 2022) and never successfully completed compression of either test sample.
- Genozip changed from open source to a commercial license starting in v15 and is no longer on
  bioconda (now distributed via `conda-forge`). It remains free for academic use but requires
  registration at [genozip.com](https://genozip.com); consult your institution's software policies
  before use in a commercial context. The Genozip developers actively encourage inclusion in
  benchmarks — if you have an academic license, their results are worth including.
- Petagene/PetaSuite requires a proprietary installer; results for this tool depend on having a
  valid license. Contact [petagene.com](https://www.petagene.com) for a trial.
