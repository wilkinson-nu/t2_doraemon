FROM wilkinsonnu/t2_doraemon:root_v6.24.06 AS builder

ARG NCORES=4
ENV GEN_DIR=/opt/generators

# Install build deps
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    libxm4 libxt-dev libxaw7-dev libmotif-dev zip unzip autoconf libtool automake

## Copy in the NEUT tarball
COPY neut-5.8.0.zip ${GEN_DIR}/neut-5.8.0.zip

## Unpack and build NEUT
WORKDIR ${GEN_DIR}
RUN unzip neut-5.8.0.zip && \
    mv neut-5.8.0 neut && \
    rm neut-5.8.0.zip && \
    cd neut && \
    cd src && autoreconf -i --force && cd .. && \
    mkdir build && cd build && \
    ../src/configure --prefix=$(readlink -f Linux) --enable-builtin-cernlib && \
    make -j${NCORES} && make install

ENV NEUT_ROOT=${GEN_DIR}/neut
ENV NEUT=${GEN_DIR}/neut/build/Linux
ENV NEUT_CARDS=${NEUT}/share/neut/Cards
ENV NEUT_CRSPATH=${NEUT}/share/neut/crsdat
ENV PATH=${NEUT}/bin:${PATH}
ENV LD_LIBRARY_PATH=${NEUT}/lib:${LD_LIBRARY_PATH}
ENV PKG_CONFIG_PATH=${NEUT}:${PKG_CONFIG_PATH}

## Get and build NUISANCE (using a fixed commit for reproducibility)
WORKDIR ${GEN_DIR}
RUN git clone https://github.com/NUISANCEMC/nuisance.git NUISANCE && \
    cd NUISANCE && git checkout c596652 && \
    mkdir build && cd build && \
    cmake -DCMAKE_CXX_STANDARD=17 \
          -DNEUT_ENABLED=1 \
          -DREWEIGHT_ENABLED=0 \
          -DHepMC3_ENABLED=0 \
          -DProb3plusplus_ENABLED=0 \
          -Dnusystematics_ENABLED=0 \
          ../ && \
    make -j${NCORES} && make install

ENV NUISANCE=${GEN_DIR}/NUISANCE
ENV PATH=${NUISANCE}/build/Linux/bin:${PATH}
ENV LD_LIBRARY_PATH=${NUISANCE}/build/Linux/lib:${LD_LIBRARY_PATH}

# ---------- Runtime stage ----------
FROM debian:11-slim

ENV GEN_DIR=/opt/generators

# Runtime deps only (strip compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python-is-python3 \
    liblzma5 \
    libxxhash0 \
    liblz4-1 \
    libpng16-16 \
    libfreetype6 \
    libgfortran5 \
    libbrotli1 \
    libquadmath0 \
    libstdc++-10-dev \
    libxpm4 \
    libxext6 \    
    && rm -rf /var/lib/apt/lists/*

## PYTHIA6
ENV PYTHIA6=${GEN_DIR}/pythia6
COPY --from=builder ${PYTHIA6} ${PYTHIA6}
ENV LD_LIBRARY_PATH=${PYTHIA6}:${LD_LIBRARY_PATH}

## ROOT
ENV ROOTSYS=${GEN_DIR}/root/install
COPY --from=builder ${ROOTSYS} ${ROOTSYS}
ENV PATH=${ROOTSYS}/bin:${PATH}
ENV LD_LIBRARY_PATH=${ROOTSYS}/lib:${LD_LIBRARY_PATH}
ENV PYTHONPATH=${ROOTSYS}/lib:${PYTHONPATH}

## NEUT
ENV NEUT_ROOT=${GEN_DIR}/neut
ENV NEUT=${GEN_DIR}/neut/build/Linux
COPY --from=builder ${NEUT} ${NEUT}
ENV NEUT_CARDS=${NEUT}/share/neut/Cards
ENV NEUT_CRSPATH=${NEUT}/share/neut/crsdat
ENV PATH=${NEUT}/bin:${PATH}
ENV LD_LIBRARY_PATH=${NEUT}/lib:${LD_LIBRARY_PATH}

## NUISANCE
ENV NUISANCE=${GEN_DIR}/NUISANCE/build
COPY --from=builder ${NUISANCE} ${NUISANCE}
ENV PATH=${NUISANCE}/Linux/bin:${PATH}
ENV LD_LIBRARY_PATH=${NUISANCE}/Linux/lib:${LD_LIBRARY_PATH}

## Python installs
RUN pip install --no-cache-dir numpy h5py matplotlib