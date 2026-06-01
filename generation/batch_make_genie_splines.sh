#!/bin/bash

## Where to save the output
OUTDIR_ROOT=${PWD}/MC_inputs

## Need to start with free nucleon XSECS
# target_arr=( 1000000010 1000010010 )

## Switch to nuclear XSECs once the nucleon XSECs have been made
## Add splines afterwards with:
# gspladd -d ${tune}_splines -o ${tune}_splines.xml

target_arr=( 1000060120 1000080160 1000180400 )
flavor_arr=( 14 -14 12 -12 16 -16 )

tune_arr=( G18_10a_02_11a G18_10b_02_11a )

## Spline parameters
nknots=250
e_max=100

## Loop over tunes
for tune in "${tune_arr[@]}"; do

    ## Splines should be collected by tune
    OUTDIR=${OUTDIR_ROOT}/${tune}_splines
    if [ ! -d "${OUTDIR}" ]; then
        mkdir -p ${OUTDIR}
    fi
    
    ## Loop over flavours
    for flav in "${flavor_arr[@]}"; do

	## Loop over targets
	for targ in "${target_arr[@]}"; do

	    ## The spline file
	    outFileName=${tune}_${flav}_${targ}_spline.xml
	    echo "Processing ${outFileName}"

	    jobScript=${outFileName/.xml/.sh}
	    
	    ## Start to make the batch file
	    echo "#!/bin/bash" > ${jobScript}
	    echo "#SBATCH --image=docker:wilkinsonnu/t2_doraemon:genie_v3.6.2" >> ${jobScript}
	    echo "#SBATCH --qos=shared" >> ${jobScript}
	    echo "#SBATCH --constraint=cpu" >> ${jobScript}
	    echo "#SBATCH --time=720" >> ${jobScript}
	    echo "#SBATCH --nodes=1" >> ${jobScript}
	    echo "#SBATCH --ntasks=1" >> ${jobScript}
	    echo "#SBATCH --mem=4GB" >> ${jobScript}

	    ## Do this in the relevant area
	    echo "cd ${OUTDIR}" >> ${jobScript}
	    
	    ## This is the real business (for free nucleons)
	    #echo "shifter gmkspl -p ${flav} -t ${targ} -n ${nknots} -e ${e_max} -o ${outFileName} --tune ${tune}" >> ${jobScript}

	    ## For nuclei (requires free nucleon input)
	    echo "shifter gmkspl -p ${flav} -t ${targ} -n ${nknots} -e ${e_max} -o ${outFileName} --tune ${tune} \
	    --input-cross-sections ${OUTDIR_ROOT}/${tune}_splines.xml" >> ${jobScript}
	    
	    ## Submit and delete
	    sbatch ${jobScript}
	    rm ${jobScript}
	done
    done
done
