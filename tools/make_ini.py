#!/usr/bin/env python3
"""
tools/make_ini.py

Create a ROMS-compatible initial conditions NetCDF using a resolved config dict.

Preferred usage (from orchestrator):
    from tools.make_ini import make_ini_from_config
    ini_path = make_ini_from_config(cfg_dict)

CLI fallback:
    python tools/make_ini.py path/to/config.yaml
"""

import os
import sys
import numpy as np
import netCDF4 as nc
import yaml
from utils import compute_z_r


def make_ini_from_config(cfg: dict) -> str:
    """
    Create the initial conditions file using values from a resolved config dict.

    Required keys in cfg:
      - io.input_dir
      - files.grd, files.ini
      - grid.N
      - vertical.Vtransform, vertical.Vstretching, vertical.THETA_S, vertical.THETA_B, vertical.HC
      - initial:
          ocean_time_seconds
          ubar_constant, vbar_constant
          u_constant, v_constant
          zeta_constant
          temp_T0, temp_dT, temp_scale
          salt_S0
    """
    input_dir = cfg["io"]["input_dir"]
    grd_name  = cfg["files"]["grd"]
    ini_name  = cfg["files"]["ini"]

    grd_path = os.path.join(input_dir, grd_name)
    ini_path = os.path.join(input_dir, ini_name)
    os.makedirs(os.path.dirname(ini_path) or ".", exist_ok=True)

    # Read required config values
    N = int(cfg["grid"]["N"])

    Vtransform  = int(cfg["vertical"]["Vtransform"])
    Vstretching = int(cfg["vertical"]["Vstretching"])
    THETA_S     = float(cfg["vertical"]["THETA_S"])
    THETA_B     = float(cfg["vertical"]["THETA_B"])
    HC          = float(cfg["vertical"]["HC"])

    init = cfg["initial"]
    ocean_time_seconds = float(init["ocean_time_seconds"])
    ubar_const = float(init["ubar_constant"])
    vbar_const = float(init["vbar_constant"])
    u_const    = float(init["u_constant"])
    v_const    = float(init["v_constant"])
    zeta_const = float(init["zeta_constant"])
    temp_T0    = float(init["temp_T0"])
    temp_dT    = float(init["temp_dT"])
    temp_scale = float(init["temp_scale"])
    salt_S0    = float(init["salt_S0"])

    # Read grid geometry
    with nc.Dataset(grd_path, "r") as grd:
        h     = grd.variables["h"][:]
        x_rho = grd.variables["x_rho"][:]
        y_rho = grd.variables["y_rho"][:]
        x_u   = grd.variables["x_u"][:]
        y_u   = grd.variables["y_u"][:]
        x_v   = grd.variables["x_v"][:]
        y_v   = grd.variables["y_v"][:]

        xi_rho  = len(grd.dimensions["xi_rho"])
        eta_rho = len(grd.dimensions["eta_rho"])
        xi_u    = xi_rho - 1
        eta_u   = eta_rho
        xi_v    = xi_rho
        eta_v   = eta_rho - 1

    # Compute vertical coordinates at RHO-points
    # Note: compute_z_r signature expected as compute_z_r(h, HC, THETA_S, THETA_B, N)
    z_r = compute_z_r(h, HC, THETA_S, THETA_B, N)  # shape: (N, eta_rho, xi_rho)

    # Interpolate z_r to staggered points
    z_r_u = 0.5 * (z_r[:, :, :-1] + z_r[:, :, 1:])  # (N, eta_u, xi_u)
    z_r_v = 0.5 * (z_r[:, :-1, :] + z_r[:, 1:, :])  # (N, eta_v, xi_v)

    # Allocate initial fields based on config
    zeta = np.full((eta_rho, xi_rho), zeta_const, dtype=np.float64)
    ubar = np.full((eta_u,  xi_u),  ubar_const, dtype=np.float64)
    vbar = np.full((eta_v,  xi_v),  vbar_const, dtype=np.float64)

    u_3d = np.full((N, eta_u,  xi_u),  u_const, dtype=np.float64)
    v_3d = np.full((N, eta_v,  xi_v),  v_const, dtype=np.float64)

    temp = temp_T0 + temp_dT * np.exp(z_r / float(temp_scale))
    salt = np.full_like(z_r, salt_S0, dtype=np.float64)

    # Write initial conditions NetCDF
    with nc.Dataset(ini_path, "w", format="NETCDF4") as f:
        # Global attributes
        f.title       = "ROMS Initial Conditions (config-driven)"
        f.history     = "Created by tools/make_ini.py"
        f.description = "Initial conditions with constant velocities and analytic T,S"
        f.source      = "Generated from grid file"

        # Dimensions
        f.createDimension("xi_rho", xi_rho)
        f.createDimension("eta_rho", eta_rho)
        f.createDimension("xi_u",   xi_u)
        f.createDimension("eta_u",  eta_u)
        f.createDimension("xi_v",   xi_v)
        f.createDimension("eta_v",  eta_v)
        f.createDimension("s_rho",  N)
        f.createDimension("ocean_time", None)

        # ocean_time
        ocean_time = f.createVariable("ocean_time", "f8", ("ocean_time",))
        ocean_time.long_name = "time since simulation start"
        ocean_time.units     = "seconds since 0001-01-01 00:00:00"
        ocean_time.calendar  = "360.0 days in every year"
        ocean_time[0]        = ocean_time_seconds

        # zeta
        v_zeta = f.createVariable("zeta", "f8", ("ocean_time", "eta_rho", "xi_rho"))
        v_zeta.long_name = "free-surface"
        v_zeta.units     = "meter"
        v_zeta[0, :, :]  = zeta

        # ubar
        v_ubar = f.createVariable("ubar", "f8", ("ocean_time", "eta_u", "xi_u"))
        v_ubar.long_name = "vertically integrated u-momentum component"
        v_ubar.units     = "meter second-1"
        v_ubar[0, :, :]  = ubar

        # vbar
        v_vbar = f.createVariable("vbar", "f8", ("ocean_time", "eta_v", "xi_v"))
        v_vbar.long_name = "vertically integrated v-momentum component"
        v_vbar.units     = "meter second-1"
        v_vbar[0, :, :]  = vbar

        # u (3D)
        v_u = f.createVariable("u", "f8", ("ocean_time", "s_rho", "eta_u", "xi_u"))
        v_u.long_name = "u-momentum component"
        v_u.units     = "meter second-1"
        v_u[0, :, :, :] = u_3d

        # v (3D)
        v_v = f.createVariable("v", "f8", ("ocean_time", "s_rho", "eta_v", "xi_v"))
        v_v.long_name = "v-momentum component"
        v_v.units     = "meter second-1"
        v_v[0, :, :, :] = v_3d

        # temp
        v_temp = f.createVariable("temp", "f8", ("ocean_time", "s_rho", "eta_rho", "xi_rho"))
        v_temp.long_name = "potential temperature"
        v_temp.units     = "Celsius"
        v_temp[0, :, :, :] = temp

        # salt
        v_salt = f.createVariable("salt", "f8", ("ocean_time", "s_rho", "eta_rho", "xi_rho"))
        v_salt.long_name = "salinity"
        v_salt.units     = "PSU"
        v_salt[0, :, :, :] = salt

    print(f"Initial conditions file written: {ini_path}")
    return ini_path


if __name__ == "__main__":
    # CLI fallback: accept a single config path
    if len(sys.argv) != 2:
        print("Usage: python tools/make_ini.py path/to/config.yaml", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1], "r") as f:
        cfg = yaml.safe_load(f)
    make_ini_from_config(cfg)