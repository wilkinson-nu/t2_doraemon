import uproot
import h5py
import numpy as np
import awkward as ak
import sys
from glob import glob
import operator
from functools import reduce
import argparse
from collections import Counter
    
## Remove CC as uninteresting for the CC-only challenge datasets
## Also remove pdgnu and tgt as everything is numu -- argon
SCALAR_BRANCHES = {
    # "Mode":         ("mode",    np.int32  ),
    # "PDGnu":        ("pdg_nu",  np.int32  ),
    # "tgt":          ("pdg_tgt", np.int32  ),
    "Enu_true":     ("Enu",     np.float32),
    "W":            ("W",       np.float32),
    "Q2":           ("Q2",      np.float32),
    "q0":           ("q0",      np.float32),
    "q3":           ("q3",      np.float32),
    # "cc":           ("cc",      np.bool_  ),
    "nfsp":         ("nfsp",    np.int32  ),
}

VLEN_BRANCHES = {
    "px":  ("px",  np.float32),
    "py":  ("py",  np.float32),
    "pz":  ("pz",  np.float32),
    "E":   ("E",   np.float32),
    "pdg": ("pdg", np.int32  ),
}

## PDG codes for neutral kaons that should all be relabeled to 311
## The treatment between generators is really inconsistent, but the physics shouldn't be affected by this re-labelling
## (Geant4 would then pick mass eigenstates)
NEUTRAL_KAON_PDGS = (310, 130, 311, -311)

## Pick a maximum PDG value to include
## This is just used to remove nuclear remnants, which are uninteresting here, and not consistently included between (or indeed within) generators
PDG_MAX = int(1e8)

## Also veto any PDG code in the following list
## For now this is just to remove any outgoing neutrinos as uninteresting
PDG_VETO = (12, -12, 14, -14, 16, -16)

## Veto events which have PDGs outside this list at the final stage
ALLOWED_PDGS = (-3122, -2212, -2112, -321, -211, -13, -11, 11, 13, 22, 111, 211, 311, 321, 2112, 2212, 3122)


def convert_flattrees_to_hdf5(root_files,
                              hdf5_file,
                              tree_name="FlatTree_VARS",
                              max_events=None):
    if isinstance(root_files, str):
        root_files = [root_files]
    root_files = [f for pattern in root_files for f in sorted(glob(pattern))]
    if not root_files:
        raise FileNotFoundError("No files matched the given pattern(s)")

    print(f"Converting {len(root_files)} file(s)...")

    # --- First pass: read all data ---
    all_scalar_data = {root_name: [] for root_name in SCALAR_BRANCHES}
    all_vlen_data   = {root_name: [] for root_name in VLEN_BRANCHES}
    all_event_ok    = []
    bad_pdg_particles = Counter()
    bad_pdg_events    = Counter()
    file_metadata   = []
    event_cursor    = 0
    particle_cursor = 0

    for path in root_files:
        with uproot.open(path) as f:
            tree = f[tree_name]
            n_events = tree.num_entries

            scalar_data = tree.arrays(list(SCALAR_BRANCHES.keys()), library="np")
            vlen_data   = tree.arrays(list(VLEN_BRANCHES.keys()), library="ak")

            ## Mask PDG codes we don't want to retain and apply to all particle branches
            pdg = vlen_data["pdg"]
            veto = reduce(operator.or_, (pdg == v for v in PDG_VETO), ak.zeros_like(pdg, dtype=bool))
            keep = (np.abs(pdg) < PDG_MAX) & ~veto
            for root_name in VLEN_BRANCHES:
                vlen_data[root_name] = vlen_data[root_name][keep]

            ## Relabel all neutral kaon variants to 311
            pdg = vlen_data["pdg"]
            kaon_mask = ak.zeros_like(pdg, dtype=bool)
            for code in NEUTRAL_KAON_PDGS:
                kaon_mask = kaon_mask | (pdg == code)
            vlen_data["pdg"] = ak.where(kaon_mask, 311, pdg)

            ## Flag events where every particle has an allowed PDG (whole event is dropped later otherwise)
            pdg = vlen_data["pdg"]
            allowed = reduce(operator.or_, (pdg == a for a in ALLOWED_PDGS), ak.zeros_like(pdg, dtype=bool))
            all_event_ok.append(ak.to_numpy(ak.all(allowed, axis=1)))

            ## Tally disallowed PDGs (particle counts and number of events containing each)
            bad = pdg[~allowed]
            codes, counts = np.unique(ak.to_numpy(ak.flatten(bad)), return_counts=True)
            for code, n in zip(codes, counts):
                bad_pdg_particles[int(code)] += int(n)
                bad_pdg_events[int(code)]    += int(ak.sum(ak.any(bad == code, axis=1)))
            
            ## Recompute nfsp from the filtered structure so offsets stay valid.
            ## The original nfsp branch cannot be trusted
            nfsp = ak.to_numpy(ak.num(vlen_data["pdg"])).astype(np.int32)
            scalar_data["nfsp"] = nfsp
            n_particles = int(nfsp.sum())

            for root_name in SCALAR_BRANCHES:
                all_scalar_data[root_name].append(scalar_data[root_name])
            for root_name in VLEN_BRANCHES:
                all_vlen_data[root_name].append(vlen_data[root_name])
            
            file_metadata.append({
                "source_file":    path,
                "n_events":       n_events,
                "n_particles":    n_particles,
                "event_start":    event_cursor,
                "particle_start": particle_cursor,
            })
            event_cursor    += n_events
            particle_cursor += n_particles
            print(f"  Read {path}: {n_events} events, {n_particles} particles")

    # --- Concatenate ---
    scalar_data = {k: np.concatenate(v) for k, v in all_scalar_data.items()}
    vlen_data   = {k: ak.concatenate(v) for k, v in all_vlen_data.items()}
    nfsp        = scalar_data["nfsp"]
    n_events    = len(nfsp)
    n_particles = int(nfsp.sum())
    print(f"Total: {n_events} events, {n_particles} particles")

    # --- Drop empty events and events with disallowed PDGs, then truncate ---
    event_ok = np.concatenate(all_event_ok)
    non_empty = nfsp > 0
    keep_idx = np.flatnonzero(non_empty & event_ok)
    n_empty = int((~non_empty).sum())
    n_bad_pdg = int((non_empty & ~event_ok).sum())
    if n_empty:
        print(f"Dropping {n_empty} empty events")
    if n_bad_pdg:
        print(f"Dropping {n_bad_pdg} events containing PDGs not in ALLOWED_PDGS")
        for code, n_ev in bad_pdg_events.most_common():
            print(f"    PDG {code:>10}: {n_ev} events, {bad_pdg_particles[code]} particles")
            
    if max_events is not None:
        if len(keep_idx) < max_events:
            raise ValueError(f"Only {len(keep_idx)} non-empty events available, cannot truncate to {max_events}")
        keep_idx = keep_idx[:max_events]

    scalar_data = {k: v[keep_idx] for k, v in scalar_data.items()}
    vlen_data   = {k: v[keep_idx] for k, v in vlen_data.items()}
    nfsp        = scalar_data["nfsp"]
    n_events    = len(nfsp)
    n_particles = int(nfsp.sum())
    print(f"Kept {n_events} events, {n_particles} particles")

    # --- Write ---
    with h5py.File(hdf5_file, "w") as hf:

        # Top-level metadata
        hf.attrs["n_events"]    = n_events
        hf.attrs["n_particles"] = n_particles
        hf.attrs["tree_name"]   = tree_name
        hf.attrs["n_sources"]   = len(root_files)

        # Per-file metadata as a group of datasets
        meta_grp = hf.create_group("sources")
        meta_grp.create_dataset("source_file",    data=np.array([m["source_file"]    for m in file_metadata], dtype=h5py.string_dtype()))
        meta_grp.create_dataset("n_events",       data=np.array([m["n_events"]       for m in file_metadata], dtype=np.int64))
        meta_grp.create_dataset("n_particles",    data=np.array([m["n_particles"]    for m in file_metadata], dtype=np.int64))
        meta_grp.create_dataset("event_start",    data=np.array([m["event_start"]    for m in file_metadata], dtype=np.int64))
        meta_grp.create_dataset("particle_start", data=np.array([m["particle_start"] for m in file_metadata], dtype=np.int64))

        # Scalar events
        ev_grp = hf.create_group("events")
        for root_name, (hdf5_name, dtype) in SCALAR_BRANCHES.items():
            data = scalar_data[root_name]
            ev_grp.create_dataset(
                hdf5_name,
                data=data.astype(dtype),
                compression="gzip",
                compression_opts=4,
            )

        # Particle stack
        pt_grp = hf.create_group("particles")
        pt_grp.attrs["description"] = "Flat concatenated stack; use offsets to index events"

        offsets = np.concatenate([[0], np.cumsum(nfsp)]).astype(np.int64)
        pt_grp.create_dataset("offsets", data=offsets, compression="gzip")

        for root_name, (hdf5_name, dtype) in VLEN_BRANCHES.items():
            data = ak.to_numpy(ak.flatten(vlen_data[root_name]))
            pt_grp.create_dataset(
                hdf5_name,
                data=data.astype(dtype),
                compression="gzip",
                compression_opts=4,
            )

    print(f"Written to {hdf5_file}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Convert FlatTree ROOT files to HDF5.")
    parser.add_argument("--root_files", type=str, required=True)
    parser.add_argument("--hdf5_file", type=str, required=True)
    parser.add_argument("--max_events", type=int, default=None)
    args = parser.parse_args()

    convert_flattrees_to_hdf5(args.root_files,
                              args.hdf5_file,
                              max_events=args.max_events)
