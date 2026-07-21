import os
import subprocess

def main():
    # Define paths and options for compare_var.py
    compare_var_script = "analysis/compare_var.py"
    files = [
        "output/k-e_nostr_his.nc",
        "output/gen_nostr_his.nc",
        "output/k-e_str_C4_1.4_his.nc",
        "output/k-e_str_C4_0.6_his.nc"
    ]
    xy_file = "input/idealized_grid_input.txt"
    variable = "AKt"

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
    compare_dvar_script = "analysis/compare_dvar.py"
    variable = "AKt"
    baseline_reference = "output/k-e_nostr_his.nc"
    baseline_parametrized = [
        "output/k-e_str_C4_0.6_his.nc",
        "output/k-e_str_C4_1.4_his.nc"
    ]
    reference = "output/gen_nostr_his.nc"
    c4_list = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
    parametrized = [
        f"output/gen_str_C4_{c4}_his.nc" for c4 in c4_list
    ]
    xy_file = "input/idealized_grid_input.txt"

    # Command for running compare_dvar.py with multiple comparison files
    compare_dvar_command = [
        "python",
        compare_dvar_script,
        "--variable", variable,
        "--baseline_reference", baseline_reference,
        "--baseline_parametrized", *baseline_parametrized,
        "--reference", reference,
        "--parametrized", *parametrized,
        "--xy_file", xy_file
    ]

    print(f"Running: {' '.join(compare_dvar_command)}")
    subprocess.run(compare_dvar_command)


if __name__ == "__main__":
    main()