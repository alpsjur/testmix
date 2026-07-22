#!/usr/bin/env python3
"""
create_initial_conditions_from_restart.py — Create a ROMS-compatible NetCDF file
for initial conditions, using an existing restart file.

This script reads a ROMS restart file and modifies its variables to create
an initial condition file. Physical variables (ubar, vbar, u, v, zeta, temp, salt)
are initialized using predefined functions.

Usage:
    python create_initial_conditions_from_restart.py --restart_file restart.nc --output_file roms_ini.nc
"""

import numpy as np
import netCDF4 as nc
import argparse
import os
from utils import compute_z_r

# ---------------------------------------------------------------------------
# Parameters for Vertical Coordinate Transformation
# ---------------------------------------------------------------------------
VTRANSFORM = 2       # Vertical transformation
VSTRETCHING = 5      # Vertical stretching
THETA_S = 5.0        # Surface stretching parameter
THETA_B = 4.0        # Bottom stretching parameter
HC = 100.0           # Critical depth for stretching
N = 40               # Number of vertical levels

# ---------------------------------------------------------------------------
# Define Functions for Initial Conditions
# ---------------------------------------------------------------------------
def zeta_function(x_rho, y_rho):
    """Define the free surface (zeta) as a function of horizontal coordinates."""
    return np.zeros_like(x_rho)

def ubar_function(x_u, y_u):
    """Define the 2D barotropic U-momentum (ubar) as a function of horizontal coordinates."""
    return np.zeros_like(x_u)

def vbar_function(x_v, y_v):
    """Define the 2D barotropic V-momentum (vbar) as a function of horizontal coordinates."""
    return 0.15*np.ones_like(x_v)

def u_function(x_u, y_u, z_r):
    """Define the 3D U-momentum (u) as a function of horizontal coordinates and depth."""
    return np.zeros_like(z_r)

def v_function(x_v, y_v, z_r):
    """Define the 3D V-momentum (v) as a function of horizontal coordinates and depth."""
    return 0.15*np.ones_like(z_r)

def temp_function(x_rho, y_rho, z_r):
    """Define the temperature (temp) as a function of horizontal coordinates and depth."""
    return 14.0 + 8.0 * np.exp(z_r / 50.0)  # z_r is negative

def salt_function(x_rho, y_rho, z_r):
    """Define the salinity (salt) as a function of horizontal coordinates and depth."""
    return np.zeros_like(z_r)#35.0 * np.ones_like(z_r)

# ---------------------------------------------------------------------------
# Create Initial Conditions File
# ---------------------------------------------------------------------------
def create_initial_conditions(grid_file, output_file):
    # Open the grid file and extract dimensions
    with nc.Dataset(grid_file, 'r') as grd:
        h = grd.variables['h'][:]         # Bathymetry
        x_rho = grd.variables['x_rho'][:]
        y_rho = grd.variables['y_rho'][:]
        x_u = grd.variables['x_u'][:]
        y_u = grd.variables['y_u'][:]
        x_v = grd.variables['x_v'][:]
        y_v = grd.variables['y_v'][:]
        xi_rho = len(grd.dimensions['xi_rho'])
        eta_rho = len(grd.dimensions['eta_rho'])
        xi_u = xi_rho - 1
        eta_u = eta_rho
        xi_v = xi_rho
        eta_v = eta_rho - 1

    # Compute vertical coordinates
    z_r = compute_z_r(h, HC, THETA_S, THETA_B, N)  # Depths at rho-points

    # Create the initial conditions NetCDF file
    with nc.Dataset(output_file, 'w', format='NETCDF4') as f:
        # Global attributes
        f.title = "ROMS Initial Conditions"
        f.history = "Created by create_initial_conditions_with_functions.py"
        f.description = "ROMS initial conditions with dynamic variable initialization."
        f.source = "Generated from grid file"

        # Dimensions
        f.createDimension('xi_rho', xi_rho)
        f.createDimension('eta_rho', eta_rho)
        f.createDimension('xi_u', xi_u)
        f.createDimension('eta_u', eta_u)
        f.createDimension('xi_v', xi_v)
        f.createDimension('eta_v', eta_v)
        f.createDimension('s_rho', N)
        f.createDimension('ocean_time', None)  # Unlimited time dimension

        # Variables

        # ocean_time
        ocean_time = f.createVariable('ocean_time', 'f8', ('ocean_time',))
        ocean_time.long_name = 'time since simulation start'
        ocean_time.units = 'seconds since 0001-01-01 00:00:00'
        ocean_time.calendar = '360.0 days in every year'
        ocean_time[0] = 0  # Set initial time to 0

        # zeta
        zeta = f.createVariable('zeta', 'f8', ('ocean_time', 'eta_rho', 'xi_rho'))
        zeta.long_name = 'free-surface'
        zeta.units = 'meter'
        zeta[0, :, :] = zeta_function(x_rho, y_rho)

        # ubar
        ubar = f.createVariable('ubar', 'f8', ('ocean_time', 'eta_u', 'xi_u'))
        ubar.long_name = 'vertically integrated u-momentum component'
        ubar.units = 'meter second-1'
        ubar[0, :, :] = ubar_function(x_u, y_u)

        # vbar
        vbar = f.createVariable('vbar', 'f8', ('ocean_time', 'eta_v', 'xi_v'))
        vbar.long_name = 'vertically integrated v-momentum component'
        vbar.units = 'meter second-1'
        vbar[0, :, :] = vbar_function(x_v, y_v)

        # Interpolate z_r to U-points and V-points
        z_r_u = 0.5 * (z_r[:, :, :-1] + z_r[:, :, 1:])  # Average over xi
        z_r_v = 0.5 * (z_r[:, :-1, :] + z_r[:, 1:, :])  # Average over eta

        # u
        u = f.createVariable('u', 'f8', ('ocean_time', 's_rho', 'eta_u', 'xi_u'))
        u.long_name = 'u-momentum component'
        u.units = 'meter second-1'
        u[0, :, :, :] = u_function(x_u, y_u, z_r_u)

        # v
        v = f.createVariable('v', 'f8', ('ocean_time', 's_rho', 'eta_v', 'xi_v'))
        v.long_name = 'v-momentum component'
        v.units = 'meter second-1'
        v[0, :, :, :] = v_function(x_v, y_v, z_r_v)

        # temp
        temp = f.createVariable('temp', 'f8', ('ocean_time', 's_rho', 'eta_rho', 'xi_rho'))
        temp.long_name = 'potential temperature'
        temp.units = 'Celsius'
        temp[0, :, :, :] = temp_function(x_rho, y_rho, z_r)

        # salt
        salt = f.createVariable('salt', 'f8', ('ocean_time', 's_rho', 'eta_rho', 'xi_rho'))
        salt.long_name = 'salinity'
        salt.units = 'PSU'
        salt[0, :, :, :] = salt_function(x_rho, y_rho, z_r)

    print(f"Initial conditions file '{output_file}' created successfully.")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create ROMS initial conditions file from a restart file.")
    parser.add_argument('--restart_file', default='input/testmix_rst.nc',
                        help="Path to the ROMS restart file (NetCDF format).")
    parser.add_argument('--output_file', default='input/testmix_ini.nc',
                        help="Path to the output initial conditions file (NetCDF format).")
    args = parser.parse_args()

    create_initial_conditions(args.restart_file, args.output_file)