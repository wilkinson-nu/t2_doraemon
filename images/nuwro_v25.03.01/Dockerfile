FROM wilkinsonnu/t2_doraemon:root_v6.24.06 AS builder

ARG NCORES=4
ENV GEN_DIR=/opt/generators

# Install build deps
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    libxml2-utils

## Symlink Pythia6 into ROOT lib dir as NuWro expects
RUN ln -s ${GEN_DIR}/pythia6/libPythia6.so ${ROOTSYS}/lib/libPythia6.so

## Get NuWro
WORKDIR ${GEN_DIR}
RUN git clone --depth 1 --branch remove-vla https://github.com/wilkinson-nu/nuwro nuwro && \
    cd nuwro && make -j${NCORES}

ENV NUWRO=${GEN_DIR}/nuwro
ENV PATH=${NUWRO}/bin:${PATH}
ENV PYTHIA6=${GEN_DIR}/pythia6
ENV ROOT_INCLUDE_PATH=${NUWRO}/src:${ROOT_INCLUDE_PATH}

## Get and build NUISANCE (using a fixed commit for reproducibility)
WORKDIR ${GEN_DIR}
RUN git clone https://github.com/NUISANCEMC/nuisance.git NUISANCE && \
    cd NUISANCE && git checkout c596652 && \
    mkdir build && cd build && \
    cmake -DCMAKE_CXX_STANDARD=17 \
          -DNuWro_ENABLED=1 \
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

## NuWro
ENV NUWRO=${GEN_DIR}/nuwro
COPY --from=builder ${NUWRO} ${NUWRO}
ENV PATH=${NUWRO}/bin:${PATH}

## NUISANCE
ENV NUISANCE=${GEN_DIR}/NUISANCE/build
COPY --from=builder ${NUISANCE} ${NUISANCE}
ENV PATH=${NUISANCE}/Linux/bin:${PATH}
ENV LD_LIBRARY_PATH=${NUISANCE}/Linux/lib:${LD_LIBRARY_PATH}

## Python installs
RUN pip install --no-cache-dir numpy h5py matplotlib
