#!/bin/bash
# run_add_str_a.sh  –  Example: add str_a to the norkyst grid file.
#
# The script copies norkyst_grd.nc to norkyst_grd_with_str_a.nc and then
# applies str_a_input_example.txt to the copy so the original is untouched.
#
# Vertical coordinate parameters match typical NorKyst settings:
#   Vtransform=2, Vstretching=5, theta_s=5.0, theta_b=4.0, hc=50.0, N=35
# Adjust if your run configuration differs.

set -e

GRID_IN="norkyst_grd.nc"
GRID_OUT="norkyst_grd_with_str_a.nc"
INPUT_FILE="str_a_input_example.txt"

echo "Copying ${GRID_IN} -> ${GRID_OUT} ..."
cp "${GRID_IN}" "${GRID_OUT}"

echo "Running add_str_a.py ..."
python3 add_str_a.py "${GRID_OUT}" "${INPUT_FILE}" \
    --N 35          \
    --theta_s 5.0   \
    --theta_b 4.0   \
    --hc 50.0       \
    --vtransform 2  \
    --vstretching 5

echo ""
echo "Output grid: ${GRID_OUT}"
