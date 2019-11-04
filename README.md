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
tools will accept gzipped files as input. The gzip standard offers various levels of compression, allowing
users to tradeoff compression time and compression efficiency. Gzip level 1 is the fastest to compress a 
given file, but at the cost of some compression efficiency. Gzip level 9 on the other hand should provide
 a smaller overall file at the cost of an increased time compressing the data. For this simple study,
 I ran gzip using the default compression level (level 6) as well as the highest compression level (level 9).
* **Unmapped BAM** - The BAM file format is a binary format that traditionally was used to store reads mapped
to a reference genome. Recently, the bioinformatics community has begun to use the BAM file to store the
raw, unmapped reads as well, with the Broad Institute using the uBAM format as the starting point for their
[best practices pipeline](https://software.broadinstitute.org/gatk/documentation/article?id=11008). The format
encodes the data in a binary format and then that binary information is compressed using a block gzip compression
algorithm. Thus, our naive expectation would be that the total size of a uBAM should be on par with the
gzipped FASTQ files.
* **Unmapped CRAM** - Like the BAM format, the CRAM format is a binary format typically used to store reads
mapped to a reference genome. When a reference genome is provided, the CRAM format is able to compress 
the data more thoroughly. The CRAM format also compresses data on a column basis, allowing the compression
algorithm to be more efficient as it compresses data one type together. It will be interesting to see how much better
our unmapped CRAM is than unmapped BAM since our data has not be mapped and no reference genome will be 
provided. CRAM files are also capable of compressing the quality scores in a lossy manner. For this initial 
evaluation, we will use CRAM in a lossless encoding manner.
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
First, unfortunately I was unable to get FaStore to complete the compression of the test samples. For
both the WES and WGS samples, the tool would begin the multi-stage process of compressing the data,
but it then would freeze. I did not see an error message. While monitoring the initial runs, I did observe
a few peaks in memory use, so I tried the samples on an instance with significant memory resources - roughly
128 GB. I also provided up to 1 TB of storage space in case significant temporary files were generated.
Alas, these efforts did not help. I amy return at some point to investigate these failures in more depth,
but for now I will just report results on the other tools.

### Timing
For this initial evaluation, I chose not to concentrate on optimizing the timing of each approach. Some of the tools
here make use of multiple-cores better than others and there may be ways to more efficiently leverage the tools, (in 
a scatter gather approach for example), but I thought a simple accounting of the time it took each tool to compress
the data would still be informative. 

Note that for two of the compression schemes (gzip and fqzcomp), for paired-end data the tools compress each FASTQ 
separately. I will record both the total serial time and the per-file times for these samples. In most instances,
I assume using the max of the per-file time would be most pertinent here since in most cases one would choose to 
run each of these in parallel.

#### Instance details
##### Whole exome data **SRR2962693**
**AWS c5d.2xlarge**
8 vCPU's
16 GB RAM
Data read from and written to NVME SSD drive

##### Whole genome data **SRR8861483**
**AWS r5d.4xlarge**
16 vCPU's
128 GB RAM
Data read from and written to NVME SSD drive

For tools which allowed for the specification of the number of cores to use, 8 cores were requested
for both WES and WGS samples. The larger instance for WGS was selected for the larger memory and storage
requirements offered.

#### Compression
|   Sample   |             gzip            |             gzip -9         |  uBAM  | uCRAM  | FaStore | Spring | Spring --no-ids |   fqzcom  |
| ---------- | --------------------------- | --------------------------- | ------ | -----  | ------- | ------ | --------------- | --------- |
| SRR2962693 |   26m and 26m (52m total)   |  1h 35m and 1h 39m (3h 14m) |   39m  |  35m   |   DNF   |   26m  |      26m        |    32m    |
| SRR8861483 | 1h 36m and 1h 23m (2h 59m)  |   9h 35m + 12h = 21h 35m    | 2h 34m | 2h 35m |   DNF   |  3h 3m |     3h 2m       |  2h 15m   | 

| SRR2962693 WES | SRR8861483 WGS |
| -------------- | -------------- |
| ![WES Compression times](https://user-images.githubusercontent.com/3038393/68101167-1cdd1d00-fe81-11e9-84f4-73b5fc453335.png)| ![WGS Compression times](https://user-images.githubusercontent.com/3038393/68101218-56158d00-fe81-11e9-807d-e6ec176b7ae0.png) |

#### Decompression
|   Sample   |               gzip            |             gzip -9           |  uBAM | uCRAM  | FaStore | Spring | Spring --no-ids |          fqzcomp            |
| ---------- | ----------------------------- | ----------------------------- | ----- | -----  | ------- | ------ | --------------- | --------------------------- |
| SRR2962693 |      2m and 2m (4m total)     |    2m and 2m (4m total)       | 10m   |  10m   |   DNF   |  16m   |      16m        | 14m and 14m (28m total)     | 
| SRR8861483 | 11m and 11m (22m total)       |      11m and 11m (22m total)  | 58m   | 1h 25m |   DNF   |  53m   |      51m        | 1h 5m and ??? (2h 10m) |

(Note: I forgot to record the time for decompressing the reverse reads for fqzcomp. My assumption is 
that it would take a similar time to decompress the reverse reads as it did to decompress the forward reads.)

| SRR2962693 WES | SRR8861483 WGS |
| -------------- | -------------- |
| ![WES Deompression times](https://user-images.githubusercontent.com/3038393/68101261-937a1a80-fe81-11e9-9ca2-83eab2bf23a2.png)| ![WGS Deompression times](https://user-images.githubusercontent.com/3038393/68101314-d0461180-fe81-11e9-92e5-9674167be848.png) |

### Storage size
As discussed in the tools section, I am concentrating on lossless compression for this current study. In many
cases, it may make sense to leverage lossy compression, as the quality scores are fairly noisy and a number of
studies show that it's possible to significantly bin quality scores without impacting typical
variant calling pipelines. However, to limit the scope to the most uncontroversial mode of compression, for
now I'll look at methods that preserve the full, original quality information.

|   Sample   |  SRA  |   FASTQ    | FASTQ.gz | FASTQ.gz -9 |  uBAM  | uCRAM  | FaStore | Spring | Spring --no-ids | fqzcomp |
| ---------- | ----- | ---------- | -------- | ----------- | ------ | ------ | ------- | ------ | --------------- | ------- |
| SRR2962693 |  7 GB |   40 GB    |  10.3 GB |   9.4 GB    | 9.3 GB | 6.6 GB |   DNF   | 3.5 GB |      3.5 GB     |  4.7 GB | 
| SRR8861483 | 23 GB |   284 GB   |  33 GB   |  32 GB      | 33 GB  | 22 GB  |   DNF   | 15 GB  |      15 GB      |  37 GB  |

| SRR2962693 WES | SRR8861483 WGS |
| -------------- | -------------- |
| ![WES Compressed file sizes](https://user-images.githubusercontent.com/3038393/68100909-94aa4800-fe7f-11e9-99cb-f2f6443dd191.png)| ![WGS Compressed file sizes](https://user-images.githubusercontent.com/3038393/68100964-f965a280-fe7f-11e9-8ca9-29496aaf843a.png) |

## Discussion
As is widely accepted, researchers at a minimum should gzip compress their raw FASTQ files. For the
HiSeq data, this provided a close to 75% reduction in storage space compared to the raw FASTQ. Add in 
the fact that gzipped files are cheap to decompress and the fact that most bioinformatics tools already
accept gzipped FASTQ files as input, there are few reasons to keep raw FASTQ file around very long.

For users who are interested in even greater storage savings though, Spring appears to be a compelling
option. I saw file sizes that saved an additional 55% - 66% storage space compared to gzipped FASTQ files.
While the decompression time was significantly longer than a simple gzip file, it still seemed reasonable
at roughly an hour for decompressing a WGS sample on a 16 core node (where only 8 cores were used). 
It was also nice that the original read ordering is completely preserved (unlike unmapped BAM and CRAM files
where the reads are sorted by read name) and that the raw base pairs and quality scores matched the 
initial data exactly, unlike fqzcomp which has the occasional quality score change. (Again, according
to the fqzcomp authors some changes may be expected as fqzcomp will set the quality score to 0 for an base
pair called as an N. These changes seem eminently reasonable, but it's nice to not have to worry about 
the changes and wonder if maybe at least some subset of changes was due to some other issue).

At a compression time of about 3 hours and a decompression time of about an hour for a WGS on an
r5.4xlarge, we can calculate the break-even time for storing the Spring compressed file vs.
the gzipped file as follows:

**Hot storage**
```
4 hours of r5d.4xlarge * $1.152/hour + 15 GB * $0.026 /GB/month * storage_duration = 33 GB * $0.026 /GB/month * storage_duration

 ($0.858 - $0.39) * storage_duration = $4.608

 storage_duration = 9.9 months
```
I believe we should be able to leverage the smaller r5d.2xlarge and see similar run times for compression and
decompression since we are only using 8 cores. If this is true, our break even time would occur in roughly half
the time, or after about 5 months.

For cold storage (i.e. Glacier) the break-even would be pushed out a bit.
```
4 hours of r5d.4xlarge * $1.152/hour + 15 GB * $0.005 /GB/month * storage_duration = 33 GB * $0.005 /GB/month * storage_duration

 ($0.165 - $0.075) * storage_duration = $4.608

 storage_duration = 51 months
```
Or roughly 26 months if we are able to use an r5d.2xlage.

Leveraging the spot market would bring in our break-even dates further as would the ability
to leverage underutilized compute cycles within our processing pipelines to perform the compression.

## Final caveats
I did not exhaustively verify that the data compression was lossless under all methods. At a minimum, 
I did verify that each tool could produce a pair of FASTQ files that contained the same number of entries 
as the input data. 

For **fqzcomp**, I verified that the nucleotide information of the decompressed data
exactly matches the input. However, I did notice that some of the quality scores had been altered. The
authors note that all bases called as an N will have their quality score set to 0 though. I did not
verify that all quality changes could be explained by this behavior.

For **Spring**, I verified that the nucleotide information and the quality information from the uncompressed 
data exactly matched the input data.

During **uBAM** and **uCRAM** creation, the input reads are sorted by read name, making comparison of 
the uncompressed and initial data more challenging. For now, I did verify that for at least one read
the nucleotides and quality scores match exactly. Although a more thorough validation is possible, I feel
fairly confident that for these two formats one can expect exact data fidelity for the nucleotides and 
quality scores.

In many pipelines, it may make sense to store the mapped data and throw away the original raw data. Assuming
your mapped reads contain at least one full-length entry for every raw read, you should be able to 
revert to unmapped FASTQ input without too much struggle and you having the mapped data would allow one to
restart their pipeline at the variant calling stages rather than re-map the samples in any re-runs. In this case,
a mapped CRAM, potentially with compressing quality scores using native CRAM quality score compression or 
external tools like [Crumble](https://academic.oup.com/bioinformatics/article/35/2/337/5051198), probably 
makes the most sense.

However, there are a number of cases where keeping the raw, unmapped data makes the most sense. For example,
there are many analyses that may be performed that don't have a mapping stage. Also, some projects anticipate
users leveraging multiple reference genomes in which case storing the data mapped to one specific reference
might not make sense. For these projects, leveraging one of the tools above might be the most appropriate.