# 3D-KAR reproducible revision workspace

## Current revision (2026-10-19)

See [current version and reproduction entry points](docs/current_version.md) for
the frozen v4 baseline, seven error-fold knowledge replays, and merged-result provenance.
The merged replay score is an analysis result, not a new end-to-end evaluation.

This repository contains the current 3D-KAR revision pipeline, frozen error-fold
definitions, knowledge replay tools, and an explicitly documented result-merging
utility. Model weights, benchmark files, generated predictions and temporary
experimental variants remain outside the published code snapshot.

## What is preserved

- Four routes: direct, basic 3D grounding, pose-aware, and bounding-box metric.
- Ovis2.5 visual extraction and final reasoning.
- Depth Pro metric depth and camera-centered back-projection.
- Pose-aware and bounding-box symbolic relation generation.
- The original 74 knowledge statements.

## What changes in the new main setting

- Route selection uses only the question text.
- The automatic router has no category/sub-category input, no answer options,
  and no lexical hard override.
- Knowledge is selected from an explicit route-to-knowledge map.
- Metadata routing remains available only as an oracle upper bound.
- One runner controls the full method and all ablations.
- Every run writes to its own directory using incremental JSONL output.

## Repository layout

```text
configs/                 experiment definitions
data/                    local data instructions and checksum
docs/experiment_plan.md  living revision checklist
knowledge/               74 rules and route mapping
scripts/                  experiment entry points
src/kar3d/               canonical implementation
tests/                    lightweight validation tests
outputs/                  ignored generated artifacts
```

## Server environment

The dependency versions in `requirements.txt` were read from the server's
`ovis` Conda environment. Depth Pro is installed from the local
`/root/autodl-tmp/ml-depth-pro` checkout on that server.

On the current server, the Ovis weights are under
`/root/autodl-fs/modelscope_cache/AIDC-AI/Ovis2___5-9B`, the Depth Pro
checkpoint is at `/root/autodl-tmp/ml-depth-pro/checkpoints/depth_pro.pt`,
and the dataset and images are under `/root/autodl-fs`. The experiment
configs contain these paths explicitly.

## Run examples

```bash
conda activate ovis
cd /root/autodl-tmp/paper-1-revision
export OMP_NUM_THREADS=8
python scripts/check_assets.py --config configs/auto_full.yaml
python scripts/run_routes.py --config configs/auto_full.yaml
python scripts/run_spatiallab.py --config configs/auto_full.yaml
python scripts/run_spatiallab.py --config configs/oracle_upper_bound.yaml
python scripts/run_spatiallab.py --config configs/fixed_basic.yaml
```

Automatic runs never receive `Category` or `Sub_Category`. These fields remain
in saved results only so route agreement and per-category accuracy can be
calculated after inference.
