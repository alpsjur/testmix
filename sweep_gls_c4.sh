#!/bin/bash

# Define the range of GLS_C4 values
GLS_C4_VALUES=(0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0 1.1 1.2 1.3 1.4 1.5)

# Base input file
BASE_INPUT_FILE="testmix.in"

# Backup the original input file
cp $BASE_INPUT_FILE "${BASE_INPUT_FILE}.bak"

# Loop through the GLS_C4 values
for GLS_C4 in "${GLS_C4_VALUES[@]}"; do
    # Create a unique output file name
    OUTPUT_HISNAME="output/gen_str_C4_${GLS_C4}_his.nc"

    # Modify the input file
    # Replace GLS_C4 placeholder
    sed -e "s/GLS_C4 == .*/GLS_C4 == ${GLS_C4}/" \
        -e "s|HISNAME == .*|HISNAME == ${OUTPUT_HISNAME}|" \
        "${BASE_INPUT_FILE}.bak" > $BASE_INPUT_FILE

    # Run the ROMS model
    echo "Running ROMS with C4=${GLS_C4}..."
    ./romsS_str < $BASE_INPUT_FILE > "logs/gen_str_C4_${GLS_C4}.log"

    # Check if the run was successful
    if [ $? -ne 0 ]; then
        echo "Run failed for C4=${GLS_C4}. Check the log file."
    else
        echo "Run completed for C4=${GLS_C4}. Output: ${OUTPUT_HISNAME}"
    fi
done

# Restore the original input file
mv "${BASE_INPUT_FILE}.bak" $BASE_INPUT_FILE

echo "Parameter sweep completed."