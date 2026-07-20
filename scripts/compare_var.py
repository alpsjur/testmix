import argparse
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import os

"""
Usage:
    python script.py <file1.nc> <file2.nc> ... \
        --variable <variable_name> \
        [--xy_file <xy_file.txt>]

Examples:

    python scripts/compare_var.py output/k-e_nostr_his.nc \
        output/gen_nostr_his.nc output/k-e_str_C4_1.4_his.nc \
        output/k-e_str_C4_0.6_his.nc \
        --variable AKt \
        --xy_file input/idealized_grid_input.txt

    # Get help on how to use the script
    python script.py --help
"""


def compute_volume_average_xarray(file_path, variable, xy_file=None):
    """
    Compute the volume average of the specified variable over x, y, and depth dimensions using xarray.
    If an xy_file is provided, only average over the specified x-y domain.
    """
    try:
        # Open the NetCDF file using xarray
        dataset = xr.open_dataset(file_path)

        # Check if the specified variable exists in the dataset
        if variable not in dataset:
            raise ValueError(f"'{variable}' variable not found in {file_path}")

        data_var = dataset[variable]  # Select the specified variable

        # If an xy_file is provided, read the x-y values and subset the dataset
        if xy_file:
            x_vals, y_vals = np.loadtxt(xy_file, unpack=True)
            x_vals = x_vals.astype(int)  # Convert to integer indices
            y_vals = y_vals.astype(int)

            # Ensure the indices are within bounds
            x_vals = np.clip(x_vals, 0, data_var.sizes["xi_rho"] - 1)
            y_vals = np.clip(y_vals, 0, data_var.sizes["eta_rho"] - 1)

            # Subset the dataset to the specified x-y domain
            data_subset = data_var.isel(
                xi_rho=xr.DataArray(x_vals, dims="points"),
                eta_rho=xr.DataArray(y_vals, dims="points"),
            )

            # Compute the mean over the subset
            volume_avg = data_subset.mean(dim=["s_w", "points"])
        else:
            # Compute the volume average over the entire domain
            volume_avg = data_var.mean(dim=["s_w", "eta_rho", "xi_rho"])

        # Close the dataset
        dataset.close()

        return volume_avg
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None


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
        volume_avg = compute_volume_average_xarray(file_path, variable, xy_file)
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