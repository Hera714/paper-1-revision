# 3D-KAR reproducible revision workspace

This is a clean local extraction of the code needed for the next 3D-KAR
experiments. It intentionally excludes abandoned scripts, partial outputs,
manual result-merging utilities, and duplicated variants from the old working
directory.

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

## Run examples

```bash
conda activate ovis
cd /root/autodl-tmp/3dkar-repro-v2
python scripts/run_routes.py --config configs/auto_full.yaml
python scripts/run_spatiallab.py --config configs/auto_full.yaml
python scripts/run_spatiallab.py --config configs/oracle_upper_bound.yaml
python scripts/run_spatiallab.py --config configs/fixed_basic.yaml
```

Automatic runs never receive `Category` or `Sub_Category`. These fields remain
in saved results only so route agreement and per-category accuracy can be
calculated after inference.
