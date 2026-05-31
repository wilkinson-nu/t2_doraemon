FROM wilkinsonnu/t2_doraemon:root_v6.24.06 AS builder

ARG NCORES=4
ENV GEN_DIR=/opt/generators

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python-is-python3 liblog4cpp5-dev

## Sort out LHAPDF
WORKDIR ${GEN_DIR}/LHAPDF
RUN wget https://lhapdf.hepforge.org/downloads/LHAPDF-6.5.1.tar.gz && \
    tar xzf LHAPDF-6.5.1.tar.gz && \
    rm LHAPDF-6.5.1.tar.gz && cd LHAPDF-6.5.1 && \
    ./configure --prefix=${PWD}/../LHAPDF-6.5.1_build && \
    make -j ${NCORES} && make install
    
ENV LHAPDF=${GEN_DIR}/LHAPDF/LHAPDF-6.5.1_build
ENV LD_LIBRARY_PATH=${LHAPDF}/lib:${LD_LIBRARY_PATH}
ENV PATH=${LHAPDF}/bin:${PATH}
ENV LHAPATH=${LHAPDF}/share/LHAPDF

## Setup the GENIE paths
ENV GENIE_VERSION=R-3_06_02
ENV GENIE=${GEN_DIR}/GENIE/${GENIE_VERSION}
ENV LHAPDF_LIB=${LHAPDF}/lib
ENV LHAPDF_INC=${LHAPDF}/include

## Get the GENIE code
WORKDIR ${GEN_DIR}/GENIE
RUN git clone -b ${GENIE_VERSION} --depth 1 --single-branch https://github.com/GENIE-MC/Generator.git ${GEN_DIR}/GENIE/${GENIE_VERSION} && \    
    cd ${GENIE} && \
    sed -i 's/g77/gfortran/g' src/make/Make.include && \
    ./configure --enable-debug \
    		--enable-fnal \
    		--enable-rwght \
    		--enable-lhapdf6 \
		--disable-lhapdf5 \
    		--disable-apfel && \
    make -j${NCORES} && make install
    
ENV PATH=$GENIE/bin:${PATH}
ENV LD_LIBRARY_PATH=$GENIE/lib:$LD_LIBRARY_PATH
    
## Reduce GENIE messaging output when it runs
RUN cp ${GENIE}/config/Messenger_whisper.xml ${GENIE}/config/Messenger.xml && \
    sed -i '$ d' ${GENIE}/config/Messenger.xml && \
    echo '  <priority msgstream="ResonanceDecay">      FATAL </priority>' >> ${GENIE}/config/Messenger.xml && \
    echo '  <priority msgstream="Pythia6Decay">        FATAL </priority>' >> ${GENIE}/config/Messenger.xml && \
    echo '  <priority msgstream="INukeNucleonCorr">    FATAL </priority>' >> ${GENIE}/config/Messenger.xml && \
    echo '  <priority msgstream="gevgen_fnal">         FATAL </priority>' >> ${GENIE}/config/Messenger.xml && \
    echo '</messenger_config>' >> ${GENIE}/config/Messenger.xml

## Get and build NUISANCE (using a fixed commit for reproducibility)
WORKDIR ${GEN_DIR}
RUN git clone https://github.com/NUISANCEMC/nuisance.git NUISANCE && \
    cd NUISANCE && git checkout c596652 && \
    mkdir build && cd build && \
    cmake -DCMAKE_CXX_STANDARD=17 \
          -DGENIE_ENABLED=1 \
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
    libxml2 \
    liblog4cpp5v5 \
    libgsl25 \
    liblzma5 \
    libxxhash0 \
    liblz4-1 \
    libpng16-16 \
    libfreetype6 \
    libgfortran5 \
    libicu67 \
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

## LHAPDF
ENV LHAPDF=${GEN_DIR}/LHAPDF/LHAPDF-6.5.1_build
COPY --from=builder ${LHAPDF} ${LHAPDF}
ENV LD_LIBRARY_PATH=${LHAPDF}/lib:${LD_LIBRARY_PATH}
ENV PATH=${LHAPDF}/bin:${PATH}
ENV LHAPATH=${LHAPDF}/share/LHAPDF

## GENIE
ENV GENIE_VERSION=R-3_06_02
ENV GENIE=${GEN_DIR}/GENIE/${GENIE_VERSION}
COPY --from=builder ${GENIE} ${GENIE}
ENV PATH=$GENIE/bin:${PATH}
ENV LD_LIBRARY_PATH=$GENIE/lib:$LD_LIBRARY_PATH

## NUISANCE
ENV NUISANCE=${GEN_DIR}/NUISANCE/build
COPY --from=builder ${NUISANCE} ${NUISANCE}
ENV PATH=${NUISANCE}/Linux/bin:${PATH}
ENV LD_LIBRARY_PATH=${NUISANCE}/Linux/lib:${LD_LIBRARY_PATH}

## Python installs
RUN pip install --no-cache-dir numpy h5py matplotlib
