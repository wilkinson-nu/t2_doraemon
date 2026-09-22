import sys
import shutil
import argparse
from pathlib import Path
from glob import glob

import h5py
import numpy as np

# Must match the production script
SCALAR_FIELDS = ["Enu", "W", "Q2",
                 "q0", "q3", "nfsp"]
VLEN_FIELDS = ["px", "py", "pz", "E", "pdg"]

def merge_hdf5(input_files, output_file, tree_name="FlatTree_VARS"):
    """Concatenate several repacked HDF5 files into one, fixing offsets/metadata."""

    # --- First pass: collect sizes so we can preallocate ---
    per_file = []
    total_events = 0
    total_particles = 0

    for path in input_files:
        with h5py.File(path, "r") as hf:
            n_ev = int(hf.attrs["n_events"])
            n_pt = int(hf.attrs["n_particles"])
            # sanity check against the actual stored data
            stored_ev = hf["events"]["nfsp"].shape[0]
            stored_pt = hf["particles"]["px"].shape[0]
            if stored_ev != n_ev:
                raise ValueError(f"{path}: n_events attr ({n_ev}) != stored events ({stored_ev})")
            if stored_pt != n_pt:
                raise ValueError(f"{path}: n_particles attr ({n_pt}) != stored particles ({stored_pt})")

        per_file.append({"path": path, "n_events": n_ev, "n_particles": n_pt})
        total_events += n_ev
        total_particles += n_pt

    print(f"Merging {len(input_files)} files: "
          f"{total_events} events, {total_particles} particles")

    # Determine dtypes from the first file
    with h5py.File(input_files[0], "r") as hf:
        scalar_dtypes = {f: hf["events"][f].dtype for f in SCALAR_FIELDS}
        vlen_dtypes = {f: hf["particles"][f].dtype for f in VLEN_FIELDS}

    # --- Write output, streaming file-by-file to keep memory low ---
    with h5py.File(output_file, "w") as out:
        out.attrs["n_events"] = total_events
        out.attrs["n_particles"] = total_particles
        out.attrs["tree_name"] = tree_name
        out.attrs["n_sources"] = len(input_files)
        
        ev_grp = out.create_group("events")
        for f in SCALAR_FIELDS:
            ev_grp.create_dataset(
                f, shape=(total_events,), dtype=scalar_dtypes[f],
                compression="gzip", compression_opts=4)

        pt_grp = out.create_group("particles")
        pt_grp.attrs["description"] = \
            "Flat concatenated stack; use offsets to index events"
        for f in VLEN_FIELDS:
            pt_grp.create_dataset(
                f, shape=(total_particles,), dtype=vlen_dtypes[f],
                compression="gzip", compression_opts=4)
        # offsets has n_events + 1 entries
        offsets_ds = pt_grp.create_dataset(
            "offsets", shape=(total_events + 1,), dtype=np.int64,
            compression="gzip")

        # Metadata about the merged sources
        meta_grp = out.create_group("sources")
        src_names = []
        src_nev = []
        src_npt = []
        src_ev_start = []
        src_pt_start = []

        ev_cursor = 0
        pt_cursor = 0
        offsets_ds[0] = 0

        for info in per_file:
            path = info["path"]
            n_ev = info["n_events"]
            n_pt = info["n_particles"]

            with h5py.File(path, "r") as hf:
                # scalar events
                for f in SCALAR_FIELDS:
                    ev_grp[f][ev_cursor:ev_cursor + n_ev] = hf["events"][f][:]

                # particle stack
                for f in VLEN_FIELDS:
                    pt_grp[f][pt_cursor:pt_cursor + n_pt] = \
                        hf["particles"][f][:]

                # rebuild global offsets: local offsets shifted by pt_cursor,
                # skipping the leading 0 of each file's offsets array
                local_offsets = hf["particles"]["offsets"][:]
                offsets_ds[ev_cursor + 1:ev_cursor + n_ev + 1] = \
                    local_offsets[1:] + pt_cursor

            src_names.append(str(path))
            src_nev.append(n_ev)
            src_npt.append(n_pt)
            src_ev_start.append(ev_cursor)
            src_pt_start.append(pt_cursor)

            ev_cursor += n_ev
            pt_cursor += n_pt
            print(f"  Merged {path}: {n_ev} events, {n_pt} particles")

        # sanity check on the offsets
        if offsets_ds[-1] != total_particles:
            raise RuntimeError(
                f"offsets end ({offsets_ds[-1]}) != total particles "
                f"({total_particles}); merge is inconsistent")

        meta_grp.create_dataset(
            "source_file",
            data=np.array(src_names, dtype=h5py.string_dtype()))
        meta_grp.create_dataset("n_events", data=np.array(src_nev, dtype=np.int64))
        meta_grp.create_dataset("n_particles", data=np.array(src_npt, dtype=np.int64))
        meta_grp.create_dataset("event_start", data=np.array(src_ev_start, dtype=np.int64))
        meta_grp.create_dataset("particle_start", data=np.array(src_pt_start, dtype=np.int64))

    print(f"Written merged file to {output_file}")



if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Repack open-data-challenge HDF5 files.")
    parser.add_argument("--input_files", nargs="+", required=True)
    parser.add_argument("--output_dir", type=Path, default=None, required=True)
    parser.add_argument("--output_name", default=None, required=True)
    args = parser.parse_args()

    ## Report on what's going on
    for arg in vars(args): print(arg, getattr(args, arg))

    ## Check that the output directory exists
    if not args.output_dir.is_dir():
        sys.exit(f"Output directory does not exist: {args.output_dir}")

    ## Get the list of files to merge
    files_to_merge = sorted(
        {f for pattern in args.input_files for f in glob(pattern)})
    
    ## Merge into a temporary location first, then move into processed_dir
    merged_tmp = args.output_dir / (args.output_name + ".tmp")
    merge_hdf5(files_to_merge, merged_tmp, max_events)

    ## Copy to the final destination
    merged_dest = args.output_dir / args.output_name
    shutil.move(str(merged_tmp), str(merged_dest))
    print(f"Merged file placed at {merged_dest}")

