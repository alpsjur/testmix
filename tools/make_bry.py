#!/usr/bin/env python3
"""
tools/make_bry.py

Create a ROMS-compatible boundary conditions NetCDF (2D fields: zeta, ubar, vbar)
using a resolved configuration dict and the existing grid file.

Preferred usage (from orchestrator):
    from tools.make_bry import make_bry_from_config
    bry_path = make_bry_from_config(cfg_dict)

CLI fallback:
    python tools/make_bry.py path/to/config.yaml
"""

import os
import sys
import numpy as np
import netCDF4 as nc
import yaml


def make_bry_from_config(cfg: dict) -> str:
    """
    Create the boundary condition file using values from a resolved config dict.

    Required keys in cfg:
      - io.input_dir
      - files.grd, files.bry
      - boundary:
          bry_time_seconds
          zeta.north/south/east/west
          ubar.north/south/east/west
          vbar.north/south/east/west
    """
    input_dir = cfg["io"]["input_dir"]
    grd_name  = cfg["files"]["grd"]
    bry_name  = cfg["files"]["bry"]

    grd_path = os.path.join(input_dir, grd_name)
    bry_path = os.path.join(input_dir, bry_name)
    os.makedirs(os.path.dirname(bry_path) or ".", exist_ok=True)

    bcfg = cfg["boundary"]
    bry_time_seconds = float(bcfg["bry_time_seconds"])

    zeta_vals = bcfg["zeta"]
    ubar_vals = bcfg["ubar"]
    vbar_vals = bcfg["vbar"]

    # Read grid geometry
    with nc.Dataset(grd_path, "r") as grd:
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

    # Map boundary edges to coordinate slices and their 1D dim names
    boundary_map = {
        "north": {
            "zeta": (x_rho[-1, :], y_rho[-1, :], "xi_rho"),
            "ubar": (x_u[-1, :],   y_u[-1, :],   "xi_u"),
            "vbar": (x_v[-1, :],   y_v[-1, :],   "xi_v"),
        },
        "south": {
            "zeta": (x_rho[0, :],  y_rho[0, :],  "xi_rho"),
            "ubar": (x_u[0, :],    y_u[0, :],    "xi_u"),
            "vbar": (x_v[0, :],    y_v[0, :],    "xi_v"),
        },
        "east": {
            "zeta": (x_rho[:, -1], y_rho[:, -1], "eta_rho"),
            "ubar": (x_u[:, -1],   y_u[:, -1],   "eta_u"),
            "vbar": (x_v[:, -1],   y_v[:, -1],   "eta_v"),
        },
        "west": {
            "zeta": (x_rho[:, 0],  y_rho[:, 0],  "eta_rho"),
            "ubar": (x_u[:, 0],    y_u[:, 0],    "eta_u"),
            "vbar": (x_v[:, 0],    y_v[:, 0],    "eta_v"),
        },
    }

    # Write boundary NetCDF
    with nc.Dataset(bry_path, "w", format="NETCDF4") as ds:
        # Dimensions
        ds.createDimension("xi_rho",  xi_rho)
        ds.createDimension("eta_rho", eta_rho)
        ds.createDimension("xi_u",    xi_u)
        ds.createDimension("eta_u",   eta_u)
        ds.createDimension("xi_v",    xi_v)
        ds.createDimension("eta_v",   eta_v)
        ds.createDimension("bry_time", None)

        # bry_time variable
        bry_time = ds.createVariable("bry_time", "f8", ("bry_time",))
        bry_time.long_name = "time since simulation start"
        bry_time.units     = "seconds since 0001-01-01 00:00:00"
        bry_time.calendar  = "360.0 days in every year"
        bry_time[0]        = bry_time_seconds

        # One record per boundary and variable
        for bname, bvars in boundary_map.items():
            # zeta
            _, _, dimname = bvars["zeta"]
            zeta_arr = np.full_like(bvars["zeta"][0], float(zeta_vals[bname]), dtype=np.float64)
            v = ds.createVariable(f"zeta_{bname}", "f8", ("bry_time", dimname))
            v.long_name = f"Free surface at {bname} boundary"
            v.units     = "meter"
            v.time      = "bry_time"
            v[0, :]     = zeta_arr

            # ubar
            _, _, dimname = bvars["ubar"]
            ubar_arr = np.full_like(bvars["ubar"][0], float(ubar_vals[bname]), dtype=np.float64)
            v = ds.createVariable(f"ubar_{bname}", "f8", ("bry_time", dimname))
            v.long_name = f"2D u-momentum at {bname} boundary"
            v.units     = "meter second-1"
            v.time      = "bry_time"
            v[0, :]     = ubar_arr

            # vbar
            _, _, dimname = bvars["vbar"]
            vbar_arr = np.full_like(bvars["vbar"][0], float(vbar_vals[bname]), dtype=np.float64)
            v = ds.createVariable(f"vbar_{bname}", "f8", ("bry_time", dimname))
            v.long_name = f"2D v-momentum at {bname} boundary"
            v.units     = "meter second-1"
            v.time      = "bry_time"
            v[0, :]     = vbar_arr

    print(f"Boundary condition file written: {bry_path}")
    return bry_path


if __name__ == "__main__":
    # CLI fallback: accept a single config path
    if len(sys.argv) != 2:
        print("Usage: python tools/make_bry.py path/to/config.yaml", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1], "r") as f:
        cfg = yaml.safe_load(f)
    make_bry_from_config(cfg)