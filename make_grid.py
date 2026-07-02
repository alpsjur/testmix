#!/usr/bin/env python3
"""
make_grid.py  –  Create a ROMS-compatible grid NetCDF file for the testmix test case.

The grid is a simple rectangular domain with uniform depth and flat bottom.
The file includes the 3D field str_a (structure frontal area density, m⁻¹)
required by the STRUCTURE_DRAG parametrization.

Usage
-----
    python make_grid.py [options]

Options (all optional, defaults are testmix parameters)
-------
    --output     Output filename              [testmix_grd.nc]
    --str_a      Uniform str_a value (m⁻¹)   [0.01]
    --depth_zero Depth below which str_a=0 (m). None means full column.  [None]

The vertical coordinates used are Vtransform=2, Vstretching=5
(Johnson, Pringle & Hughes 2019), matching testmix.in.
"""

import argparse
import numpy as np

try:
    import netCDF4 as nc
except ImportError:
    raise SystemExit("netCDF4 is required: pip install netCDF4")


# ---------------------------------------------------------------------------
# Testmix grid parameters — must match testmix.in
# ---------------------------------------------------------------------------
LM      = 10          # Interior rho-points in xi
MM      = 12          # Interior rho-points in eta
N       = 40          # Vertical rho-levels
H0      = 600.0       # Uniform depth (m, positive downward)
DX      = 800.0       # Grid spacing in xi (m)
DY      = 800.0       # Grid spacing in eta (m)
F0      = 1.263e-4    # Coriolis parameter (rad/s)

# Vertical coordinate parameters (testmix.in)
VTRANSFORM  = 2
VSTRETCHING = 5
THETA_S     = 5.0
THETA_B     = 4.0
HC          = 100.0   # = Tcline from testmix.in


def compute_z_r(h, hc, theta_s, theta_b, N):
    """
    Compute depths at rho-levels assuming zeta=0 (mean sea level).
    Vtransform=2, Vstretching=5 (Shchepetkin 2010).
    Matches the formula in roms/ROMS/Utility/set_scoord.F lines 512-531.

    Parameters
    ----------
    h          : ndarray (eta_rho, xi_rho), positive downward [m]
    hc, theta_s, theta_b, N : scalar ROMS parameters

    Returns
    -------
    z_r : ndarray (N, eta_rho, xi_rho), negative (sea level = 0)
          Index [0] is the bottom-most rho-level (k=1 in Fortran).
          Index [N-1] is the top-most rho-level (k=N in Fortran).
    """
    k_arr = np.arange(1, N + 1, dtype=float)
    rN    = float(N)

    # Non-uniform s-coordinate (Vstretching=5, matches set_scoord.F line 515-516)
    sc_r = -(k_arr**2 - 2.0*k_arr*rN + k_arr + rN**2 - rN) / (rN**2 - rN) \
           - 0.01*(k_arr**2 - k_arr*rN) / (1.0 - rN)

    # Stretching function: surface part
    if theta_s > 0:
        Csur = (1.0 - np.cosh(theta_s * sc_r)) / (np.cosh(theta_s) - 1.0)
    else:
        Csur = -(sc_r ** 2)

    # Stretching function: bottom enhancement
    if theta_b > 0:
        Cs_r = (np.exp(theta_b * Csur) - 1.0) / (1.0 - np.exp(-theta_b))
    else:
        Cs_r = Csur

    h3d   = h[np.newaxis, :, :]
    sc_3d = sc_r[:, np.newaxis, np.newaxis]
    Cs_3d = Cs_r[:, np.newaxis, np.newaxis]

    # Vtransform=2, zeta=0
    z_r = (hc * sc_3d + h3d * Cs_3d) / (hc + h3d) * h3d
    return z_r   # <= 0


def build_str_a(h, pm, pn, z_r, str_a_value, depth_zero_below=None):
    """
    Build the 3D str_a array.

    For this simple testmix case str_a is spatially uniform (set to
    str_a_value everywhere), with the option to zero it below a given
    depth from the sea surface.

    Parameters
    ----------
    h              : (eta_rho, xi_rho)
    pm, pn         : (eta_rho, xi_rho) — not used here (uniform grid), but
                     included so the interface matches the general formula:
                       str_a = N_cyl * d * pm * pn
    z_r            : (N, eta_rho, xi_rho), negative
    str_a_value    : scalar, uniform str_a [m⁻¹]
    depth_zero_below : float or None.  If given, set str_a = 0 for any
                     sigma level whose centre is deeper than this value
                     (i.e., further from the surface than depth_zero_below).

    Returns
    -------
    str_a : (N, eta_rho, xi_rho)
    """
    N_lev, eta_rho, xi_rho = z_r.shape
    str_a = np.full((N_lev, eta_rho, xi_rho), str_a_value, dtype=np.float64)

    if depth_zero_below is not None:
        dist_from_surface = -z_r      # positive; 0 = sea surface
        str_a[dist_from_surface > depth_zero_below] = 0.0

    return str_a


def write_grid(output, str_a_value, depth_zero_below):
    # Grid dimensions
    xi_rho  = LM + 2
    eta_rho = MM + 2
    xi_psi  = LM + 1
    eta_psi = MM + 1
    xi_u    = LM + 1
    eta_u   = eta_rho
    xi_v    = xi_rho
    eta_v   = MM + 1

    # 2D coordinate arrays (cell centres at rho-points)
    xi_idx  = np.arange(xi_rho,  dtype=float)   # 0 .. xi_rho-1
    eta_idx = np.arange(eta_rho, dtype=float)

    x_rho = (xi_idx[np.newaxis,  :] + 0.5) * DX     # (eta_rho, xi_rho)
    y_rho = (eta_idx[:, np.newaxis] + 0.5) * DY

    x_psi = (np.arange(1, xi_rho,  dtype=float)) * DX
    y_psi = (np.arange(1, eta_rho, dtype=float)) * DY
    x_psi, y_psi = np.meshgrid(x_psi, y_psi)         # (eta_psi, xi_psi)

    x_u   = (np.arange(1, xi_rho,  dtype=float)) * DX
    y_u   = y_rho[:, :xi_u].copy()
    x_u   = np.tile(x_u, (eta_u, 1))                 # (eta_u, xi_u)

    x_v   = x_rho[:eta_v, :].copy()
    y_v   = (np.arange(1, eta_rho, dtype=float)) * DY
    y_v   = np.tile(y_v[:, np.newaxis], (1, xi_v))   # (eta_v, xi_v)

    # Uniform scalar fields
    h      = np.full((eta_rho, xi_rho), H0,        dtype=np.float64)
    f      = np.full((eta_rho, xi_rho), F0,        dtype=np.float64)
    pm     = np.full((eta_rho, xi_rho), 1.0 / DX,  dtype=np.float64)
    pn     = np.full((eta_rho, xi_rho), 1.0 / DY,  dtype=np.float64)
    xl_val = float(LM * DX)          # domain extent in xi (m)
    el_val = float(MM * DY)          # domain extent in eta (m)

    # Vertical coordinates for str_a construction
    z_r = compute_z_r(h, HC, THETA_S, THETA_B, N)

    # Build str_a
    str_a = build_str_a(h, pm, pn, z_r, str_a_value, depth_zero_below)

    # Blockage ratio check
    z_w       = np.zeros((N + 1, eta_rho, xi_rho))
    z_w[1:-1] = 0.5 * (z_r[:-1] + z_r[1:])
    z_w[0]    = -h
    z_w[-1]   = 0.0
    Hz_approx = np.diff(z_w, axis=0)                 # (N, eta_rho, xi_rho)
    blockage  = str_a * Hz_approx
    nonzero   = str_a > 0
    if nonzero.any():
        print(f"str_a range (non-zero): "
              f"{str_a[nonzero].min():.4g} – {str_a[nonzero].max():.4g} m⁻¹")
        print(f"Max blockage ratio    : {blockage.max():.4f}"
              f"  (should be < ~0.3 for parametrization validity)")
    else:
        print("WARNING: str_a is zero everywhere!")

    # ---------------------------------------------------------------------------
    # Write NetCDF
    # ---------------------------------------------------------------------------
    with nc.Dataset(output, 'w', format='NETCDF4') as ds:
        # Global attributes
        ds.title       = "ROMS grid file for testmix"
        ds.type        = "ROMS grid file"
        ds.Conventions = "CF-1.6"
        ds.history     = "Created by make_grid.py"

        # Dimensions
        ds.createDimension('xi_rho',  xi_rho)
        ds.createDimension('eta_rho', eta_rho)
        ds.createDimension('xi_psi',  xi_psi)
        ds.createDimension('eta_psi', eta_psi)
        ds.createDimension('xi_u',    xi_u)
        ds.createDimension('eta_u',   eta_u)
        ds.createDimension('xi_v',    xi_v)
        ds.createDimension('eta_v',   eta_v)
        ds.createDimension('s_rho',   N)
        ds.createDimension('one',     1)

        # Scalar domain-size variables (required by ROMS get_grid.F)
        def scalar_var(name, value, long_name, units):
            v = ds.createVariable(name, 'f8', ('one',))
            v.long_name = long_name
            v.units     = units
            v[:] = value

        scalar_var('xl', xl_val, 'domain length in the XI-direction', 'meter')
        scalar_var('el', el_val, 'domain length in the ETA-direction', 'meter')

        # Spherical flag (0 = Cartesian)
        vs = ds.createVariable('spherical', 'i4', ('one',))
        vs.long_name = 'grid type logical switch'
        vs.flag_values    = [0, 1]
        vs.flag_meanings  = 'Cartesian spherical'
        vs[:] = 0

        # Helper to write a 2D field
        def write2d(name, dims, data, long_name, units, dtype='f8'):
            v = ds.createVariable(name, dtype, dims)
            v.long_name = long_name
            v.units     = units
            v[:]        = data

        write2d('h',      ('eta_rho', 'xi_rho'), h,
                'bathymetry at RHO-points', 'meter')
        write2d('f',      ('eta_rho', 'xi_rho'), f,
                'Coriolis parameter at RHO-points', 'second-1')
        write2d('pm',     ('eta_rho', 'xi_rho'), pm,
                'curvilinear coordinate metric in XI', 'meter-1')
        write2d('pn',     ('eta_rho', 'xi_rho'), pn,
                'curvilinear coordinate metric in ETA', 'meter-1')
        write2d('x_rho',  ('eta_rho', 'xi_rho'), x_rho,
                'x-locations of RHO-points', 'meter')
        write2d('y_rho',  ('eta_rho', 'xi_rho'), y_rho,
                'y-locations of RHO-points', 'meter')
        write2d('x_psi',  ('eta_psi', 'xi_psi'), x_psi,
                'x-locations of PSI-points', 'meter')
        write2d('y_psi',  ('eta_psi', 'xi_psi'), y_psi,
                'y-locations of PSI-points', 'meter')
        write2d('x_u',    ('eta_u',   'xi_u'),   x_u,
                'x-locations of U-points', 'meter')
        write2d('y_u',    ('eta_u',   'xi_u'),   y_rho[:, :xi_u],
                'y-locations of U-points', 'meter')
        write2d('x_v',    ('eta_v',   'xi_v'),   x_rho[:eta_v, :],
                'x-locations of V-points', 'meter')
        write2d('y_v',    ('eta_v',   'xi_v'),   y_v,
                'y-locations of V-points', 'meter')

        # 3D structure frontal area density
        # NOTE: _FillValue must NOT be 0.0 — ROMS masks any value where
        # ABS(val) >= ABS(_FillValue). Use a large sentinel instead.
        v = ds.createVariable('str_a', 'f8',
                              ('s_rho', 'eta_rho', 'xi_rho'),
                              fill_value=9.99e+36)
        v.long_name  = 'structure frontal area density'
        v.units      = 'meter-1'
        v.valid_min  = np.float64(0.0)
        v[:]         = str_a

    print(f"Grid file written: {output}")
    print(f"  xi_rho={xi_rho}, eta_rho={eta_rho}, N={N}")
    print(f"  Domain: {xl_val:.0f} m x {el_val:.0f} m, depth={H0:.0f} m")
    print(f"  Vtransform={VTRANSFORM}, Vstretching={VSTRETCHING}, "
          f"theta_s={THETA_S}, theta_b={THETA_B}, hc={HC}")
    if depth_zero_below is not None:
        print(f"  str_a = {str_a_value} m⁻¹ for z < {depth_zero_below} m, "
              f"0 deeper")
    else:
        print(f"  str_a = {str_a_value} m⁻¹ throughout the full water column")


def main():
    parser = argparse.ArgumentParser(
        description='Create testmix ROMS grid NetCDF with str_a field')
    parser.add_argument('--output', default='testmix_grd.nc',
                        help='Output filename (default: testmix_grd.nc)')
    parser.add_argument('--str_a', type=float, default=0.01,
                        help='Uniform str_a value in m⁻¹ (default: 0.01)')
    parser.add_argument('--depth_zero', type=float, default=None,
                        help='Set str_a=0 below this depth in m '
                             '(default: full column non-zero)')
    args = parser.parse_args()

    write_grid(
        output          = args.output,
        str_a_value     = args.str_a,
        depth_zero_below= args.depth_zero,
    )


if __name__ == '__main__':
    main()
