import argparse
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import os
from utils import compute_volume_average

"""
Usage:
    python compare_dvar.py --variable <variable_name> --baseline_file1 <file1.nc> --baseline_file2 <file2.nc>
                           --param_file_pattern <pattern> --reference_file <file.nc> [--gls_c4_values <values>]
                           [--xy_file <xy_file.txt>]

Examples:
    # Compute ΔTKE for baseline files and parameterized files with default GLS_C4 values
    python compare_dvar.py --variable tke \
                           --baseline_file1 output/k-e_str_C4_1.4_his.nc \
                           --baseline_file2 output/k-e_nostr_his.nc \
                           --param_file_pattern "output/gen_str_C4_{GLS_C4}_his.nc" \
                           --reference_file output/gen_nostr_his.nc \
                           --xy_file input/idealized_grid_input.txt

    # Get help
    python script.py --help
"""

def compute_variable_difference(file1, file2, variable, xy_file=None):
    """
    Compute the difference in the volume average of a specified variable between two files.

    Parameters:
        file1 (str): Path to the first NetCDF file.
        file2 (str): Path to the second NetCDF file.
        variable (str): The name of the variable to compute the difference for.
        xy_file (str): Optional path to a file specifying x-y indices for subsetting the domain.

    Returns:
        xarray.DataArray: The difference in the volume-averaged variable for each time step.
    """
    try:
        # Open both files using xarray
        ds1 = xr.open_dataset(file1)
        ds2 = xr.open_dataset(file2)

        # Compute the volume averages for both files
        avg1 = compute_volume_average(ds1, variable, xy_file)
        avg2 = compute_volume_average(ds2, variable, xy_file)

        # Compute the difference in volume averages
        dvar = avg1 - avg2

        # Close the datasets
        ds1.close()
        ds2.close()

        return dvar
    except Exception as e:
        print(f"Error computing variable difference for '{variable}': {e}")
        return None


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Compute and plot the difference in a specified variable (e.g., ΔTKE) between NetCDF files."
    )
    parser.add_argument(
        "-v", "--variable",
        required=True,
        type=str,
        help="Variable name to compute the difference for (e.g., 'tke')."
    )
    parser.add_argument(
        "--baseline_file1",
        required=True,
        type=str,
        help="Path to the first baseline NetCDF file."
    )
    parser.add_argument(
        "--baseline_file2",
        required=True,
        type=str,
        help="Path to the second baseline NetCDF file."
    )
    parser.add_argument(
        "--param_file_pattern",
        default='output/gen_str_C4_{GLS_C4}_his.nc',
        type=str,
        help="Pattern for parameterized NetCDF files. Default 'output/gen_str_C4_{GLS_C4}_his.nc'."
    )
    parser.add_argument(
        "--reference_file",
        required=True,
        type=str,
        help="Path to the reference NetCDF file."
    )
    parser.add_argument(
        "--gls_c4_values",
        nargs="+",
        type=float,
        default=[0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
        help="List of GLS_C4 values to use for parameterized files. Default: [0.2, 0.3, ..., 1.5]."
    )
    parser.add_argument(
        "--xy_file",
        type=str,
        help="Optional text file specifying x-y indices for subsetting the domain."
    )

    args = parser.parse_args()

    # Extract arguments
    variable = args.variable
    baseline_file1 = args.baseline_file1
    baseline_file2 = args.baseline_file2
    param_file_pattern = args.param_file_pattern
    reference_file = args.reference_file
    GLS_C4_VALUES = args.gls_c4_values
    xy_file = args.xy_file

    # Plotting
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Compute and plot baseline ΔVariable
    print(f"Computing Δ{variable} for baseline files: {baseline_file1} and {baseline_file2}")
    baseline_dvar = compute_variable_difference(baseline_file1, baseline_file2, variable, xy_file)
    if baseline_dvar is not None:
        ax.plot(baseline_dvar, label=f"Baseline Δ{variable}", linewidth=3, color="black")
    
    # Compute and plot ΔVariable for parameterized files
    for GLS_C4 in GLS_C4_VALUES:
        file1 = param_file_pattern.format(GLS_C4=GLS_C4)
        print(f"Computing Δ{variable} for file: {file1} and reference: {reference_file}")
        dvar = compute_variable_difference(file1, reference_file, variable, xy_file)
        if dvar is not None:
            label = f"Δ{variable} (GLS_C4={GLS_C4})"
            ax.plot(dvar, label=label)
    
    # Finalize the plot
    ax.set_xlabel("Time Step")
    ax.set_ylabel(f"Δ{variable}")
    ax.set_title(f"Time Series of Δ{variable}")
    ax.legend()
    ax.grid()
    os.makedirs("figures", exist_ok=True)
    fig.savefig(f"figures/compare_d{variable}.png")

if __name__ == "__main__":
    main()