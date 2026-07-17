import sys
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import os

def compute_volume_average_xarray(file_path):
    """
    Compute the volume average of TKE over x, y, and depth dimensions using xarray.
    """
    try:
        # Open the NetCDF file using xarray
        dataset = xr.open_dataset(file_path)
        
        # Assume TKE is stored in a variable named 'tke'
        # Adjust the variable name if it's different in your file
        if "tke" not in dataset:
            raise ValueError(f"'tke' variable not found in {file_path}")
        
        tke = dataset["tke"]  # Select the TKE variable
        
        # Compute the volume average over 'x', 'y', and 'depth'
        volume_avg_tke = tke.mean(dim=["s_w", "eta_rho", "xi_rho"])
        
        
        # Close the dataset
        dataset.close()
        
        return volume_avg_tke
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None

def main():
    # Ensure at least one NetCDF file is provided as a command line argument
    if len(sys.argv) < 2:
        print("Usage: python script.py <file1.nc> <file2.nc> ...")
        sys.exit(1)
    
    # Get file paths from command line arguments
    file_paths = sys.argv[1:]
    
    # Initialize a list to store time series data
    time_series_data = []
    
    # Process each file
    for file_path in file_paths:
        print(f"Processing file: {file_path}")
        volume_avg_tke = compute_volume_average_xarray(file_path)
        if volume_avg_tke is not None:
            # Extract the file name without folder path and '.nc' extension
            file_label = os.path.basename(file_path).replace(".nc", "")
            time_series_data.append((file_label, volume_avg_tke))
    
    # Plot the time series
    if time_series_data:
        fig, ax = plt.subplots(figsize=(10, 6))

        for label, time_series in time_series_data:
            ax.plot(time_series, label=label)
        
        ax.set_xlabel("Time Step")
        ax.set_ylabel("TKE")
        ax.set_title("Time series of grid-averaged TKE")
        ax.legend()
        ax.grid()
        fig.savefig("figures/compare_tke.png")
    else:
        print("No valid data to plot.")

if __name__ == "__main__":
    main()