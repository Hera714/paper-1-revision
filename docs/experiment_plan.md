# 3D-KAR revision experiment plan

This document is the living checklist for the revised submission. Update it
when an experiment is added, changed, completed, or removed.

## Decisions already made

- [x] Keep the four-route method architecture.
- [x] Replace metadata route selection in the main setting with a question-only
  VLM controller.
- [x] Do not use answer options, images, category labels, or sub-category labels
  for automatic route selection.
- [x] Keep the original 74 knowledge statements and select knowledge by the
  chosen route through `knowledge/route_map.json`.
- [x] Retain metadata routing only as an oracle upper bound.
- [x] Retire incomplete and low-performing legacy controller outputs.
- [x] Use one canonical runner and unique output directories.
- [ ] Confirm the proposed route-to-knowledge grouping with the authors.

## P0 — local code review before upload

- [x] Extract the active Ovis perception, Depth Pro, 3D grounding, pose relation,
  and bounding-box relation modules.
- [x] Add a question-only automatic router without lexical overrides.
- [x] Add auto, oracle, and fixed-route configurations.
- [x] Add route-level knowledge configuration.
- [x] Add incremental JSONL outputs and a summary file.
- [x] Record stage-level wall-clock timings.
- [x] Keep raw data and generated outputs out of Git by default.
- [ ] Author review of prompts, route definitions, and knowledge mapping.
- [ ] Upload reviewed version to GitHub.

## P0 — first server validation

- [x] Run static import and environment checks in the `ovis` environment.
- [x] Run route-only prediction on all 1,400 questions.
- [x] Report route distribution, oracle agreement, confusion matrix, confidence
  distribution, and low-confidence fallback rate.
- [x] Manually inspect at least 20 disagreements per predicted route.
- [x] Run an end-to-end stratified pilot before the full benchmark.
- [x] Freeze the accepted router prompt and confidence threshold.

## Main experiments

- [ ] Automatic question-only routing, full method, three seeds.
- [ ] Oracle metadata routing, full method, upper bound.
- [ ] Fixed Basic route control.
- [ ] Base VLM under a matched final-reasoning prompt and generation budget.
- [ ] Route-error impact: end-to-end accuracy for route matches vs mismatches.

## Progressive-removal ablation

The intended ablation is cumulative removal, not a one-factor factorial study.
The paper must state this explicitly and list every enabled component per row.

| Stage | Auto routing | Fine features | 3D grounding | Symbolic relations | Knowledge |
|---|---:|---:|---:|---:|---:|
| Full | on | on | on | on | on |
| − Knowledge | on | on | on | on | off |
| − Relations, − Knowledge | on | on | on | off | off |
| − Fine features, − Relations, − Knowledge | on | off | on | off | off |
| Fixed Basic control | off | basic only | on | route-defined | on |

- [ ] Decide whether the paper will call this a “progressive removal study” or
  add separate one-factor controls for stronger causal claims.
- [ ] If retaining claims about an individual component, add a one-factor row
  where only that component is changed.
- [ ] Add the reviewer-requested controls: 2D anchors only; depth without
  back-projection; 3D coordinates without relation cards; matched two-stage
  prompting without 3D evidence.

## Generalization, comparison, and efficiency

- [ ] Run RealWorldQA* with the same automatic router and route-level knowledge.
- [ ] Preserve and publish the RealWorldQA* retained sample IDs.
- [ ] Add SpatialRGPT and the closest feasible matched-backbone baseline.
- [ ] Add at least one non-Qwen-family VLM if compute permits.
- [ ] Report routing, perception, depth, grounding, relation, final-reasoning,
  and total latency, plus peak memory and token counts.

## Manuscript work — intentionally deferred

- [ ] Revise architecture description after experiments are frozen.
- [ ] Correct claims about which routes construct 3D graphs and relation cards.
- [ ] Rewrite the ablation description to match the actual cumulative design.
- [ ] Update related work, novelty comparison, tables, limitations, and response
  to reviewers.
- [ ] Replace all old result numbers with reproducible run artifacts.

## 2026-10-13 V4 repair and rerun log

- Original full run: 641/1400, 45.7857%.
- Parser-only conservative rescore: 652/1400, 46.5714%; 29 Unknown outputs recovered and 11 were correct. The original JSONL remains unchanged.
- Fixed answer formats, first-JSON parsing, extraction diagnostics, larger structured-output budget, explicit image-plane coordinates, and exact final answer tags.
- Refined the question-only router without adding metadata or answer-option access.
- Added occlusion-aware bbox uncertainty and removed contradictory hard pose deductions.
- Ten-case V2 pilot reached 7/10; the later bbox repair corrected case 3, giving an expected 8/10 on the same set.
- Case 5 remained wrong under both the orientation route and forced direct VLM route, so no sample-specific rule was added.
- Full V4 run started in screen session auto_revision_v4.
- Config: configs/auto_revision_v4.yaml
- Output: outputs/auto_revision_v4_seed42/
- Log: outputs/auto_revision_v4_seed42/screen.log
