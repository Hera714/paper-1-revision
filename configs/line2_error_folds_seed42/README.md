# line2_orientation error sample folds

- Baseline: auto_revision_v4_seed42
- Route: line2_orientation
- Selection: selected_route=line2_orientation, status=ok, is_correct=false
- Split: random.Random(42) shuffle followed by round-robin assignment
- Target fold size: about 50

## Files

- folds.json: source hash, selection rule, fold metadata, and category counts.
- all_error_ids.ids: all selected error IDs.
- errors.jsonl: full extracted prediction records.
- fold1.ids: 47 IDs.
- fold2.ids: 46 IDs.
- fold3.ids: 46 IDs.

## Fold statistics

| Fold | Count | Categories |
|---|---:|---|
| fold1 | 47 | 3D Geometry: 6; Orientation: 24; Relative Positioning: 5; Size & Scale: 9; Spatial Navigation: 3 |
| fold2 | 46 | 3D Geometry: 6; Orientation: 27; Relative Positioning: 2; Size & Scale: 5; Spatial Navigation: 6 |
| fold3 | 46 | 3D Geometry: 8; Orientation: 22; Relative Positioning: 1; Size & Scale: 4; Spatial Navigation: 11 |
