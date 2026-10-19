# line3_bbox error sample folds

- Baseline: auto_revision_v4_seed42
- Route: line3_bbox
- Selection: selected_route=line3_bbox, status=ok, is_correct=false
- Split: random.Random(42) shuffle followed by round-robin assignment
- Target fold size: about 50

## Files

- folds.json: source hash, selection rule, fold metadata, and category counts.
- all_error_ids.ids: all selected error IDs.
- errors.jsonl: full extracted prediction records.
- fold1.ids: 49 IDs.
- fold2.ids: 49 IDs.
- fold3.ids: 49 IDs.

## Fold statistics

| Fold | Count | Categories |
|---|---:|---|
| fold1 | 49 | 3D Geometry: 12; Depth & Occlusion: 2; Relative Positioning: 5; Size & Scale: 25; Spatial Navigation: 5 |
| fold2 | 49 | 3D Geometry: 19; Depth & Occlusion: 3; Relative Positioning: 5; Size & Scale: 21; Spatial Navigation: 1 |
| fold3 | 49 | 3D Geometry: 15; Depth & Occlusion: 3; Orientation: 1; Relative Positioning: 2; Size & Scale: 25; Spatial Navigation: 3 |
