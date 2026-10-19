# line1_base error sample folds

- Baseline: auto_revision_v4_seed42
- Route: line1_base
- Selection: selected_route=line1_base, status=ok, is_correct=false
- Split: random.Random(42) shuffle followed by round-robin assignment
- Target fold size: about 50

## Files

- folds.json: source hash, selection rule, fold metadata, and category counts.
- all_error_ids.ids: all selected error IDs.
- errors.jsonl: full extracted prediction records.
- fold1.ids: 43 IDs.
- fold2.ids: 43 IDs.
- fold3.ids: 43 IDs.

## Fold statistics

| Fold | Count | Categories |
|---|---:|---|
| fold1 | 43 | 3D Geometry: 1; Depth & Occlusion: 9; Orientation: 3; Relative Positioning: 20; Size & Scale: 2; Spatial Navigation: 8 |
| fold2 | 43 | 3D Geometry: 1; Depth & Occlusion: 9; Orientation: 1; Relative Positioning: 17; Size & Scale: 3; Spatial Navigation: 12 |
| fold3 | 43 | 3D Geometry: 3; Depth & Occlusion: 6; Relative Positioning: 20; Size & Scale: 3; Spatial Navigation: 11 |
