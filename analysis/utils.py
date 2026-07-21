import xarray as xr
import numpy as np

def compute_layer_thickness(dataset):
    """
    Compute the layer thickness for each cell using z_rho, zeta, and h.
    Supports both s_rho (cell centers) and s_w (cell edges).

    Parameters:
        dataset (xarray.Dataset): The dataset containing z_rho, zeta, and h.

    Returns:
        xarray.DataArray: A DataArray representing layer thickness for each model level.
    """
    try:
        # Extract necessary variables as NumPy arrays
        z_rho = dataset["z_rho"].values  # Depth at cell centers
        zeta = dataset["zeta"].values    # Sea surface height
        h = dataset["h"].values          # Bathymetry

        # Get dimensions
        ocean_time, s_rho, eta_rho, xi_rho = z_rho.shape

        # Initialize z_w (one more vertical level than z_rho)
        z_w = np.zeros((ocean_time, s_rho + 1, eta_rho, xi_rho))

        # Bottom edge (cell bottom at the seafloor)
        z_w[:, 0, :, :] = -h

        # Mid-level edges (average between adjacent z_rho levels)
        z_w[:, 1:-1, :, :] = 0.5 * (z_rho[:, :-1, :, :] + z_rho[:, 1:, :, :])

        # Top edge (cell top at the free surface)
        z_w[:, -1, :, :] = zeta

        # Compute layer thickness (difference between adjacent z_w levels)
        dz = np.diff(z_w, axis=1)  # Thickness between edges

        # Convert back to xarray.DataArray
        dz_da = xr.DataArray(
            data=dz,
            dims=["ocean_time", "s_rho", "eta_rho", "xi_rho"],
            coords={
                "ocean_time": dataset["z_rho"].coords["ocean_time"],
                "s_rho": dataset["z_rho"].coords["s_rho"],
                "x_rho": dataset["z_rho"].coords["x_rho"],
                "y_rho": dataset["z_rho"].coords["y_rho"],
            },
            name="layer_thickness",
        )

        return dz_da
    except Exception as e:
        raise ValueError(f"Error computing layer thickness: {e}")


def compute_volume_average(dataset, variable, xy_file=None):
    """
    Compute the volume average of the specified variable over x, y, and depth dimensions using xarray.
    If an xy_file is provided, only average over the specified x-y domain.
    Automatically determines whether to use 's_w' or 's_rho' as the vertical dimension.
    """
    try:
        # Check if the specified variable exists in the dataset
        if variable not in dataset:
            raise ValueError(f"'{variable}' variable not found in file")

        data_var = dataset[variable]  # Select the specified variable

        # Determine the vertical dimension ('s_w' or 's_rho') based on availability
        if "s_w" in data_var.dims:
            # Interpolate variable from s_w levels to s_rho levels using NumPy
            data_var_np = data_var.values  # Convert to NumPy array
            data_var_interp_np = 0.5 * (data_var_np[:, :-1, :, :] + data_var_np[:, 1:, :, :])  # Average neighboring levels

            # Convert back to xarray.DataArray
            data_var_interp = xr.DataArray(
                data=data_var_interp_np,
                dims=["ocean_time", "s_rho", "eta_rho", "xi_rho"],
                coords={
                    "ocean_time": data_var.coords["ocean_time"],
                    "s_rho": dataset["z_rho"].coords["s_rho"],  # Use s_rho coordinates
                    "x_rho": data_var.coords["x_rho"],
                    "y_rho": data_var.coords["y_rho"],
                },
            )
        elif "s_rho" in data_var.dims:
            data_var_interp = data_var  # Already on s_rho levels, no interpolation needed
        else:
            raise ValueError(
                f"Neither 's_w' nor 's_rho' found as a vertical dimension for variable '{variable}' in {file_path}. "
                f"Available dimensions: {list(data_var.dims)}"
            )

        # Compute the layer thickness
        dz = compute_layer_thickness(dataset)

        # If an xy_file is provided, read the x-y values and subset the dataset
        if xy_file:
            x_vals, y_vals = np.loadtxt(xy_file, unpack=True)
            x_vals = x_vals.astype(int)  # Convert to integer indices
            y_vals = y_vals.astype(int)

            # Ensure the indices are within bounds
            x_vals = np.clip(x_vals, 0, data_var.sizes["xi_rho"] - 1)
            y_vals = np.clip(y_vals, 0, data_var.sizes["eta_rho"] - 1)

            # Subset the dataset to the specified x-y domain
            data_subset = data_var_interp.isel(
                xi_rho=xr.DataArray(x_vals, dims="points"),
                eta_rho=xr.DataArray(y_vals, dims="points"),
            )
            dz_subset = dz.isel(
                xi_rho=xr.DataArray(x_vals, dims="points"),
                eta_rho=xr.DataArray(y_vals, dims="points"),
            )

            # Compute the volume-weighted average
            volume_avg = (data_subset * dz_subset).sum(dim=["s_rho", "points"]) / dz_subset.sum(dim=["s_rho", "points"])
        else:
            # Compute the volume-weighted average over the entire domain
            volume_avg = (data_var_interp * dz).sum(dim=["s_rho", "eta_rho", "xi_rho"]) / dz.sum(dim=["s_rho", "eta_rho", "xi_rho"])

        # Close the dataset
        dataset.close()

        return volume_avg
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None