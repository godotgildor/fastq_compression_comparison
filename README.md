# Comparison of FASTQ compression algorithms

## Background
Next generation sequencing (NGS) experiments produce a tremendous amount of raw data that will 
be used in further downstream analysis. Typically, the raw data from an instrument is stored in 
[FASTQ](https://en.wikipedia.org/wiki/FASTQ_format) format, a raw text format where each base read
is represented by 2 bytes - a byte to provide the nucleotide at a given position and a second byte 
providing a quality score, or how confident the instrument was in calling that nucleotide.

In raw text format, these files are quite hefty. For instance, when sequencing the whole human genome,
experiments frequently will aim to have each nucleotide represented on average 30 times in their
sequencing run. This would lead to raw FASTQ files of around:
```
3 billion nucleotides * 30x coverage * 2 bytes/nucleotide = 180 GB
```

Storing the data as raw text is incredibly inefficient though. Nucleotides are typically chosen from an
alphabet of 4 characters (or potentially a little more if one wishes to allow for ambiguous or no-calls),
so one would expect a bit over 2 bits needed per nucleotide rather than the full 8 bits provided in 
the text file. The quality score range varies by instrument, with some instruments using as few as 2 bits
to represent quality scores. Historically, the most popular instruments would output around 64 different 
quality scores which would require around 6 bits to encode them directly. Thus, a simple binary encoding of 
the information should take only about half of the naive text version: 
```
(2 bits + 6 bits)/(8 bits + 8 bits) = 50%
```

The data itself is not uniformly distributed though and thus even better compression ratios should be
achievable by using entropic methods of compression or leveraging information about the 
nature of genomic data. To that end, a number of researchers have created tools to compress genomic data.

I am interested in surveying some of these tools to get a sense of the compression ratios they afford 
and determine if they would be able to fit in with typical NGS data workflows.

## Tools evaluated
* **gzip** - By far the most popular method to compress FASTQ files is to simply gzip them. Most bioinformatic
tools will accept gzipped files as input. 
* **Unmapped BAM** - The BAM file format is a binary format that traditionally was used to store reads mapped
to a reference genome. Recently, the bioinformatics community has begun to use the BAM file to store the
raw, unmapped reads as well, with the Broad Institute using the uBAM format as the starting point for their
[best practices pipeline](https://software.broadinstitute.org/gatk/documentation/article?id=11008).
* **Unmapped CRAM** - Like the BAM format, the CRAM format is a binary format typically used to store reads
mapped to a reference genome. The CRAM format is able to compress the data more thoroughly, at least partially
with the knowledge of the reference genome used for mapping. It will be interesting to see how much better
CRAM is than BAM when the data has not be mapped and no reference provided. CRAM files can also compress 
the quality scores in a lossy manner. For this initial evaluation, we will use CRAM in a lossless encoding
manner.
* [**FaStore**](https://academic.oup.com/bioinformatics/article/34/16/2748/4956350) - The FaStore compressor
offers both lossless and lossy compresion. For lossy compression, it can both alter read identifiers as
well as alter quality scores. For our tests, we will only evaluate the lossless mode for now. While
I suspect that for many if not most cases, compressing the quality scores will have little to no impact
on downstream analysis, to simplify the current evaluation I will stick to the uncontroversial lossless 
approaches. That said, I would evaluate discarding the read identifiers, but it is a bit challenging
to both keep the full quality scores and discard the read identifiers using the scripts provided by FaStore.
* [**Spring**](https://academic.oup.com/bioinformatics/article-abstract/35/15/2674/5232998?redirectedFrom=fulltext) - 
The Spring compressor offers lossless and lossy modes similar to FaStore. Like FaStore, I will only evaluate
lossless quality compression here. I will also evaluate the removal of read identifiers here though as it
is a straight forward option to the tool.
* [**fqzcomp**](https://github.com/jkbonfield/fqzcomp) - This compressor also offers lossless and lossy
compression of quality scores. Once again, for our evaluation purposes we will stick to lossless for now.

## Data used during evaluation
As a first pass evaluation, I selected two NGS samples from the 
[Sequence Read Archive (SRA)](https://www.ncbi.nlm.nih.gov/sra/) to evaluate a set of compression 
techniques.

[**SRR2962693**](https://www.ncbi.nlm.nih.gov/sra/?term=SRR2962693): A human, whole exome sample from an Illumina HiSeq 2500 run. 

[**SRR8861483**](https://www.ncbi.nlm.nih.gov/sra/?term=SRR8861483): A human, whole genome sample from an Illumina NovaSeq 6000 run.

Starting with their NovaSeq instruments, Illumina began using a simplified quality binning approach, 
with each base pair using around 2 bits to store quality information rather than the ~6 bits used in 
previous machines like the HiSeq line. Thus, our samples should allow us to monitor performance
differences due to changes in quality representation across the older and newer instruments.

## Results

### Timing
For this initial evaluation, I chose not to concentrate on optimizing the timing of each approach. Some of the tools
here make use of multiple-cores better than others and there may be ways to more efficiently leverage the tools, (in 
a scatter gather approach for example), but I thought a simple accounting of the time it took each tool to compress
the data would still be informative. 

Note that for two of the compression schemes (gzip and fqzcomp), for paired-end data the tools compress each FASTQ 
separately. I will record both the total serial time and the per-file times for these samples. In most instances,
I assume using the max of the per-file time would be most pertinent here since in most cases one would choose to 
run each of these in parallel.

#### Compression
|   Sample   |             gzip            |  uBAM | uCRAM | FaStore | Spring | Spring --no-ids | fqzcomp |
| ---------- | --------------------------- | ----- | ----- | ------- | ------ | --------------- | ------- |
| SRR2962693 | 25.5m and 26m (51.5m total) | ----- | ----- | ------- | ------ | --------------- | ------- |
| SRR8861483 | ----------------------------| ----- | ----- | ------- | ------ | --------------- | ------- | 

#### Decompression
|   Sample   |               gzip            |  uBAM | uCRAM | FaStore | Spring | Spring --no-ids | fqzcomp |
| ---------- | ----------------------------- | ----- | ----- | ------- | ------ | --------------- | ------- |
| SRR2962693 | 3.75m and 3.75mm (7.5m total) | ----- | ----- | ------- | ------ | --------------- | ------- | 
| SRR8861483 | ----------------------------- | ----- | ----- | ------- | ------ | --------------- | ------- |


### Storage size
As discussed in the tools section, I am concentrating on lossless compression for this current study. In many
cases, it may make sense to leverage lossy compression as the quality scores are fairly noisy and a number of
studies show that it's possible to significantly bin quality scores without significantly impacting typical
variant calling pipelines. However, to limit scope to the most uncontroversial mode of compression, for
now I'll look at methods that preserve the full, original quality information.

|   Sample   |  SRA  | FASTQ | FASTQ.gz |  uBAM | uCRAM | FaStore | Spring | Spring --no-ids | fqzcomp |
| ---------- | ----- | ----- | -------- | ----- | ----- | ------- | ------ | --------------- | ------- |
| SRR2962693 |  7 GB | 40 GB |  10.3 GB | ----- | ----- | ------- | ------ | --------------- | ------- | 
| SRR8861483 | ----- | ----- | -------- | ----- | ----- | ------- | ------ | --------------- | ------- |

## Final caveats
In the studies described above, I did not verify that the decompressed data matches the original data. A few
tools mentioned there could be slight changes to white space or other small character changes that would impact
md5 sums but should not impact the underlying information. In the future, it would be nice simply check that the
nucleotides and quality scores are all as expected, but for now I'm assuming the tools are working as expected.

In many pipelines, it may make sense to store the mapped data and throw away the original raw data. Assuming
your mapped reads contain at least one full-length entry for every raw read, you should be able to 
revert to unmapped FASTQ input without too much struggle and you having the mapped data would allow one to
restart their pipeline at the variant calling stages rather than re-map the samples in any re-runs. In this case,
a mapped CRAM, potentially with compressing quality scores using native CRAM quality score compression or 
external tools like [Crumble]() probably makes the most sense.

However, there are a number of cases where keeping the raw, unmapped data makes the most sense. For example,
there are many analyses that may be performed that don't have a mapping stage. Also, some projects anticipate
users leveraging multiple reference genomes in which case storing the data mapped to one specific reference
might not make sense. For these projects, leveraging one of the tools above might be the most appropriate.