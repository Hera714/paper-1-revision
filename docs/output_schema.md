# Output schema

Each run writes immutable artifacts under `outputs/<run_name>/`:

- `config.yaml`: exact configuration used for the run;
- `predictions.jsonl`: one append-only record per sample;
- `summary.json`: overall accuracy, route counts, and category-level accuracy;
- `routes.jsonl`: optional route-only predictions;
- `routes_summary.json`: optional route-only aggregate statistics.

Every prediction record contains:

- sample ID, image filename, answer, and post-hoc reporting labels;
- selected route, proposed route, confidence, source, reason, and raw controller
  response;
- extracted objects and grounded geometric attributes;
- symbolic relation text and injected knowledge text as separate fields;
- raw final response, parsed answer, correctness, and status;
- stage-level wall-clock timings.

The JSONL file is append-only so a stopped run can resume without rewriting or
silently merging earlier predictions. A new configuration must use a new
`run_name`.
