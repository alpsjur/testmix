import os
import subprocess

def main():
    # Define paths and options for compare_var.py
    compare_var_script = "scripts/compare_var.py"
    files = [
        "output/k-e_nostr_his.nc",
        "output/gen_nostr_his.nc",
        "output/k-e_str_C4_1.4_his.nc",
        "output/k-e_str_C4_0.6_his.nc"
    ]
    xy_file = "input/idealized_grid_input.txt"
    variable = "rho" 

    # Command for running compare_var.py
    compare_var_command = [
        "python",
        compare_var_script,
        *files,
        "--variable", variable,
        "--xy_file", xy_file
    ]

    print(f"Running: {' '.join(compare_var_command)}")
    subprocess.run(compare_var_command)

    # Define paths and options for compare_dvar.py
    compare_dvar_script = "scripts/compare_dvar.py"
    variable = "rho" 
    baseline_file1 = "output/k-e_str_C4_0.6_his.nc"
    baseline_file2 = "output/k-e_nostr_his.nc"
    param_file_pattern = "output/gen_str_C4_{GLS_C4}_his.nc"
    reference_file = "output/gen_nostr_his.nc"
    xy_file = "input/idealized_grid_input.txt"
    gls_c4_values = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]

    # Command for running compare_dvar.py
    compare_dvar_command = [
        "python",
        compare_dvar_script,
        "--variable", variable,
        "--baseline_file1", baseline_file1,
        "--baseline_file2", baseline_file2,
        "--param_file_pattern", param_file_pattern,
        "--reference_file", reference_file,
        "--xy_file", xy_file,
        "--gls_c4_values", *map(str, gls_c4_values)
    ]

    print(f"Running: {' '.join(compare_dvar_command)}")
    subprocess.run(compare_dvar_command)

if __name__ == "__main__":
    main()