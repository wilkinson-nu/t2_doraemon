#!/bin/bash
#SBATCH --image=docker:wilkinsonnu/t2_doraemon:nuwro_v25.03.01
#SBATCH --account=m4045
#SBATCH --qos=shared
#SBATCH --constraint=cpu
#SBATCH --time=1440
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --mem=4GB
#SBATCH --module=none

## These change for each job
THIS_SEED=__THIS_SEED__
FILE_NUM=__FILE_NUM__
NU_PDG=__NU_PDG__
OUTDIR=__OUTDIR__
TARG=__TARG__
ROOT_NAME=__ROOT_NAME__
OUTFILE=__OUTFILE__

E_MONO=__E_MONO__
FLUX_FILE=__FLUX_FILE__
FLUX_HIST=__FLUX_HIST__

INPUTS_DIR=${PWD}/MC_inputs

## Where to temporarily save files
TEMPDIR=${SCRATCH}/${OUTFILE/.root/}_${THIS_SEED}

echo "Moving to SCRATCH: ${TEMPDIR}"
mkdir ${TEMPDIR}
cd ${TEMPDIR}

## Special target names for NuWro...
SHORT_TARG=""
if [[ $TARG == "1000080160[0.8889],1000010010[0.1111]" ]]; then
    SHORT_TARG="H2O"
elif [[ $TARG == "1000060120[0.9231],1000010010[0.0769]" ]]; then
    SHORT_TARG="CH"
elif [[ $TARG == "1000180400[1.00]" ]]; then
    SHORT_TARG="Ar"
elif [[ $TARG == "1000060120[0.85714],1000010010[0.14286]" ]]; then
    SHORT_TARG="CH2"
elif [[ $TARG == "1000060120[1.00]" ]]; then
    SHORT_TARG="C"
elif [[ $TARG == "1000010010[1.00]" ]]; then
    SHORT_TARG="proton"
elif [[ $TARG == "1000000010[1.00]" ]];	then
    SHORT_TARG="neutron"
else
    echo "Don't know how to parse target ${TARG}... exiting..."
    exit
fi

if [ -n "${E_MONO}" ]; then
    echo "Monoenergetic mode: E=${E_MONO}"
    INCARD=generic_NUWROv25.3.1_MONO.params
    cp ${INPUTS_DIR}/${INCARD} .
    sed -i "s/_E_MONO_/${E_MONO}/g" ${INCARD}
    PREPARE_FLUX_ARGS=""
else
    echo "Complex flux mode: ${FLUX_FILE}, ${FLUX_HIST}"
    cp ${INPUTS_DIR}/${FLUX_FILE} .
    INCARD=generic_NUWROv25.3.1.params
    cp ${INPUTS_DIR}/${INCARD} .
    sed -i "s/_FLUX_FILE_/${FLUX_FILE}/g" ${INCARD}
    sed -i "s/_FLUX_HIST_/${FLUX_HIST}/g" ${INCARD}
    PREPARE_FLUX_ARGS="-F ${FLUX_FILE},${FLUX_HIST},${NU_PDG}"
fi

sed -i "s/_NU_PDG_/${NU_PDG}/g" ${INCARD}
sed -i "s/_THIS_SEED_/${THIS_SEED}/g" ${INCARD}
sed -i "s/_SHORT_TARG_/${SHORT_TARG}/g" ${INCARD}

echo "Running nuwro..."
shifter nuwro -i ${INCARD} -o ${OUTFILE}

echo "Running PrepareNuWroEvents..."
shifter PrepareNuWroEvents ${OUTFILE} ${PREPARE_FLUX_ARGS}

echo "Running nuisflat..."
shifter nuisflat -f GenericVectors -i NuWro:${OUTFILE} -o ${OUTFILE/.root/_NUISFLAT.root} -q "nuisflat_SaveSignalFlags=false"

echo "Converting to hdf5..."
cp ${INPUTS_DIR}/convert_to_hdf5.py .
shifter python convert_to_hdf5.py ${OUTFILE/.root/_NUISFLAT.root} ${OUTFILE/.root/_NUISFLAT.h5}
echo "Complete"

## Copy back the important files
cp ${TEMPDIR}/${OUTFILE/.root/_NUISFLAT.root} ${OUTDIR}/.
cp ${TEMPDIR}/${OUTFILE/.root/_NUISFLAT.h5} ${OUTDIR}/.

## Clean up
rm -r ${TEMPDIR}
