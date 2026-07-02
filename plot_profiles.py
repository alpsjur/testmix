#!/usr/bin/env python3
"""
plot_profiles.py  –  Compare ROMS history-file profiles across runs.

Produces one figure per variable (density anomaly, u, v, TKE, GLS),
each showing horizontally-averaged vertical profiles from one or more
history files and user-specified time steps.

Usage
-----
    python plot_profiles.py FILE1 [FILE2 ...] [options]

Options
-------
    --timesteps  INT [INT ...]   Time-step indices to plot (0-based).
                                 Default: first and last record.
    --labels     STR [STR ...]   Legend labels for each file.
                                 Default: basename of each file.
    --iavg       INT             Single i-index (xi_rho) for averaging.
                                 Default: average over all interior columns.
    --javg       INT             Single j-index (eta_rho) for averaging.
                                 Default: average over all interior rows.
    --outdir     DIR             Directory to save figures (PNG).
                                 Default: show interactively.

Examples
--------
    # Compare two runs, plot first and last record
    python plot_profiles.py run1/roms_his.nc run2/roms_his.nc

    # Plot specific time steps and save figures
    python plot_profiles.py roms_his.nc --timesteps 0 50 168 --outdir figs/
"""

import argparse
import os
import sys

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.cm as cm

try:
    import netCDF4 as nc
except ImportError:
    sys.exit("netCDF4 is required: pip install netCDF4")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_z_w(ds, tidx):
    """
    Compute physical depths at W-points for one time record.

    Returns z_w : (N+1, eta_rho, xi_rho), negative values (0 = sea surface).
    """
    h      = ds['h'][:]                        # (eta_rho, xi_rho)
    hc     = float(ds['hc'][:])
    s_w    = ds['s_w'][:]                      # (N+1,)
    Cs_w   = ds['Cs_w'][:]                     # (N+1,)
    zeta   = ds['zeta'][tidx, :, :]            # (eta_rho, xi_rho)
    vtrans = int(ds['Vtransform'][:])

    h3    = h[np.newaxis, :, :]
    z3    = zeta[np.newaxis, :, :]
    s3    = s_w[:, np.newaxis, np.newaxis]
    Cs3   = Cs_w[:, np.newaxis, np.newaxis]

    if vtrans == 1:
        z_w = hc * s3 + (h3 - hc) * Cs3 + z3 * (1.0 + s3)
    else:   # Vtransform = 2
        z_w = (hc * s3 + h3 * Cs3) / (hc + h3) * (h3 + z3) - h3
    return z_w


def horiz_avg(arr3d, isel=None, jsel=None):
    """
    Average a (k, eta, xi) array over horizontal dimensions.
    If isel / jsel are given, select a single column instead.
    Returns 1-D array of shape (k,).
    """
    if isel is not None and jsel is not None:
        return arr3d[:, jsel, isel]
    if isel is not None:
        return arr3d[:, :, isel].mean(axis=1)
    if jsel is not None:
        return arr3d[:, jsel, :].mean(axis=1)
    return arr3d.reshape(arr3d.shape[0], -1).mean(axis=1)


def load_profiles(filepath, timesteps, isel, jsel):
    """
    Load all needed profiles from one file for the requested time steps.

    Returns dict of lists, indexed by variable name:
      profiles[varname] = list of (z, values) tuples – one per time step
    """
    profiles = {v: [] for v in ('rho', 'u', 'v', 'tke', 'gls')}
    time_labels = []

    with nc.Dataset(filepath) as ds:
        Nt = len(ds.dimensions['ocean_time'])
        t_units = ds['ocean_time'].units

        for ti in timesteps:
            if ti >= Nt or ti < -Nt:
                print(f"  WARNING: time index {ti} out of range (Nt={Nt}), skipping.")
                continue

            # --- time label ---
            t_sec = float(ds['ocean_time'][ti])
            t_hr  = t_sec / 3600.0
            if t_hr < 48:
                tlabel = f"t={t_hr:.1f} h"
            else:
                tlabel = f"t={t_hr/24:.1f} d"
            time_labels.append(tlabel)

            # --- rho-level depth ---
            z_rho = ds['z_rho'][ti, :, :, :]   # (s_rho, eta_rho, xi_rho)
            z_rho_1d = horiz_avg(z_rho, isel, jsel)

            # --- w-level depth ---
            z_w   = compute_z_w(ds, ti)         # (s_w, eta_rho, xi_rho)
            z_w_1d = horiz_avg(z_w, isel, jsel)

            # --- density anomaly (rho-levels) ---
            rho = ds['rho'][ti, :, :, :]
            profiles['rho'].append((z_rho_1d, horiz_avg(rho, isel, jsel)))

            # --- u velocity (rho-levels, on xi_u grid) ---
            u_raw = ds['u'][ti, :, :, :]        # (s_rho, eta_u, xi_u)
            # Interpolate to rho-points in xi: average adjacent u-columns
            u_rho = 0.5 * (u_raw[:, :, :-1] + u_raw[:, :, 1:])
            # Average over rho-interior xi (xi_u has one fewer point than xi_rho)
            # Use xi_rho interior = 1:-1; xi_u ~ 0:-1 already
            u_1d = horiz_avg(u_rho, isel if isel is None else max(0, isel-1), jsel)
            profiles['u'].append((z_rho_1d, u_1d))

            # --- v velocity (rho-levels, on eta_v grid) ---
            v_raw = ds['v'][ti, :, :, :]        # (s_rho, eta_v, xi_v)
            v_rho = 0.5 * (v_raw[:, :-1, :] + v_raw[:, 1:, :])
            v_1d  = horiz_avg(v_rho, isel, jsel if jsel is None else max(0, jsel-1))
            profiles['v'].append((z_rho_1d, v_1d))

            # --- TKE (w-levels) ---
            tke = ds['tke'][ti, :, :, :]        # (s_w, eta_rho, xi_rho)
            profiles['tke'].append((z_w_1d, horiz_avg(tke, isel, jsel)))

            # --- GLS (w-levels) ---
            gls = ds['gls'][ti, :, :, :]
            profiles['gls'].append((z_w_1d, horiz_avg(gls, isel, jsel)))

    return profiles, time_labels


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

VAR_META = {
    'rho': dict(title='Density anomaly',   xlabel='ρ – ρ₀  (kg m⁻³)',   xscale='linear'),
    'u':   dict(title='U velocity',        xlabel='u  (m s⁻¹)',          xscale='linear'),
    'v':   dict(title='V velocity',        xlabel='v  (m s⁻¹)',          xscale='linear'),
    'tke': dict(title='Turbulent kinetic energy', xlabel='TKE  (m² s⁻²)', xscale='log'),
    'gls': dict(title='Generic length scale',     xlabel='GLS  (m³ s⁻³)', xscale='log'),
}


def make_figures(all_profiles, all_time_labels, file_labels):
    """
    all_profiles    : list (one per file) of dict varname -> [(z,v), ...]
    all_time_labels : list (one per file) of list of str
    file_labels     : list of str
    Returns dict of Figure objects keyed by variable name.
    """
    # Build a colour cycle: different hue per file, line style per time step
    linestyles = ['-', '--', ':', '-.', (0,(3,1,1,1))]
    n_files = len(all_profiles)
    file_colours = cm.tab10(np.linspace(0, 1, max(n_files, 1)))

    figs = {}
    for varname, meta in VAR_META.items():
        fig, ax = plt.subplots(figsize=(5, 8))
        ax.set_title(meta['title'], fontsize=13)
        ax.set_xlabel(meta['xlabel'], fontsize=11)
        ax.set_ylabel('Depth  (m)', fontsize=11)
        if meta['xscale'] == 'log':
            ax.set_xscale('log')
        ax.grid(True, alpha=0.35)

        for fi, (profiles, tlabels) in enumerate(zip(all_profiles, all_time_labels)):
            colour = file_colours[fi]
            for ti, ((z, vals), tlabel) in enumerate(zip(profiles[varname], tlabels)):
                ls  = linestyles[ti % len(linestyles)]
                lbl = f"{file_labels[fi]}  {tlabel}"
                ax.plot(vals, z, color=colour, linestyle=ls, linewidth=1.6, label=lbl)

        ax.legend(fontsize=8, loc='best')
        fig.tight_layout()
        figs[varname] = fig

    return figs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description='Compare vertical profiles from ROMS history files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    p.add_argument('files', nargs='+', metavar='FILE',
                   help='ROMS history NetCDF file(s)')
    p.add_argument('--timesteps', nargs='+', type=int, default=None,
                   metavar='N',
                   help='Time-step indices to plot (0-based). '
                        'Default: first and last.')
    p.add_argument('--labels', nargs='+', default=None,
                   metavar='LABEL',
                   help='Legend label for each file (default: filename).')
    p.add_argument('--iavg', type=int, default=None,
                   help='Fixed xi_rho index (default: average all).')
    p.add_argument('--javg', type=int, default=None,
                   help='Fixed eta_rho index (default: average all).')
    p.add_argument('--outdir', default=None,
                   help='Save figures to this directory instead of showing.')
    return p.parse_args()


def main():
    args = parse_args()

    # File labels
    file_labels = args.labels or [os.path.basename(f) for f in args.files]
    if len(file_labels) < len(args.files):
        file_labels += [os.path.basename(f) for f in args.files[len(file_labels):]]

    all_profiles   = []
    all_time_labels = []

    for filepath, label in zip(args.files, file_labels):
        if not os.path.isfile(filepath):
            sys.exit(f"ERROR: file not found: {filepath}")

        # Determine time indices
        with nc.Dataset(filepath) as ds:
            Nt = len(ds.dimensions['ocean_time'])
        if args.timesteps is None:
            timesteps = [0, Nt - 1] if Nt > 1 else [0]
        else:
            timesteps = args.timesteps

        print(f"Loading {filepath}  (Nt={Nt}, steps={timesteps})")
        profiles, tlabels = load_profiles(filepath, timesteps, args.iavg, args.javg)
        all_profiles.append(profiles)
        all_time_labels.append(tlabels)

    print("Plotting...")
    figs = make_figures(all_profiles, all_time_labels, file_labels)

    if args.outdir:
        os.makedirs(args.outdir, exist_ok=True)
        for varname, fig in figs.items():
            outpath = os.path.join(args.outdir, f"profile_{varname}.png")
            fig.savefig(outpath, dpi=150)
            print(f"  Saved {outpath}")
        plt.close('all')
    else:
        plt.show()


if __name__ == '__main__':
    main()
