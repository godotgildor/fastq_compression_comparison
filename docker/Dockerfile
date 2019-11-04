FROM ubuntu:18.04 as build
ENV SAMTOOLS_VERSION 1.9
ENV PICARD_VERSION 2.21.1
ENV CRUMBLE_VERSION 0.8.3

RUN apt-get update && apt-get install -y gcc g++ wget ncurses-dev zlib1g-dev libbz2-dev liblzma-dev build-essential git cmake
RUN wget https://github.com/samtools/samtools/releases/download/${SAMTOOLS_VERSION}/samtools-${SAMTOOLS_VERSION}.tar.bz2 && \
    tar jxvf samtools-${SAMTOOLS_VERSION}.tar.bz2 && \
    cd samtools-${SAMTOOLS_VERSION} && ./configure --prefix=/samtools && make -j `nproc` && make install
RUN wget https://github.com/broadinstitute/picard/releases/download/${PICARD_VERSION}/picard.jar && \
    mkdir -p /picard && cp picard.jar /picard/
RUN git clone https://github.com/jkbonfield/fqzcomp.git && \
    cd fqzcomp && make -j `nproc` 
RUN git clone https://github.com/refresh-bio/FaStore.git && \
    cd FaStore && make -j `nproc` && chmod 755 scripts/*.sh
RUN git clone https://github.com/shubhamchandak94/Spring.git && \
    cd Spring && mkdir build && cd build && cmake ../ && make -j `nproc`
RUN wget https://github.com/jkbonfield/crumble/releases/download/v0.8.3/crumble-${CRUMBLE_VERSION}.tar.gz && \
    cd /samtools-${SAMTOOLS_VERSION}/htslib-${SAMTOOLS_VERSION} && ./configure && make -j `nproc` && make install && \
    cd / && tar zxvf crumble-${CRUMBLE_VERSION}.tar.gz && mv crumble-${CRUMBLE_VERSION} /crumble && cd /crumble && \
    ./configure --with-htslib=/samtools-${SAMTOOLS_VERSION}/htslib-${SAMTOOLS_VERSION} && make -j `nproc`

#########################################################################################################
# Final image
FROM ubuntu:18.04
RUN apt-get update && apt-get install -y python3 openjdk-11-jre-headless libgomp1 && \
    apt-get autoclean && apt-get autoremove && rm -rf /var/lib/apt/lists/*

COPY --from=build /samtools/bin/ /samtools/bin/
COPY --from=build /picard/ /picard/
COPY --from=build /fqzcomp/fqzcomp /usr/local/bin/fqzcomp
COPY --from=build /FaStore/bin /FaStore/scripts
COPY --from=build /FaStore/scripts /FaStore/scripts
RUN sed -i 's/FASTORE_BIN=.\//FASTORE_BIN=\/FaStore\/scripts\//g' /FaStore/scripts/*.sh
RUN sed -i 's/FASTORE_REBIN=.\//FASTORE_REBIN=\/FaStore\/scripts\//g' /FaStore/scripts/*.sh
RUN sed -i 's/FASTORE_PACK=.\//FASTORE_PACK=\/FaStore\/scripts\//g' /FaStore/scripts/*.sh
COPY --from=build /Spring/build/spring /Spring/build/spring
COPY --from=build /crumble/crumble /usr/local/bin/crumble
COPY --from=build /usr/local/lib /usr/local/lib
ENV PATH="/samtools/bin:/FaStore/scripts:/Spring/build/:/usr/local/bin:${PATH}"
RUN /sbin/ldconfig -v
ADD compress_fastq /usr/local/bin 

ENTRYPOINT ["compress_fastq"]