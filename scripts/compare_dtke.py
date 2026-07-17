import sys
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

def compute_tke_difference(file1, file2):
    """
    Compute the difference in TKE (ΔTKE) between two files.
    """
    try:
        # Open both files using xarray
        ds1 = xr.open_dataset(file1)
        ds2 = xr.open_dataset(file2)
        
        # Ensure both files contain the 'tke' variable
        if "tke" not in ds1 or "tke" not in ds2:
            raise ValueError(f"'tke' variable not found in one or both files: {file1}, {file2}")
        
        # Extract TKE variables
        tke1 = ds1["tke"]  # From file1
        tke2 = ds2["tke"]  # From file2
        
        # Compute the difference (ΔTKE)
        dtke = (tke1 - tke2).mean(dim=["s_w", "eta_rho", "xi_rho"]).values
        
        # Close the datasets
        ds1.close()
        ds2.close()
        
        return dtke
    except Exception as e:
        print(f"Error processing files {file1} and {file2}: {e}")
        return None

def main():
    # Baseline files
    baseline_file1 = "output/k-e_str_GLS_C4_0.6_his.nc"
    baseline_file2 = "output/k-e_nostr_his.nc"
    
    # Parameterized files
    GLS_C4_VALUES = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
    param_file_pattern = "output/gen_str_GLS_C4_{GLS_C4}_his.nc"
    reference_file = "output/gen_nostr_his.nc"
    
    # Plotting
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Compute and plot baseline ΔTKE
    print(f"Computing ΔTKE for baseline files: {baseline_file1} and {baseline_file2}")
    baseline_dtke = compute_tke_difference(baseline_file1, baseline_file2)
    if baseline_dtke is not None:
        ax.plot(baseline_dtke, label="Baseline ΔTKE", linewidth=3, color="black")
    
    # Compute and plot ΔTKE for parameterized files
    for GLS_C4 in GLS_C4_VALUES:
        file1 = param_file_pattern.format(GLS_C4=GLS_C4)
        print(f"Computing ΔTKE for file: {file1} and reference: {reference_file}")
        dtke = compute_tke_difference(file1, reference_file)
        if dtke is not None:
            label = f"ΔTKE (GLS_C4={GLS_C4})"
            ax.plot(dtke, label=label)
    
    # Finalize the plot
    ax.set_xlabel("Time Step")
    ax.set_ylabel("ΔTKE")
    ax.set_title("Time Series of ΔTKE")
    ax.legend()
    ax.grid()
    fig.savefig("figures/compare_dtke.png")

if __name__ == "__main__":
    main()