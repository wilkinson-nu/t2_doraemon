FROM debian:11-slim

ARG NCORES=4
ENV GEN_DIR=/opt/generators

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gfortran cmake git wget \
    libboost-all-dev libclhep-dev \
    python3 python3-pip \
    python3-numpy python3-dev \
    zlib1g-dev libx11-dev libssl-dev libpng-dev libjpeg-dev \
    liblzma-dev libxxhash-dev libxpm-dev libxft-dev libxext-dev \
    libgsl-dev liblz4-dev libgif-dev libtiff-dev libxml2-dev \
    libfftw3-dev libblas-dev ca-certificates \
    libxerces-c-dev libhdf5-dev \
    libglu1-mesa-dev libgl1-mesa-dev libgl1-mesa-dri \
    libosmesa6 libosmesa6-dev \
    libglew-dev freeglut3-dev libyaml-cpp-dev \
    && update-ca-certificates

# Build dir
WORKDIR ${GEN_DIR}

# Get PYTHIA6
RUN wget --no-check-certificate http://root.cern.ch/download/pythia6.tar.gz && \
    tar -xzf pythia6.tar.gz && rm pythia6.tar.gz && \
    wget --no-check-certificate https://pythia.org/download/pythia6/pythia6428.f && \
    mv pythia6428.f pythia6/pythia6428.f && rm pythia6/pythia6416.f

# Build PYTHIA6
WORKDIR ${GEN_DIR}/pythia6
RUN sed -i "s/int /extern int /g" pythia6_common_address.c && \
    sed -i "s/char /extern char /g" pythia6_common_address.c && \
    sed -i "s/extern int pyuppr/int pyuppr/g" pythia6_common_address.c && \
    sed -i "s/m64/march=native/g" makePythia6.linuxx8664 && \
    ./makePythia6.linuxx8664

ENV PYTHIA6=${GEN_DIR}/pythia6
ENV LD_LIBRARY_PATH=${PYTHIA6}:${LD_LIBRARY_PATH}

# Get ROOT
WORKDIR ${GEN_DIR}
RUN git clone -b v6-24-06 --depth 1 --single-branch https://github.com/root-project/root.git root

# Build ROOT
WORKDIR ${GEN_DIR}/root/install
RUN cmake -DPYTHIA6_LIBRARY=${PYTHIA6}/libPythia6.so \
          -DCMAKE_CXX_STANDARD=17 \
	  -Dpythia6=ON -Dminuit2=ON -Dmathmore=ON -Dgdml=ON \
          -Ddavix=OFF -Dfitsio=OFF -Dgfal=OFF -Dcastor=OFF \
          -Dclad=OFF -Dhttp=OFF -Droot7=OFF -Dwebgui=OFF \
          -Dxrootd=OFF -Dmlp=OFF -Dmysql=OFF -Doracle=OFF \
          -Dpgsql=OFF -Droofit=OFF -Dspectrum=OFF -Dsqlite=OFF \
          -Ddataframe=OFF -Dimt=OFF -Dtmva=OFF -Dvdt=OFF \
          -Dtmva-cpu=OFF -Dtmva-pymva=OFF -Dssl=OFF -Dcudnn=OFF \
	  -Deve=ON -Dx11=ON -Dopengl=ON -Dbuiltin_ftgl=ON -Dbuiltin_gl2ps=ON \
          -DPYTHON_EXECUTABLE=/usr/bin/python3 -Dpython3=ON \
          ../ && \
    make -j${NCORES} && make install

## Set ROOT environment
ENV ROOTSYS=${GEN_DIR}/root/install
ENV PATH=${ROOTSYS}/bin:${PATH}
ENV LD_LIBRARY_PATH=${ROOTSYS}/lib:${LD_LIBRARY_PATH}
