#!/usr/bin/env python3
"""
add_str_a.py  –  Add or update the str_a variable in a ROMS grid NetCDF file.

str_a is the structure frontal area density (m⁻¹), a 3D field on
(s_rho, eta_rho, xi_rho) used by the STRUCTURE_MIXING parametrization.
ROMS applies drag wherever str_a > 0, scaled with str_a.

Usage
-----
    python add_str_a.py GRID_FILE INPUT_FILE [INPUT_FILE ...] [options]

Positional arguments
--------------------
    GRID_FILE      Existing ROMS grid NetCDF file (modified in-place).
    INPUT_FILE(s)  One or more text files with columns:
                       xi_index  eta_index  str_a  depth
                   where xi_index and eta_index are 0-based integer indices,
                   str_a is the value (m⁻¹), and depth is the depth extent
                   in metres (positive downward from the surface). A depth of
                   -1 means the structure extends through the full water column.
                   Lines starting with '#' and the first non-comment line
                   (treated as a header) are ignored.

Options
-------
    --reset         Zero str_a everywhere before applying input files.
    --N N           Number of vertical rho-levels.  Required when str_a does
                    not yet exist in the grid file and the s_rho dimension is
                    absent.
    --theta_s TS    Surface stretching parameter  [default: 5.0]
    --theta_b TB    Bottom  stretching parameter  [default: 4.0]
    --hc HC         Critical depth / Tcline (m)   [default: 100.0]
    --vtransform V  Vtransform (1 or 2)            [default: 2]
    --vstretching S Vstretching (1, 4, or 5)       [default: 5]

Notes
-----
* The vertical coordinate parameters default to the testmix.in values.
  For other grids (e.g. norkyst) pass the correct values on the command line.
* Because ROMS uses terrain-following sigma coordinates, the same sigma level
  maps to different physical depths at different (xi, eta) locations.  This
  script computes z_r at each column individually so the depth cutoff is
  applied correctly everywhere.
* The grid file is opened in append mode ('a'), so all existing variables and
  attributes are preserved.
"""

import argparse
import sys
from datetime import datetime, timezone

import numpy as np

try:
    import netCDF4 as nc
except ImportError:
    raise SystemExit("netCDF4 is required: pip install netCDF4")


# ---------------------------------------------------------------------------
# Vertical-coordinate utilities
# ---------------------------------------------------------------------------

def _sc_r(N: int, vstretching: int) -> np.ndarray:
    """
    Compute the s-coordinate values at rho-points for k = 1 … N.

    Returns array of shape (N,) with values in (-1, 0).
    """
    k = np.arange(1, N + 1, dtype=float)
    rN = float(N)

    if vstretching == 5:
        # Shchepetkin (2010) non-uniform spacing — matches set_scoord.F lines 515-516
        sc = (-(k**2 - 2.0*k*rN + k + rN**2 - rN) / (rN**2 - rN)
              - 0.01*(k**2 - k*rN) / (1.0 - rN))
    else:
        # Standard mid-cell placement used by Vstretching 1, 2, 3, 4
        sc = -1.0 + (k - 0.5) / rN

    return sc  # shape (N,), bottom=-1 to top~0


def _stretching(sc: np.ndarray, theta_s: float, theta_b: float,
                vstretching: int) -> np.ndarray:
    """
    Compute the stretching function C(s) for the given Vstretching option.

    Parameters
    ----------
    sc          : s-coordinate values, shape (N,)
    theta_s     : surface control parameter
    theta_b     : bottom  control parameter
    vstretching : ROMS Vstretching flag (1, 4, or 5)

    Returns
    -------
    Cs : shape (N,)
    """
    if vstretching in (4, 5):
        # Shchepetkin (2005 / 2010) — same Cs formula for both 4 and 5
        if theta_s > 0.0:
            csur = (1.0 - np.cosh(theta_s * sc)) / (np.cosh(theta_s) - 1.0)
        else:
            csur = -(sc ** 2)

        if theta_b > 0.0:
            Cs = (np.exp(theta_b * csur) - 1.0) / (1.0 - np.exp(-theta_b))
        else:
            Cs = csur

    elif vstretching == 1:
        # Song & Haidvogel (1994)
        if theta_s > 0.0:
            csur = (1.0 - np.cosh(theta_s * sc)) / (np.cosh(theta_s) - 1.0)
        else:
            csur = -(sc ** 2)

        if theta_b > 0.0:
            Cs = ((1.0 - theta_b) * csur
                  - theta_b * (np.sinh(theta_b * sc) / np.sinh(theta_b) - sc))
        else:
            Cs = csur

    else:
        raise ValueError(f"Unsupported Vstretching={vstretching}. "
                         "Use 1, 4, or 5.")

    return Cs  # shape (N,)


def compute_z_r(h: np.ndarray, hc: float, theta_s: float, theta_b: float,
                N: int, vtransform: int = 2, vstretching: int = 5) -> np.ndarray:
    """
    Compute physical depths at rho-levels (zeta = 0, mean sea level).

    Parameters
    ----------
    h           : (eta_rho, xi_rho), bathymetry (positive downward, m)
    hc          : critical depth / Tcline (m)
    theta_s     : surface stretching
    theta_b     : bottom  stretching
    N           : number of vertical rho-levels
    vtransform  : 1 (Song & Haidvogel) or 2 (Shchepetkin)
    vstretching : 1, 4, or 5

    Returns
    -------
    z_r : (N, eta_rho, xi_rho), depth at rho-points (negative, 0 = surface)
          Index [0] = bottom-most level; index [N-1] = top-most level.
    """
    sc = _sc_r(N, vstretching)                          # (N,)
    Cs = _stretching(sc, theta_s, theta_b, vstretching) # (N,)

    h3d  = h[np.newaxis, :, :]        # (1, eta_rho, xi_rho)
    sc3d = sc[:, np.newaxis, np.newaxis]  # (N, 1, 1)
    Cs3d = Cs[:, np.newaxis, np.newaxis]  # (N, 1, 1)

    if vtransform == 2:
        # Shchepetkin & McWilliams (2009)
        z_r = (hc * sc3d + h3d * Cs3d) / (hc + h3d) * h3d
    elif vtransform == 1:
        # Song & Haidvogel (1994)
        z_r = hc * (sc3d - Cs3d) + h3d * Cs3d
    else:
        raise ValueError(f"Unsupported Vtransform={vtransform}. Use 1 or 2.")

    return z_r   # (<= 0)


# ---------------------------------------------------------------------------
# Input file reader
# ---------------------------------------------------------------------------

def read_input_file(filepath: str) -> list[tuple[int, int, float, float]]:
    """
    Read an input file and return a list of (xi, eta, str_a_val, depth).

    File format
    -----------
    * Lines starting with '#' are ignored.
    * The first non-comment line is treated as a header and skipped.
    * Each subsequent line must have four whitespace- or comma-separated fields:
          xi_index  eta_index  str_a  depth
      where xi_index and eta_index are integers, and str_a / depth are floats.
    """
    records = []
    header_seen = False

    with open(filepath) as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if not header_seen:
                header_seen = True
                continue  # skip header row

            # Accept whitespace- or comma-separated fields
            parts = line.replace(',', ' ').split()
            if len(parts) < 4:
                raise ValueError(
                    f"{filepath}:{lineno}: expected 4 columns, "
                    f"got {len(parts)}: {line!r}")
            try:
                xi    = int(parts[0])
                eta   = int(parts[1])
                val   = float(parts[2])
                depth = float(parts[3])
            except ValueError as exc:
                raise ValueError(
                    f"{filepath}:{lineno}: cannot parse row: {exc}") from exc

            records.append((xi, eta, val, depth))

    if not records:
        print(f"  WARNING: {filepath} contains no data rows.", file=sys.stderr)

    return records


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def apply_str_a(ds: "nc.Dataset",
                records: list[tuple[int, int, float, float]],
                z_r: np.ndarray,
                N: int) -> int:
    """
    Write str_a values from *records* into the open dataset *ds*.

    Returns the number of (xi, eta) points that were updated.
    """
    str_a_var = ds.variables['str_a']
    n_updated = 0

    for (xi, eta, val, depth) in records:
        # Bounds check
        eta_size = ds.dimensions['eta_rho'].size
        xi_size  = ds.dimensions['xi_rho'].size
        if not (0 <= eta < eta_size and 0 <= xi < xi_size):
            print(f"  WARNING: (xi={xi}, eta={eta}) out of bounds "
                  f"({xi_size} x {eta_size}), skipping.", file=sys.stderr)
            continue

        if depth == -1.0:
            # Full water column
            str_a_var[:, eta, xi] = val
        else:
            # z_r is negative; sigma levels shallower than `depth` satisfy
            # -z_r[k, eta, xi] <= depth  i.e.  z_r[k, eta, xi] >= -depth
            col_z = z_r[:, eta, xi]    # shape (N,)
            within = col_z >= -depth   # True for levels within `depth` of surface
            str_a_var[:, eta, xi] = np.where(within, val, 0.0)

        n_updated += 1

    return n_updated


def main():
    parser = argparse.ArgumentParser(
        description='Add or update str_a in a ROMS grid NetCDF file.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)

    parser.add_argument('grid_file',
                        help='Existing ROMS grid NetCDF file (modified in-place)')
    parser.add_argument('input_files', nargs='+',
                        help='One or more input files with columns: '
                             'xi_index  eta_index  str_a  depth')

    parser.add_argument('--reset', action='store_true',
                        help='Reset str_a to zero everywhere before '
                             'applying input files')
    parser.add_argument('--N', type=int, default=None,
                        help='Number of vertical rho-levels (required when '
                             'str_a does not yet exist and the s_rho dimension '
                             'is absent from the grid file)')
    parser.add_argument('--theta_s', type=float, default=5.0,
                        help='Surface stretching parameter [default: 5.0]')
    parser.add_argument('--theta_b', type=float, default=4.0,
                        help='Bottom stretching parameter  [default: 4.0]')
    parser.add_argument('--hc', type=float, default=100.0,
                        help='Critical depth / Tcline (m) [default: 100.0]')
    parser.add_argument('--vtransform', type=int, default=2, choices=[1, 2],
                        help='Vtransform (1 or 2)         [default: 2]')
    parser.add_argument('--vstretching', type=int, default=5, choices=[1, 4, 5],
                        help='Vstretching (1, 4, or 5)    [default: 5]')

    args = parser.parse_args()

    # ------------------------------------------------------------------
    # 1. Read all input files first (fast-fail before touching the grid)
    # ------------------------------------------------------------------
    all_records = []
    for path in args.input_files:
        print(f"Reading input file: {path}")
        recs = read_input_file(path)
        print(f"  {len(recs)} data rows loaded.")
        all_records.extend(recs)

    if not all_records:
        sys.exit("No records found in any input file. Nothing to do.")

    # ------------------------------------------------------------------
    # 2. Open the grid file in append mode
    # ------------------------------------------------------------------
    print(f"\nOpening grid file: {args.grid_file}")
    with nc.Dataset(args.grid_file, 'a') as ds:

        # Read bathymetry
        if 'h' not in ds.variables:
            sys.exit("ERROR: grid file does not contain variable 'h' (bathymetry).")
        h = ds.variables['h'][:]   # (eta_rho, xi_rho), positive downward

        # Determine N
        if 's_rho' in ds.dimensions:
            N_file = ds.dimensions['s_rho'].size
            if args.N is not None and args.N != N_file:
                print(f"WARNING: --N={args.N} overrides s_rho dimension size "
                      f"{N_file}. Using {N_file}.", file=sys.stderr)
            N = N_file
            print(f"  Using N={N} from existing s_rho dimension.")
        else:
            if args.N is None:
                sys.exit(
                    "ERROR: The grid file has no 's_rho' dimension and --N "
                    "was not provided.  Specify --N <number_of_levels>.")
            N = args.N
            print(f"  Creating s_rho dimension with N={N}.")
            ds.createDimension('s_rho', N)

        # Check/create str_a variable
        if 'str_a' in ds.variables:
            str_a_var = ds.variables['str_a']
            var_shape = str_a_var.shape
            expected  = (N, h.shape[0], h.shape[1])
            if var_shape != expected:
                sys.exit(
                    f"ERROR: existing str_a shape {var_shape} does not match "
                    f"expected {expected}.")
            if args.reset:
                print("  --reset: zeroing str_a everywhere.")
                str_a_var[:] = 0.0
            else:
                print("  str_a already exists; existing non-zero values are "
                      "preserved (use --reset to zero first).")
        else:
            print("  str_a not found; creating variable and initialising to 0.")
            str_a_var = ds.createVariable(
                'str_a', 'f8',
                ('s_rho', 'eta_rho', 'xi_rho'),
                fill_value=9.99e+36)
            str_a_var.long_name = 'structure frontal area density'
            str_a_var.units     = 'meter-1'
            str_a_var.valid_min = np.float64(0.0)
            str_a_var[:]        = 0.0

        # ------------------------------------------------------------------
        # 3. Compute z_r (physical depth at rho-levels)
        # ------------------------------------------------------------------
        print(f"\nComputing z_r with Vtransform={args.vtransform}, "
              f"Vstretching={args.vstretching}, "
              f"theta_s={args.theta_s}, theta_b={args.theta_b}, "
              f"hc={args.hc}, N={N} ...")
        z_r = compute_z_r(
            h, args.hc, args.theta_s, args.theta_b, N,
            vtransform=args.vtransform,
            vstretching=args.vstretching)
        print(f"  z_r range: {z_r.min():.1f} … {z_r.max():.1f} m")

        # ------------------------------------------------------------------
        # 4. Apply records to str_a
        # ------------------------------------------------------------------
        print(f"\nApplying {len(all_records)} record(s) to str_a ...")
        n_updated = apply_str_a(ds, all_records, z_r, N)
        print(f"  {n_updated} grid column(s) updated.")

        # ------------------------------------------------------------------
        # 5. Update history attribute
        # ------------------------------------------------------------------
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        files_str = ', '.join(args.input_files)
        new_hist  = (f"{timestamp}: add_str_a.py applied from {files_str}")
        if hasattr(ds, 'history'):
            ds.history = new_hist + '\n' + ds.history
        else:
            ds.history = new_hist

    # ------------------------------------------------------------------
    # 6. Report summary
    # ------------------------------------------------------------------
    print(f"\nDone.  Grid file updated: {args.grid_file}")
    nonzero = int(np.sum(ds.variables['str_a'][:] > 0)
                  if False else 0)  # file is closed; reopen briefly for stats
    with nc.Dataset(args.grid_file) as ds_check:
        arr = ds_check.variables['str_a'][:]
        nonzero_cells = int(np.sum(arr > 0))
        total_cells   = arr.size
        print(f"  str_a non-zero cells : {nonzero_cells:,} / {total_cells:,}")
        if nonzero_cells:
            nz = arr[arr > 0]
            print(f"  str_a range (non-zero): {nz.min():.4g} – {nz.max():.4g} m⁻¹")


if __name__ == '__main__':
    main()
