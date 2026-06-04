#!/usr/bin/env bash
#SBATCH -J plantrg_protein_clean
#SBATCH --mem=150G
#SBATCH -o model_project/data_cleaning/logs/protein_cleaning_%j.out
#SBATCH -e model_project/data_cleaning/logs/protein_cleaning_%j.err

set -euo pipefail

cd /home/user/zhangzhishuai/data/plantDB/PlantRG

mkdir -p model_project/data_cleaning/results model_project/data_cleaning/logs

mamba run -n bio3 python model_project/data_cleaning/scripts/build_protein_positive_set.py \
  --manifest metadata/plantrg_full_manifest.csv \
  --protein-dir downloads/sequences/protein \
  --outdir model_project/data_cleaning/results
