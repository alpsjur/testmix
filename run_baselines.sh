#!/bin/bash

# Define experiments
EXPERIMENTS=(
    "gen_nostr"     # GEN turbulence without structure-induced mixing
    "k-e_nostr"     # k-e turbulence without structure-induced mixing
    "k-e_str_weak"  # k-e turbulence with weak structure-induced mixing
    "k-e_str_strong" # k-e turbulence with strong structure-induced mixing
)

# Base input file
BASE_INPUT_FILE="testmix.in"

# Backup the original input file
cp $BASE_INPUT_FILE "${BASE_INPUT_FILE}.bak"

# Function to modify the testmix.in file
modify_input_file() {
    local turbulence_type=$1
    local enable_str=$2
    local GLS_C4=$3
    local output_file=$4

    # Restore the original input file
    cp "${BASE_INPUT_FILE}.bak" $BASE_INPUT_FILE

    # Update turbulence parameters based on type
    if [ "$turbulence_type" == "k-e" ]; then
        sed -i "s/^ *GLS_P == .*/       GLS_P == 3.0d0/" $BASE_INPUT_FILE
        sed -i "s/^ *GLS_M == .*/       GLS_M == 1.5d0/" $BASE_INPUT_FILE
        sed -i "s/^ *GLS_N == .*/       GLS_N == -1.0d0/" $BASE_INPUT_FILE
        sed -i "s/^ *GLS_SIGK == .*/       GLS_SIGK == 1.0d0/" $BASE_INPUT_FILE
        sed -i "s/^ *GLS_SIGP == .*/       GLS_SIGP == 1.3d0/" $BASE_INPUT_FILE
        sed -i "s/^ *GLS_C1 == .*/       GLS_C1 == 1.44d0/" $BASE_INPUT_FILE
        sed -i "s/^ *GLS_C2 == .*/       GLS_C2 == 1.92d0/" $BASE_INPUT_FILE
        sed -i "s/^ *GLS_C3M == .*/       GLS_C3M == -0.4d0/" $BASE_INPUT_FILE
        sed -i "s/^ *GLS_CMU0 == .*/       GLS_CMU0 == 0.5477d0/" $BASE_INPUT_FILE
        sed -i "s/^ *GLS_Pmin == .*/       GLS_Pmin == 1.0d-12/" $BASE_INPUT_FILE
    fi
    # No changes for "gen" - keep original parameters

    # Enable or disable structure-induced mixing
    if [ "$enable_str" == "true" ]; then
        sed -i "s/^! *STR_CD/\      STR_CD/" $BASE_INPUT_FILE
    else
        sed -i "s/^ *STR_CD/!      STR_CD/" $BASE_INPUT_FILE
    fi

    # Update GLS_C4 parameter
    sed -i "s/^ *GLS_C4 == .*/       GLS_C4 == ${GLS_C4}d0/" $BASE_INPUT_FILE

    # Update output file name
    sed -i "s|HISNAME == .*|HISNAME == ${output_file}|" $BASE_INPUT_FILE
}

# Run the experiments
for experiment in "${EXPERIMENTS[@]}"; do
    case $experiment in
        "gen_nostr")
            echo "Running GEN turbulence without structure-induced mixing..."
            modify_input_file "gen" "false" 0.6 "output/gen_nostr_his.nc"
            ./romsS_nostr < $BASE_INPUT_FILE > "logs/gen_nostr.log"
            ;;
        "k-e_nostr")
            echo "Running k-e turbulence without structure-induced mixing..."
            modify_input_file "k-e" "false" 0.6 "output/k-e_nostr_his.nc"
            ./romsS_nostr < $BASE_INPUT_FILE > "logs/k-e_nostr.log"
            ;;
        "k-e_str_weak")
            echo "Running k-e turbulence with weak structure-induced mixing..."
            modify_input_file "k-e" "true" 1.4 "output/k-e_str_weak_his.nc"
            ./romsS_str < $BASE_INPUT_FILE > "logs/k-e_str_weak.log"
            ;;
        "k-e_str_strong")
            echo "Running k-e turbulence with strong structure-induced mixing..."
            modify_input_file "k-e" "true" 0.6 "output/k-e_str_strong_his.nc"
            ./romsS_str < $BASE_INPUT_FILE > "logs/k-e_str_strong.log"
            ;;
    esac

    # Check if the run was successful
    if [ $? -ne 0 ]; then
        echo "Run failed for experiment: $experiment. Check the log file."
    else
        echo "Run completed for experiment: $experiment."
    fi
done

# Restore the original input file
mv "${BASE_INPUT_FILE}.bak" $BASE_INPUT_FILE

echo "All experiments completed."