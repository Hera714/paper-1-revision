"""Merge all seven requested replay results into an immutable-baseline copy."""
import copy
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'outputs/auto_revision_v4_seed42'
OUT = ROOT / 'outputs/auto_revision_v4_seed42_merged_error_folds_v1'
NAMES = [
    'line0_error_fold1_knowledge_v1_seed42',
    'line0_error_fold2_knowledge_v1_seed42',
    'line1_error_fold1_knowledge_v1_seed42',
    'line1_error_fold3_knowledge_v1_seed42',
    'line2_error_fold2_knowledge_v1_seed42',
    'line2_error_fold3_knowledge_v1_seed42',
    'line3_error_fold2_knowledge_v1_seed42',
]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rows(p):
    return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]


def save(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    if OUT.exists():
        raise FileExistsError('Refusing to overwrite: ' + str(OUT))
    baseline_path = BASE / 'predictions.jsonl'
    baseline = rows(baseline_path)
    by_id = {str(r['id']): r for r in baseline}
    assert len(by_id) == len(baseline) == 1400
    assert sha(baseline_path) == '9a0f65b53f3856174b557b9f8eb21ebddbe19feded3445bf780d475046f55b80'
    source_paths = [baseline_path, BASE / 'summary.json']
    changes, replacements = [], {}
    sources = []
    for name in NAMES:
        folder = ROOT / 'outputs' / name
        path = folder / 'predictions.jsonl'
        manifest_path = folder / 'manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        source_paths.extend([path, manifest_path, folder / 'summary.json'])
        latest = {}
        for row in rows(path):
            latest[str(row['id'])] = row
        expected = list(map(str, manifest['ids']))
        assert len(expected) == len(set(expected))
        assert set(latest) == set(expected), name
        corrected = []
        for sid in expected:
            row, old = latest[sid], by_id[sid]
            assert sid not in replacements, 'Overlapping source ID: ' + sid
            assert row['status'] == 'ok', (name, sid)
            assert old['is_correct'] is False, sid
            for key in ['image_filename', 'selected_route']:
                assert row[key] == old[key], (sid, key)
            assert str(row['answer']) == str(old['answer']), sid
            assert row['baseline_prediction'] == old['prediction'], sid
            for key in ['raw_response', 'final_reasoning_thinking', 'final_answer_text', 'prediction', 'knowledge_text']:
                assert key in row, (sid, key)
            valid = str(row['prediction']) in ['1', '2', '3', '4']
            correct = valid and str(row['prediction']) == str(old['answer'])
            assert bool(row['is_correct']) == correct, sid
            merged = copy.deepcopy(old)
            merged.update(copy.deepcopy(row))
            merged['is_correct'] = correct
            merged['answer_valid'] = valid
            # Keep the baseline ID type/order, while replacing every replay field.
            merged['id'] = old['id']
            merged['timings'] = {
                'final_reasoning_replay_seconds': row.get('elapsed_seconds'),
                'total_seconds': None,
                'note': 'Upstream cached; not a new end-to-end timing.',
            }
            merged['merge_provenance'] = {
                'source_predictions': str(path.relative_to(ROOT)),
                'baseline_predictions': str(baseline_path.relative_to(ROOT)),
                'upstream_trace_source': 'baseline cache; routing/perception not rerun',
                'baseline_timings': old.get('timings'),
                'replaced_fields': sorted(row),
            }
            replacements[sid] = merged
            if correct:
                corrected.append(sid)
            changes.append(dict(id=sid, source=name, baseline_prediction=old['prediction'],
                                prediction=row['prediction'], is_correct=correct))
        sources.append(dict(name=name, replaced=len(expected), correct=len(corrected), corrected_ids=corrected))
    assert len(replacements) == 323
    before = {str(p): sha(p) for p in source_paths}
    merged_rows = [replacements.get(str(r['id']), copy.deepcopy(r)) for r in baseline]
    assert [r['id'] for r in merged_rows] == [r['id'] for r in baseline]
    for old, new in zip(baseline, merged_rows):
        if str(old['id']) not in replacements:
            assert old == new
    by_category, by_route = defaultdict(list), defaultdict(list)
    for row in merged_rows:
        # Recompute scoring from predictions, never just sum saved booleans.
        correct = row.get('status') == 'ok' and str(row.get('prediction')) in ['1','2','3','4'] and str(row.get('prediction')) == str(row['answer'])
        assert correct == bool(row['is_correct']), row['id']
        by_category[row['category']].append(correct)
        by_route[row['selected_route']].append(correct)
    def stats(values):
        return dict(correct=sum(values), total=len(values), accuracy=round(100 * sum(values) / len(values), 4))
    correct = sum(r['is_correct'] for r in merged_rows)
    original_correct = sum(r['is_correct'] for r in baseline)
    summary = dict(evaluated=len(merged_rows), correct=correct,
        accuracy=round(100 * correct / len(merged_rows), 4),
        route_counts=dict(Counter(r['selected_route'] for r in merged_rows)),
        status_counts=dict(Counter(r['status'] for r in merged_rows)),
        by_category={k:stats(v) for k,v in sorted(by_category.items())},
        by_route={k:stats(v) for k,v in sorted(by_route.items())},
        baseline_correct=original_correct, baseline_accuracy=round(100*original_correct/1400,4),
        replaced_samples=len(replacements), unchanged_samples=1400-len(replacements),
        additional_correct=correct-original_correct,
        accuracy_gain_percentage_points=round(100*(correct-original_correct)/1400,4),
        replacement_sources=sources,
        note='Merged error-only development replays with unchanged baseline samples; not a fresh full-pipeline evaluation or independent generalization result.')
    assert before == {str(p): sha(p) for p in source_paths}, 'Input changed during merge'
    OUT.mkdir(parents=True, exist_ok=False)
    output_path = OUT / 'predictions.jsonl'
    output_path.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in merged_rows), encoding='utf-8')
    save(OUT / 'summary.json', summary)
    save(OUT / 'replacements.json', changes)
    save(OUT / 'merge_manifest.json', dict(source_sha256=before, output_sha256=sha(output_path),
        script_sha256=sha(Path(__file__)), original_files_preserved=True,
        policy='Replace every listed ID, including still-wrong outputs; retain cached upstream fields only where replay has no replacement.'))
    (OUT / 'README.md').write_text(
        '# 错误 fold 回放合并副本\n\n'
        f'原基线 1400 题，正确 {original_correct}；本副本正确 {correct}，准确率 {summary["accuracy"]}%。\n\n'
        f'按 ID 替换全部 {len(replacements)} 条，含仍答错的题；其余样本保持原样。新推理全文、thinking、答案、知识及回放字段来自对应 fold。'
        '未重跑的路由与感知轨迹保留基线缓存；每条替换记录含 merge_provenance，不混称新生成的上游过程。'
        'timings 标明仅回放耗时，原耗时保存在来源信息内。\n\n'
        '所有源文件均保留；merge_manifest.json 记录输入与输出哈希，replacements.json 记录逐题来源和变化。\n\n'
        '**这是使用错误样本开发集迭代后拼接的分析副本，不是统一知识包完整重跑的实验，不能作为独立测试集泛化或正式完整 pipeline 成绩。**\n', encoding='utf-8')
    assert before == {str(p): sha(p) for p in source_paths}, 'Input changed after merge'
    assert rows(output_path) == merged_rows
    print(json.dumps(dict(output_dir=str(OUT), summary=summary), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
