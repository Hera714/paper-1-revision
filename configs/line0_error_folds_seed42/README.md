# line0 error sample folds

- Baseline: auto_revision_v4_seed42
- Route: line0_pure_vlm
- Selection: selected_route=line0_pure_vlm, status=ok, is_correct=false
- Split: random.Random(42) shuffle followed by round-robin assignment
- Target fold size: about 50

## Files

- folds.json: source hash, selection rule, fold metadata, and category counts.
- all_error_ids.ids: all selected error IDs.
- errors.jsonl: full extracted prediction records.
- fold1.ids: 48 IDs.
- fold2.ids: 48 IDs.
- fold3.ids: 48 IDs.
- fold4.ids: 48 IDs.
- fold5.ids: 48 IDs.
- fold6.ids: 48 IDs.

## Fold statistics

| Fold | Count | Categories |
|---|---:|---|
| fold1 | 48 | 3D Geometry: 10; Depth & Occlusion: 18; Orientation: 3; Relative Positioning: 1; Size & Scale: 5; Spatial Navigation: 11 |
| fold2 | 48 | 3D Geometry: 12; Depth & Occlusion: 12; Orientation: 1; Relative Positioning: 4; Size & Scale: 11; Spatial Navigation: 8 |
| fold3 | 48 | 3D Geometry: 10; Depth & Occlusion: 15; Orientation: 4; Relative Positioning: 1; Size & Scale: 6; Spatial Navigation: 12 |
| fold4 | 48 | 3D Geometry: 6; Depth & Occlusion: 17; Orientation: 5; Size & Scale: 6; Spatial Navigation: 14 |
| fold5 | 48 | 3D Geometry: 10; Depth & Occlusion: 13; Orientation: 3; Relative Positioning: 4; Size & Scale: 7; Spatial Navigation: 11 |
| fold6 | 48 | 3D Geometry: 6; Depth & Occlusion: 18; Orientation: 2; Size & Scale: 6; Spatial Navigation: 16 |
