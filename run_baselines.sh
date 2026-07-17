#!/bin/bash

# run baseline gen turbulence closure without structure-induced mixing
./romsS_nostr < testmix.in > "logs/gen_nostr.log"
mv output/roms_his.nc output/gen_nostr_his.nc 

# run baseline k-e turbulence closure without structure-induced mixing
./romsS_nostr < testmix_k-e_GLS_C4_0.6.in > "logs/k-e_nostr.log"
mv output/k-e_GLS_C4_0.6_his.nc output/k-e_nostr_his.nc 

# run k-e turbulence closure with strong mixing
./romsS_str < testmix_k-e_GLS_C4_0.6.in > "logs/k-e_str_GLS_C4_0.6.log"

# run k-e turbulence closure with weak mixing
./romsS_str < testmix_k-e_GLS_C4_1.4.in > "logs/k-e_str_GLS_C4_1.4.log"

