FROM continuumio/miniconda3

RUN apt-get update && \
    apt-get install -y gcc g++ zlib1g-dev libbz2-dev liblzma-dev build-essential git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy tool definitions so make_env.py can derive the conda environment
COPY tools/ /app/tools/
COPY scripts/ /app/scripts/
COPY make_env.py /app/

# Generate environment.yml from tool definitions and apply it
RUN python make_env.py > /tmp/environment.yml && \
    conda env update --name base -f /tmp/environment.yml && \
    conda clean -afy

# Run any source-build install steps declared in tool files
RUN python make_env.py --install-steps > /tmp/install_steps.sh && \
    bash /tmp/install_steps.sh

# Petagene (optional — proprietary installer, requires a license from petagene.com)
# To include Petagene, copy your .deb into docker/ before building, then uncomment:
# ADD petasuite-cloud-edition_1.2.6p6_amd64.deb /petasuite-cloud-edition_1.2.6p6_amd64.deb
# RUN dpkg -i /petasuite-cloud-edition_1.2.6p6_amd64.deb && \
#     rm /petasuite-cloud-edition_1.2.6p6_amd64.deb && \
#     petasuite_install_corpus human

COPY benchmarks/ /app/benchmarks/
COPY report/ /app/report/
COPY run_benchmark.py /app/

ENTRYPOINT ["python", "/app/run_benchmark.py"]
