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

For inspecting one result in detail, use these explicit fields:

- `selected_route` and `routing`: chosen route plus the controller's confidence,
  reason, proposed route, and complete raw response;
- `intermediate_trace`: raw object-extraction response, any visible extraction
  thinking, each object's stated extraction reason, and symbolic relation text;
- `scene_graph`: grounded objects with 2D points, depth/3D coordinates, and any
  route-specific features (also retained under the legacy `objects` field);
- `final_reasoning_thinking`: text inside the final response's `<think>` block;
- `final_answer_text` and `raw_response`: the text after the thinking block and
  the complete unmodified final model response, respectively.

The current question-only router and object extractor run with thinking disabled.
Their thinking fields are therefore normally empty; their complete raw outputs
and explicit reasons are still saved. No hidden reasoning is reconstructed.

The JSONL file is append-only so a stopped run can resume without rewriting or
silently merging earlier predictions. A new configuration must use a new
`run_name`.
