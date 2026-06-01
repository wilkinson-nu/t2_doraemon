#!/bin/bash
#SBATCH --image=docker:wilkinsonnu/t2_doraemon:genie_v3.6.2
#SBATCH --account=m4045
#SBATCH --qos=shared
#SBATCH --constraint=cpu
#SBATCH --time=1440
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --mem=4GB

## These change for each job
THIS_SEED=__THIS_SEED__
FILE_NUM=__FILE_NUM__
NU_PDG=__NU_PDG__
OUTDIR=__OUTDIR__
TARG=__TARG__
ROOT_NAME=__ROOT_NAME__
OUTFILE=__OUTFILE__

## Flux mode: set E_MONO for monoenergetic, or FLUX_FILE+FLUX_HIST+E_MIN+E_MAX for complex flux
E_MONO=__E_MONO__
E_MIN=__E_MIN__
E_MAX=__E_MAX__
FLUX_FILE=__FLUX_FILE__
FLUX_HIST=__FLUX_HIST__

## These are fixed
TUNE=G18_10b_02_11a
NEVENTS=1000000
INPUTS_DIR=${PWD}/MC_inputs

## Where to temporarily save files
TEMPDIR=${SCRATCH}/${OUTFILE/.root/}_${THIS_SEED}

echo "Moving to SCRATCH: ${TEMPDIR}"
mkdir ${TEMPDIR}
cd ${TEMPDIR}

if [ -n "${E_MONO}" ]; then
    echo "Monoenergetic mode: E=${E_MONO}"
    GEVGEN_FLUX_ARGS="-e ${E_MONO}"
    PREPARE_FLUX_ARGS="-m ${E_MONO}"
else
    echo "Complex flux mode: ${FLUX_FILE} [${FLUX_HIST}], E=${E_MIN},${E_MAX}"
    cp ${INPUTS_DIR}/${FLUX_FILE} .
    GEVGEN_FLUX_ARGS="-f ${FLUX_FILE},${FLUX_HIST} -e ${E_MIN},${E_MAX}"
    PREPARE_FLUX_ARGS="-f ${FLUX_FILE},${FLUX_HIST}"
fi

## Copy over the splines
cp ${INPUTS_DIR}/${TUNE}_splines.xml.gz .

echo "Starting gevgen..."
shifter gevgen -n ${NEVENTS} -t ${TARG} -p ${NU_PDG} \
	--event-generator-list CC \
	--cross-sections ${TUNE}_splines.xml.gz \
	--tune ${TUNE} --seed ${THIS_SEED} \
	${GEVGEN_FLUX_ARGS} -o ${OUTFILE}

echo "Running PrepareGENIE..."
shifter PrepareGENIE -i $OUTFILE ${PREPARE_FLUX_ARGS} -t $TARG -o ${OUTFILE/.root/_NUIS.root}
 
echo "Running nuisflat..."
shifter nuisflat -f GenericVectors -i GENIE:${OUTFILE/.root/_NUIS.root} -o ${OUTFILE/.root/_NUISFLAT.root} -q "nuisflat_SaveSignalFlags=false"

echo "Converting to hdf5..."
cp ${INPUTS_DIR}/convert_to_hdf5.py .
shifter python convert_to_hdf5.py ${OUTFILE/.root/_NUISFLAT.root} ${OUTFILE/.root/_NUISFLAT.h5}
echo "Complete"

## Copy back the important files
cp ${TEMPDIR}/${OUTFILE/.root/_NUISFLAT.root} ${OUTDIR}/.
cp ${TEMPDIR}/${OUTFILE/.root/_NUISFLAT.h5} ${OUTDIR}/.

## Clean up
rm -r ${TEMPDIR}

