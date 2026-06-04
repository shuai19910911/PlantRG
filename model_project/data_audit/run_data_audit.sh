#!/usr/bin/env bash
#SBATCH -p q07
#SBATCH -c 30
#SBATCH --mem=150G
#SBATCH -J plantrg_data_audit
#SBATCH -o model_project/data_audit/logs/%x_%j.out
#SBATCH -e model_project/data_audit/logs/%x_%j.err

set -euo pipefail

cd /home/user/zhangzhishuai/data/plantDB/PlantRG
mkdir -p model_project/data_audit/logs model_project/data_audit/results

mamba run -n bio3 python model_project/data_audit/scripts/audit_plantrg_sequences.py \
  --manifest metadata/plantrg_full_manifest.csv \
  --seq-root downloads/sequences \
  --outdir model_project/data_audit/results \
  --threads "${SLURM_CPUS_PER_TASK:-30}"

