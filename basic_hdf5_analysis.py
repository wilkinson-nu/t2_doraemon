import h5py
import numpy as np
import matplotlib.pyplot as plt
import sys
from glob import glob
from mpl_toolkits.axes_grid1 import make_axes_locatable

## Plot aesthetics
plt.rcParams.update({
    "font.size": 14,
    "axes.labelsize": 16,
    "axes.titlesize": 16,
    "xtick.labelsize": 12,
    "ytick.labelsize": 14,
    "legend.fontsize": 14,
    "axes.linewidth": 1.5,
    "xtick.major.width": 1.5,
    "ytick.major.width": 1.5,
    "xtick.minor.width": 1.2,
    "ytick.minor.width": 1.2,
})

XLABELS = {
    "ke":      "Kinetic energy (GeV)",
    "px":      r"$p_{x}$ (GeV)",
    "py":      r"$p_{y}$ (GeV)",
    "pz":      r"$p_{z}$ (GeV)",
    "pxoverE": r"$p_{x}/E$",
    "pyoverE": r"$p_{y}/E$",
    "pzoverE": r"$p_{z}/E$",
}

MULT_DICT = {
    -3122: 3,
    -2212: 3,
    -2112: 3,
    -321: 3,
    -211: 10,
    -13: 3,
    -11: 3,
    11: 5,
    13: 3,
    22: 5,
    111: 10,
    211: 10,
    311: 5,
    321: 5,
    2112: 15,
    2212: 15,
    3122: 3
}

expected_pdgs = [-3122, -2212, -2112, -321, -211, -13, -11, 11, 13, 22, 111, 211, 311, 321, 2112, 2212, 3122]

def rgb(r, g, b):
    return (r / 255.0, g / 255.0, b / 255.0)


def make_bins(min, max, nbins, log_binning=False):
    if log_binning:
        if min <= 0:
            raise ValueError("min must be > 0 for log binning")
        return np.logspace(np.log10(min), np.log10(max), nbins + 1)
    return np.linspace(min, max, nbins + 1)


def get_pdg_counts(hdf5_file):
    print("Counting PDG codes in", hdf5_file)

    with h5py.File(hdf5_file, "r") as f:
        pt_grp = f["particles"]
        pdg_list = pt_grp["pdg"][:]

    unique_pdgs, counts = np.unique(pdg_list, return_counts=True)

    print("Found", len(unique_pdgs), "unique pdg codes:")
    print(unique_pdgs)

    return dict(zip(unique_pdgs.tolist(), counts.tolist()))


def find_unexpected(hdf5_file, expected, max_print=50):
    with h5py.File(hdf5_file, "r") as f:
        pt_grp = f["particles"]
        pdg = np.asarray(pt_grp["pdg"][:], dtype=np.int64)
        offsets = np.asarray(pt_grp["offsets"][:], dtype=np.int64)

    odd_codes = np.setdiff1d(np.unique(pdg), np.asarray(expected, dtype=np.int64))
    print(f"\n=== {hdf5_file} ===")
    if odd_codes.size == 0:
        print("  no unexpected codes")
        return

    hits = np.flatnonzero(~np.isin(pdg, expected))
    events = np.searchsorted(offsets, hits, side="right") - 1

    for code in odd_codes.tolist():
        m = pdg[hits] == code
        ev = events[m]
        print(f"  pdg {code}: {m.sum()} particles, events {ev[:max_print].tolist()}"
              + (" ..." if ev.size > max_print else ""))

def dump_event(hdf5_file, event):
    """Print the full final state of a single event."""
    with h5py.File(hdf5_file, "r") as f:
        pt_grp = f["particles"]
        offsets = np.asarray(pt_grp["offsets"][:], dtype=np.int64)
        start, stop = offsets[event], offsets[event + 1]
        print(f"\nEvent {event}: {stop - start} particles")
        for key in ("pdg", "E", "px", "py", "pz"):
            print(f"  {key}: {np.asarray(pt_grp[key][start:stop])}")
            

def plot_pdg_frequencies(files,
                         labels,
                         colors=None,
                         normalize=False,
                         group_width=0.7,
                         prefix="all"):
    # Get counts per file
    counts_per_file = [get_pdg_counts(f) for f in files]

    # Build the union of all PDG codes across every file, sorted
    all_pdgs = sorted(set().union(*[c.keys() for c in counts_per_file]))

    # Convert PDG codes to strings so they're treated as categorical
    pdg_labels = [str(p) for p in all_pdgs]
    x = np.arange(len(all_pdgs))

    n_files = len(files)

    # group_width < 1 leaves a gap between adjacent PDG groups.
    # Each file's bar within a group is group_width / n_files wide.
    bar_width = group_width / n_files

    # Default color cycle if none provided
    if colors is None:
        colors = [None] * n_files

    fig, ax = plt.subplots(figsize=(max(10, len(all_pdgs) * 0.4), 6))

    for i, (counts, label, color) in enumerate(zip(counts_per_file, labels, colors)):
        heights = np.array([counts.get(p, 0) for p in all_pdgs], dtype=float)

        if normalize:
            total = heights.sum()
            if total > 0:
                heights = heights / total

        # Center the group of bars on each x position
        offset = (i - (n_files - 1) / 2) * bar_width
        ax.bar(x + offset, heights, bar_width, label=label, color=color)

    ax.set_xticks(x)
    ax.set_xticklabels(pdg_labels, rotation=90)
    ax.set_xlabel("PDG code")
    ax.set_ylabel("Fraction" if normalize else "Frequency")
    ax.set_yscale("log")
    ax.legend(frameon=False)

    fig.tight_layout()
    fig.savefig(f"{prefix}_pdg_frequencies.pdf")
    plt.close(fig)

    return all_pdgs


def load_particles(hdf5_file, var):
    with h5py.File(hdf5_file, "r") as f:
        pt_grp = f["particles"]

        def read(name):
            return np.asarray(pt_grp[name][:], dtype=np.float64)

        pdg = np.asarray(pt_grp["pdg"][:], dtype=np.int32)
        nevt = pt_grp["offsets"][:].size - 1
        
        if var in ("px", "py", "pz"):
            return nevt, pdg, read(var)

        if var in ("pxoverE", "pyoverE", "pzoverE"):
            comp = var[:2]  # "px", "py" or "pz"
            return nevt, pdg, read(comp) / read("E")

        if var == "ke":
            E = read("E")
            p2 = read("px")**2 + read("py")**2 + read("pz")**2
            m = np.sqrt(np.clip(E**2 - p2, 0.0, None))
            return nevt, pdg, E - m

    raise ValueError(f"unknown var: {var}")

def load_multiplicity(hdf5_file, codes):
    """Per-event count of particles matching `codes`, length n_events."""
    codes = np.atleast_1d(np.asarray(codes, dtype=np.int64))

    with h5py.File(hdf5_file, "r") as f:
        pt = f["particles"]
        pdg = np.asarray(pt["pdg"][:], dtype=np.int64)
        offsets = np.asarray(pt["offsets"][:], dtype=np.int64)

    n_events = offsets.size - 1
    assert offsets[-1] == pdg.size, "offsets[-1] != n_particles"

    hits = np.flatnonzero(np.isin(pdg, codes))
    ev = np.searchsorted(offsets, hits, side="right") - 1
    counts = np.bincount(ev, minlength=n_events)

    return n_events, counts


def plot_comparisons(files, pdg_codes, x_min, x_max, nbins,
                     labels, colors, var_name="ke",
                     log_binning=False, title=None, prefix="all", logy=True):

    pdg_label = pdg_codes
    # Accept a single code or a list/tuple of codes
    if np.isscalar(pdg_codes):
        pdg_codes = [pdg_codes]
    code_set = set(pdg_codes)

    edges = make_bins(x_min, x_max, nbins, log_binning)

    fig, ax = plt.subplots(figsize=(8, 6))
    any_data = False

    for hdf5_file, label, color in zip(files, labels, colors):
        nevt, pdg, var = load_particles(hdf5_file, var_name)
        # Select particles whose pdg is any of the requested codes
        sel = var[np.isin(pdg, list(code_set))]
        if sel.size == 0:
            continue  # this file has none of the requested codes
        any_data = True
        ax.hist(
            sel,
            bins=edges,
            histtype="step",
            linewidth=1.5,
            weights=np.full(sel.size, 1.0 / nevt),
            label=label,
            color=color,
        )

    if not any_data:
        print(f"No particles found for pdg codes {sorted(code_set)}, skipping")
        plt.close(fig)
        return

    if log_binning:
        ax.set_xscale("log")
    ax.set_xlabel(XLABELS[var_name])
    ax.set_ylabel("Particles per event")

    log_string = "liny"
    if logy:
        ax.set_yscale("log")
        log_string = "logy"

    # Build a default title/filename from the codes if not given
    codes_str = "_".join(str(c) for c in sorted(code_set))
    ax.legend(frameon=False, title=f"PDG = {pdg_label}", title_fontsize="medium")

    fig.tight_layout()
    fig.savefig(f"{prefix}_{var_name}_pdg_{codes_str}_{log_string}.pdf")
    plt.close(fig)


def plot_multiplicity(files, pdg_codes, x_max, labels, colors,
                      title=None,
                      prefix="all", logy=True):

    pdg_label = pdg_codes
    if np.isscalar(pdg_codes):
        pdg_codes = [pdg_codes]
    code_set = sorted(set(pdg_codes))

    edges = np.arange(0, x_max + 2) - 0.5

    fig, ax = plt.subplots(figsize=(8, 6))
    any_data = False

    for hdf5_file, label, color in zip(files, labels, colors):
        nevt, counts = load_multiplicity(hdf5_file, code_set)
        if counts.max() == 0:
            continue
        any_data = True

        mean = counts.mean()                      # before clipping
        sel = np.clip(counts, None, x_max)        # pile overflow into last bin

        ax.hist(sel, bins=edges, histtype="step", linewidth=1.5,
                weights=np.full(sel.size, 1.0 / nevt),
                label=rf"{label}",
                color=color)

    if not any_data:
        print(f"No particles found for pdg codes {code_set}, skipping",
              flush=True)
        plt.close(fig)
        return

    ax.set_xticks(np.arange(edges[0] + 0.5, x_max + 1))
    ax.set_xlim(edges[0], edges[-1])
    ax.set_xlabel(f"N. {pdg_label}")
    ax.set_ylabel("Fraction of events")

    log_string = "liny"
    if logy:
        ax.set_yscale("log")
        log_string = "logy"

    codes_str = "_".join(str(c) for c in code_set)
    ax.legend(frameon=False)

    fig.tight_layout()
    fig.savefig(f"{prefix}_N{codes_str}_{log_string}.pdf")
    plt.close(fig)
    
    
def cooccurrence_matrix(hdf5_file, codes, min_count=None, chunk=200_000):
    """
    P[i, j] = P(event satisfies codes[j] | event satisfies codes[i])

    "Satisfies code c" means the event holds at least min_count[c] instances,
    defaulting to 1.  For CC-numu samples pass min_count={13: 2} so that the
    primary muon doesn't count and row/column 13 means "an extra mu- exists".
    """
    codes = np.asarray(codes, dtype=np.int64)
    n_codes = codes.size

    thresh = np.ones(n_codes, dtype=np.int64)
    for c, m in (min_count or {}).items():
        thresh[codes == c] = m

    with h5py.File(hdf5_file, "r") as f:
        pt = f["particles"]
        pdg = np.asarray(pt["pdg"][:], dtype=np.int64)
        offsets = np.asarray(pt["offsets"][:], dtype=np.int64)

    n_events = offsets.size - 1
    assert offsets[-1] == pdg.size, "offsets[-1] != n_particles"

    # Map each particle to a column, discarding codes we didn't ask about
    order = np.argsort(codes)
    sorted_codes = codes[order]
    pos = np.clip(np.searchsorted(sorted_codes, pdg), 0, n_codes - 1)
    keep = sorted_codes[pos] == pdg

    # Event index only for the particles we kept -- avoids one int64 per
    # particle in the file, which matters at 10M events
    hits = np.flatnonzero(keep)
    ev = np.searchsorted(offsets, hits, side="right") - 1
    col = order[pos[keep]]

    # Collapse to one entry per (event, code), keeping the multiplicity
    key, mult = np.unique(ev * n_codes + col, return_counts=True)
    ev, col = key // n_codes, key % n_codes
    sel = mult >= thresh[col]
    ev, col = ev[sel], col[sel]

    C = np.zeros((n_codes, n_codes), dtype=np.float64)
    for lo in range(0, n_events, chunk):
        hi = min(lo + chunk, n_events)
        i0, i1 = np.searchsorted(ev, lo), np.searchsorted(ev, hi)
        if i1 == i0:
            continue
        B = np.zeros((hi - lo, n_codes), dtype=np.float32)
        B[ev[i0:i1] - lo, col[i0:i1]] = 1.0
        C += B.T @ B

    n_with = np.diag(C).copy()
    with np.errstate(invalid="ignore", divide="ignore"):
        P = C / n_with[:, None]
    P[n_with == 0] = np.nan

    return P, n_with, n_events

def fmt_cell(v, sci_below=0.1):
    """v in percent. Fixed-point down to sci_below, mathtext scientific under it."""
    if v == 0:
        return "0"
    if v >= sci_below:
        return f"{v:.3g}"
    return f"{v:.2g}"


def plot_cooccurrence(hdf5_file, codes, title=None,
                      prefix="all", annotate=True, cmap="viridis"):

    ## Ignore the first mu- (all CC events)
    min_count={13:2}
    P, n_with, n_events = cooccurrence_matrix(hdf5_file, codes, min_count)

    code_labels = [str(c) for c in codes]
    col_labels = [f"{l} (\u2265{min_count[c]})" if c in min_count else l
                  for l, c in zip(code_labels, codes)]
    row_labels = [f"{l}  ({n / n_events:.2%})"
                  for l, n in zip(col_labels, n_with)]

    n = len(codes)
    fig, ax = plt.subplots(figsize=(0.55 * n + 4.5, 0.55 * n + 2))
    im = ax.imshow(P*100, vmin=0, vmax=100, cmap=cmap, aspect="equal")

    ax.set_xticks(np.arange(n))
    ax.set_xticklabels(col_labels, rotation=90)
    ax.set_yticks(np.arange(n))
    ax.set_yticklabels(row_labels)
    ax.set_title(title or hdf5_file.split("/")[-1])

    if annotate:
        for i in range(n):
            for j in range(n):
                v = P[i, j]*100
                if np.isnan(v):
                    continue
                ax.text(j, i, fmt_cell(v), ha="center", va="center",
                        fontsize=9, color="white" if v < 50 else "black")

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="4%", pad=0.15)
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_label(r"$P(x \mid y)$ [%]", rotation=270, labelpad=15)

    fig.tight_layout()
    fig.savefig(f"{prefix}_cooccurrence.pdf")
    plt.close(fig)    
    

def make_plots(file_prefix):
    
    input_files = [
        "output/"+file_prefix+"_GENIEv3_G18_10a_02_11a_10M.h5",
        "output/"+file_prefix+"_GENIEv3_G18_10b_02_11a_10M.h5",
        "output/"+file_prefix+"_NUWROv25.3.1_10M.h5",
        "output/"+file_prefix+"_NEUT580_10M.h5",
    ]
    
    generator_names = ["GENIE 10a",
                       "GENIE 10b",
                       "NuWro 25",
                       "NEUT 580"]

    # Define your own colors with RGB (0-255) values
    colors = [
        rgb(  0, 119, 187),   # blue
        rgb( 51, 187, 238),   # cyan
        rgb(  0, 153, 136),   # teal
        rgb(238,  51, 119),   # magenta
    ]
    
    all_pdgs = plot_pdg_frequencies(input_files, generator_names, colors=colors, normalize=False, prefix="plots/"+file_prefix)

    for file_name, generator_name in zip(input_files, generator_names):
        ## Check for any odd PDGs
        find_unexpected(file_name, expected_pdgs)
        plot_cooccurrence(file_name, all_pdgs, title=generator_name,
                          prefix="plots/"+file_prefix+"_"+generator_name.replace(" ", ""), annotate=True, cmap="viridis")
    
    ## Now loop over all pdgs, and make per pdg plots
    for pdg in all_pdgs:
        print("Making plots for pdg =", pdg)

        plot_multiplicity(input_files, pdg, MULT_DICT[pdg], generator_names, colors,
                      title=None, prefix="plots/"+file_prefix, logy=True)
        logy = False
 
        plot_comparisons(input_files, pdg, 0, 6, 30,
                         generator_names, colors, var_name="ke", 
                         log_binning=False, title=None, prefix="plots/"+file_prefix, logy=logy)
        plot_comparisons(input_files, pdg, -1, 1, 50,
                         generator_names, colors, var_name="pxoverE",
                         log_binning=False, title=None, prefix="plots/"+file_prefix, logy=logy)        
        plot_comparisons(input_files, pdg, -1, 1, 50,
                         generator_names, colors, var_name="pyoverE",
                         log_binning=False, title=None, prefix="plots/"+file_prefix, logy=logy)
        plot_comparisons(input_files, pdg, -1, 1, 50,
                         generator_names, colors, var_name="pzoverE",
                         log_binning=False, title=None, prefix="plots/"+file_prefix, logy=logy) 
        

if __name__ == "__main__":

    make_plots("DUNE_FHC_numu_Ar40_osc")
    make_plots("DUNE_FHC_numu_Ar40_unosc")
    make_plots("MONO_numu_Ar40_0.6GeV")
    make_plots("MONO_numu_Ar40_2.5GeV")
    make_plots("MONO_numu_Ar40_10GeV")
    
