#!/usr/bin/env python3
"""
create_boundary_conditions.py
Create a ROMS-compatible NetCDF file for boundary conditions (2D fields only).

This script reads a ROMS grid file and constructs a boundary condition file for free surface
(`zeta`) and 2D momentum (`ubar`, `vbar`). Boundary conditions are defined as functions of space
(and optionally time).

Usage:
    python create_boundary_conditions.py --grid_file testmix_grd.nc --output_file testmix_bry.nc
"""

import numpy as np
import netCDF4 as nc
import argparse

# ---------------------------------------------------------------------------
# Boundary Condition Functions
# ---------------------------------------------------------------------------
def zeta_boundary(x, y, boundary_name):
    """
    Define free-surface (zeta) boundary condition.
    """
    return np.zeros_like(x)

def ubar_boundary(x, y, boundary_name):
    """
    Define 2D U-momentum (ubar) boundary condition.
    """
    return np.zeros_like(x)  # No cross-boundary flow (example)

def vbar_boundary(x, y, boundary_name):
    """
    Define 2D V-momentum (vbar) boundary condition.
    """
    if boundary_name == 'south':
        return 0.15 * np.ones_like(x) 
    else:
        return np.zeros_like(x) 

# ---------------------------------------------------------------------------
# Create Boundary Condition File
# ---------------------------------------------------------------------------
def create_boundary_conditions(grid_file, output_file):
    # Open the grid file
    with nc.Dataset(grid_file, 'r') as grd:
        h = grd.variables['h'][:]
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

    # Create boundary condition file
    with nc.Dataset(output_file, 'w', format='NETCDF4') as ds:
        # Define dimensions
        ds.createDimension('xi_rho', xi_rho)
        ds.createDimension('eta_rho', eta_rho)
        ds.createDimension('xi_u', xi_u)
        ds.createDimension('eta_u', eta_u)
        ds.createDimension('xi_v', xi_v)
        ds.createDimension('eta_v', eta_v)
        ds.createDimension('bry_time', None)  # Unlimited time

        # Define bry_time variable
        bry_time = ds.createVariable('bry_time', 'f8', ('bry_time',))
        bry_time.long_name = 'time since simulation start'
        bry_time.units = 'seconds since 0001-01-01 00:00:00'
        bry_time.calendar = '360.0 days in every year'
        bry_time[0] = 0.0  # Set initial time to 0 seconds

        # Boundary mappings
        boundary_map = {
            'north': {
                'zeta': (x_rho[-1, :], y_rho[-1, :], 'xi_rho'),
                'ubar': (x_u[-1, :], y_u[-1, :], 'xi_u'),
                'vbar': (x_v[-1, :], y_v[-1, :], 'xi_v'),
            },
            'south': {
                'zeta': (x_rho[0, :], y_rho[0, :], 'xi_rho'),
                'ubar': (x_u[0, :], y_u[0, :], 'xi_u'),
                'vbar': (x_v[0, :], y_v[0, :], 'xi_v'),
            },
            'east': {
                'zeta': (x_rho[:, -1], y_rho[:, -1], 'eta_rho'),
                'ubar': (x_u[:, -1], y_u[:, -1], 'eta_u'),
                'vbar': (x_v[:, -1], y_v[:, -1], 'eta_v'),
            },
            'west': {
                'zeta': (x_rho[:, 0], y_rho[:, 0], 'eta_rho'),
                'ubar': (x_u[:, 0], y_u[:, 0], 'eta_u'),
                'vbar': (x_v[:, 0], y_v[:, 0], 'eta_v'),
            },
        }

        # Loop through boundaries
        for boundary_name, boundary_vars in boundary_map.items():
            # Free surface (zeta)
            zeta_x, zeta_y, zeta_dim = boundary_vars['zeta']
            zeta = zeta_boundary(zeta_x, zeta_y, boundary_name)
            zeta_var = ds.createVariable(f'zeta_{boundary_name}', 'f8', ('bry_time', zeta_dim))
            zeta_var.long_name = f'Free surface at {boundary_name} boundary'
            zeta_var.units = 'meter'
            zeta_var.time = 'bry_time'
            zeta_var[0, :] = zeta

            # 2D U-momentum (ubar)
            ubar_x, ubar_y, ubar_dim = boundary_vars['ubar']
            ubar = ubar_boundary(ubar_x, ubar_y, boundary_name)
            ubar_var = ds.createVariable(f'ubar_{boundary_name}', 'f8', ('bry_time', ubar_dim))
            ubar_var.long_name = f'2D u-momentum at {boundary_name} boundary'
            ubar_var.units = 'meter second-1'
            ubar_var.time = 'bry_time'
            ubar_var[0, :] = ubar

            # 2D V-momentum (vbar)
            vbar_x, vbar_y, vbar_dim = boundary_vars['vbar']
            vbar = vbar_boundary(vbar_x, vbar_y, boundary_name)
            vbar_var = ds.createVariable(f'vbar_{boundary_name}', 'f8', ('bry_time', vbar_dim))
            vbar_var.long_name = f'2D v-momentum at {boundary_name} boundary'
            vbar_var.units = 'meter second-1'
            vbar_var.time = 'bry_time'
            vbar_var[0, :] = vbar

    print(f"Boundary condition file '{output_file}' created successfully.")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create ROMS boundary condition file from a grid file.")
    parser.add_argument('--grid_file', default='input/testmix_grd.nc', 
                        help="Path to the ROMS grid file (NetCDF format).")
    parser.add_argument('--output_file', default='input/testmix_bry.nc',
                        help="Path to the output boundary condition file (NetCDF format).")
    args = parser.parse_args()

    create_boundary_conditions(args.grid_file, args.output_file)