import argparse
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import os
from utils import compute_volume_average

"""
Usage:
    python compare_dvar.py --variable <variable_name> 
                           --baseline_reference <baseline_reference_file.nc> 
                           --baseline_parametrized <baseline_file1.nc> <baseline_file2.nc> ...
                           --reference <reference_file.nc> 
                           --parametrized <param_file1.nc> <param_file2.nc> ...
                           [--xy_file <xy_file.txt>]

Examples:
    # Compute ΔTKE for multiple baseline_parametrized and parametrized files
    python compare_dvar.py --variable tke \
                           --baseline_reference output/k-e_nostr_his.nc \
                           --baseline_parametrized output/k-e_str_C4_1.4_his.nc output/k-e_str_C4_0.6_his.nc \
                           --reference output/gen_nostr_his.nc \
                           --parametrized output/gen_str_C4_1.0_his.nc output/gen_str_C4_1.2_his.nc \
                           --xy_file input/idealized_grid_input.txt

    # Get help
    python compare_dvar.py --help
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
        "--baseline_reference",
        required=True,
        type=str,
        help="Path to the reference baseline NetCDF file."
    )
    parser.add_argument(
        "--baseline_parametrized",
        required=True,
        nargs="+",
        type=str,
        help="Paths to one or more baseline parametrized NetCDF files."
    )
    parser.add_argument(
        "--reference",
        required=True,
        type=str,
        help="Path to the reference NetCDF file."
    )
    parser.add_argument(
        "--parametrized",
        required=True,
        nargs="+",
        type=str,
        help="Paths to one or more parametrized NetCDF files."
    )
    parser.add_argument(
        "--xy_file",
        type=str,
        help="Optional text file specifying x-y indices for subsetting the domain."
    )

    args = parser.parse_args()

    # Extract arguments
    variable = args.variable
    baseline_reference = args.baseline_reference
    baseline_parametrized = args.baseline_parametrized
    parametrized = args.parametrized
    reference = args.reference
    xy_file = args.xy_file

    # Plotting
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Compute and plot ΔVariable for each baseline_parametrized file

    linestyles = ["-", "--", "-."]
    for i, baseline_file in enumerate(baseline_parametrized):
        print(f"Computing Δ{variable} for baseline files: {baseline_file} and {baseline_reference}")
        baseline_dvar = compute_variable_difference(baseline_file, baseline_reference, variable, xy_file)
        if baseline_dvar is not None:
            label = f"{os.path.basename(baseline_file)}"
            ax.plot(baseline_dvar, label=label, linewidth=3, color="black", ls=linestyles[i])
    
    # Compute and plot ΔVariable for parameterized files
    for i, file in enumerate(parametrized):
        print(f"Computing Δ{variable} for file: {file} and reference: {reference}")
        dvar = compute_variable_difference(file, reference, variable, xy_file)
        if dvar is not None:
            label = f"{os.path.basename(file)}"
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