#!/bin/bash

## Can be used to arbitrarily pile on more
FIRST_JOB=0
LAST_JOB=10

OUTDIR_ROOT=${CFS}/dune/users/cwilk/t2_doraemon

## Generate for numu only
NU_PDG=14
TARG=1000180400[1.00]
FLUX_FILE=DUNE_FHC_NuFit5NO_trunc.root
E_MIN=0.25
E_MAX=8
OUTNAME_ROOT=DUNE_FHC_numu_Ar40

## Loop over templates
for GENERATOR in GENIEv3_G18_10a_02_11a GENIEv3_G18_10b_02_11a \
		 NEUT580 NUWROv25.3.1
do

    OUTDIR=${OUTDIR_ROOT}/${GENERATOR}
    if [ ! -d "${OUTDIR}" ]; then
	mkdir -p ${OUTDIR}
    fi
    TEMPLATE=batch_${GENERATOR}_TEMPLATE.sh
    
    for FLUX in osc unosc; do
	
	for JOB in $(seq ${FIRST_JOB} ${LAST_JOB}); do
	    
	    printf -v PADJOB "%03d" $JOB
	    
	    OUTFILE=${OUTNAME_ROOT}_${FLUX}_${GENERATOR}_1M_${PADJOB}.root
	    
	    ## Check if file has already been processed
	    if [[ -f "${OUTDIR}/${OUTFILE/.root/_NUISFLAT.root}" && \
		     -f "${OUTDIR}/${OUTFILE/.root/_NUISFLAT.h5}" ]]; then
                continue
	    fi
	    echo "Processing ${OUTFILE}"
	    
	    ## Copy the template
	    THIS_TEMP=${OUTNAME_ROOT}_${FLUX}_${GENERATOR}_1M_${PADJOB}.sh
	    cp ${TEMPLATE} ${THIS_TEMP}
	    
	    ## Set everything important...
	    sed -i "s/__THIS_SEED__/${RANDOM}/g" ${THIS_TEMP}
	    sed -i "s/__FILE_NUM__/${PADJOB}/g" ${THIS_TEMP}
	    sed -i "s/__NU_PDG__/${NU_PDG}/g" ${THIS_TEMP}
	    sed -i "s/__OUTDIR__/${OUTDIR//\//\\/}/g" ${THIS_TEMP}
	    sed -i "s/__OUTFILE__/${OUTFILE}/g" ${THIS_TEMP}
	    sed -i "s/__FLUX_FILE__/${FLUX_FILE}/g" ${THIS_TEMP}
	    sed -i "s/__FLUX_HIST__/${FLUX}/g" ${THIS_TEMP}
            sed -i "s/__TARG__/${TARG}/g" ${THIS_TEMP}
            sed -i "s/__ROOT_NAME__/${OUTNAME_ROOT}/g" ${THIS_TEMP}
	    sed -i "s/__E_MAX__/${E_MAX}/g" ${THIS_TEMP}
            sed -i "s/__E_MIN__/${E_MIN}/g" ${THIS_TEMP}
	    sed -i "s/__E_MONO__//g" ${THIS_TEMP}
	    echo "Submitting ${THIS_TEMP}"
	    
	    ## Submit the template
	    sbatch ${THIS_TEMP}
	    
	    ## No need to delete, so done
	    rm ${THIS_TEMP}
	done
    done
done
