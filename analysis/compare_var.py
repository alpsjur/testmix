import argparse
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import os

from utils import compute_volume_average

"""
Usage:
    python script.py <file1.nc> <file2.nc> ... \
        --variable <variable_name> \
        [--xy_file <xy_file.txt>]
"""

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Compute and plot the volume average of a specified variable from NetCDF files."
    )
    parser.add_argument(
        "files",
        metavar="file",
        type=str,
        nargs="+",
        help="NetCDF files to process (e.g., file1.nc file2.nc ...)",
    )
    parser.add_argument(
        "-v",
        "--variable",
        required=True,
        type=str,
        help="Variable name to compute the volume average for (e.g., 'tke').",
    )
    parser.add_argument(
        "-xy",
        "--xy_file",
        type=str,
        help="Optional text file specifying x-y indices for subsetting the domain.",
    )

    args = parser.parse_args()

    file_paths = args.files
    variable = args.variable
    xy_file = args.xy_file

    # Initialize a list to store time series data
    time_series_data = []

    # Process each file
    for file_path in file_paths:
        print(f"Processing file: {file_path}")
        dataset = xr.open_dataset(file_path)
        volume_avg = compute_volume_average(dataset, variable, xy_file)
        if volume_avg is not None:
            # Extract the file name without folder path and '.nc' extension
            file_label = os.path.basename(file_path).replace(".nc", "")
            time_series_data.append((file_label, volume_avg))

    # Plot the time series
    if time_series_data:
        fig, ax = plt.subplots(figsize=(10, 6))

        for label, time_series in time_series_data:
            ax.plot(time_series, label=label)

        ax.set_xlabel("Time Step")
        ax.set_ylabel(variable)
        ax.set_title(f"Time series of grid-averaged {variable}")
        ax.legend()
        ax.grid()
        os.makedirs("figures", exist_ok=True)
        fig.savefig(f"figures/compare_{variable}.png")
    else:
        print("No valid data to plot.")


if __name__ == "__main__":
    main()