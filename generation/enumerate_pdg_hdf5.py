import h5py
import numpy as np
import matplotlib.pyplot as plt
import sys
from glob import glob

def enumerate_pdgs(hdf5_file):

    print(hdf5_file)
    
    ## Load and concatenate across all files
    pdg_list = []
    
    with h5py.File(hdf5_file, "r") as f:
        pt_grp = f["particles"]
        pdg_list = pt_grp["pdg"][:]

    unique_pdgs = np.unique(pdg_list)

    print("Found", len(unique_pdgs), "unique pdg codes:")
    print(unique_pdgs)

        
if __name__ == "__main__":
    enumerate_pdgs("/global/cfs/cdirs/doraemon/www/T2/DUNE_FHC_numu_Ar40_osc_GENIEv3_G18_10a_02_11a_10M.h5")
    enumerate_pdgs("/global/cfs/cdirs/doraemon/www/T2/DUNE_FHC_numu_Ar40_osc_GENIEv3_G18_10b_02_11a_10M.h5")
    enumerate_pdgs("/global/cfs/cdirs/doraemon/www/T2/DUNE_FHC_numu_Ar40_osc_NUWROv25.3.1_10M.h5")
    enumerate_pdgs("/global/cfs/cdirs/doraemon/www/T2/DUNE_FHC_numu_Ar40_osc_NEUT580_10M.h5")
