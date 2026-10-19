"""One final image-plus-knowledge inference per frozen line0 error, no selector."""
import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, default=ROOT/'configs/auto_revision_v4.yaml')
    p.add_argument('--fold-dir', type=Path, default=ROOT/'configs/line0_error_folds_seed42')
    p.add_argument('--fold', default='fold1', choices=[f'fold{i}' for i in range(1,7)])
    p.add_argument('--knowledge', type=Path, default=ROOT/'knowledge_packs/line0_error_fold1_v1.json')
    p.add_argument('--output-dir', type=Path, default=ROOT/'outputs/line0_error_fold1_knowledge_v1_seed42')
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    from kar3d.config import ExperimentConfig
    config = ExperimentConfig.load(args.config)
    fold = json.loads((args.fold_dir/'folds.json').read_text(encoding='utf-8'))
    baseline_path = Path(fold['source_predictions'])
    if sha(baseline_path) != fold['source_sha256']:
        raise ValueError('Baseline hash differs from frozen fold source')
    baseline = {str(x['id']): x for x in rows(baseline_path)}
    ids_file = args.fold_dir/(args.fold+'.ids')
    ids = ids_file.read_text(encoding='utf-8').split()
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('Empty fold or duplicate IDs')
    dataset_path = Path(config.data_path)
    dataset_rows = json.loads(dataset_path.read_text(encoding='utf-8'))
    dataset = {str(x['id']): x for x in dataset_rows}
    if len(dataset) != len(dataset_rows):
        raise ValueError('Duplicate dataset IDs')
    pack = json.loads(args.knowledge.read_text(encoding='utf-8'))
    if pack['route'] != 'line0_pure_vlm':
        raise ValueError('Wrong knowledge route')
    knowledge = '\n\n'.join(s['title']+'\n'+'\n'.join('- '+r for r in s['rules']) for s in pack['sections'])
    for i in ids:
        b, d = baseline[i], dataset[i]
        if b['selected_route'] != pack['route'] or b['status'] != 'ok' or b['is_correct'] is not False:
            raise ValueError('Not a frozen line0 error: '+i)
        if str(b['answer']) != str(d['Answer']) or b['image_filename'] != d['Image_Filename']:
            raise ValueError('Dataset mismatch: '+i)
        if not (Path(config.image_dir)/d['Image_Filename']).is_file():
            raise FileNotFoundError(d['Image_Filename'])
    meta = dict(baseline=str(baseline_path), baseline_sha256=sha(baseline_path),
        dataset_sha256=sha(dataset_path), config_sha256=sha(args.config), ids=ids,
        ids_sha256=sha(ids_file), knowledge_version=pack['version'], knowledge_sha256=sha(args.knowledge),
        seed=args.seed, seed_policy='seed + integer sample ID',
        protocol='one final image+knowledge inference; frozen line0; no selector',
        implementation_sha256={f:sha(ROOT/f) for f in ['scripts/replay_line0_error_fold.py',
        'src/kar3d/pipeline.py','src/kar3d/perception.py','src/kar3d/evaluation.py']})
    if args.check:
        print(json.dumps(dict(valid=True, planned=len(ids), knowledge_words=len(knowledge.split()),
            version=pack['version'], baseline_sha256=sha(baseline_path)), indent=2))
        return
    args.output_dir.mkdir(parents=True, exist_ok=True)
    meta_path = args.output_dir/'manifest.json'
    if meta_path.exists() and json.loads(meta_path.read_text(encoding='utf-8')) != meta:
        raise ValueError('Run settings changed; use a new output directory')
    save(meta_path, meta)
    output = args.output_dir/'predictions.jsonl'
    previous = rows(output) if output.exists() else []
    if any(str(r['id']) not in ids for r in previous):
        raise ValueError('Foreign IDs in output')
    completed = {str(r['id']) for r in previous if r['status']=='ok'}
    pending = [i for i in ids if i not in completed]
    if pending:
        import numpy as np
        import torch
        from PIL import Image
        from tqdm import tqdm
        from kar3d.perception import Ovis3DPerceptionModule
        from kar3d.pipeline import ThreeDKARPipeline
        from kar3d.evaluation import extract_answer, split_thinking_and_answer
        perception = Ovis3DPerceptionModule(model_path=str(config.model_path))
        pipeline = ThreeDKARPipeline(perception=perception, router=None, depth=None, knowledge=None,
            use_depth=False, use_backprojection=False, use_symbolic_relations=False, use_knowledge=False)
        for i in tqdm(pending, desc='line0_error_fold_knowledge'):
            d = dataset[i]
            seed = args.seed + int(i)
            options = '\n'.join(f"{j}. {d.get(f'Option_{j}', '')}" for j in range(1,5))
            record = dict(id=i, selected_route='line0_pure_vlm', image_filename=d['Image_Filename'],
                question=d['Question'], options_text=options, answer=str(d['Answer']),
                baseline_prediction=baseline[i]['prediction'], baseline_is_correct=False,
                knowledge_text=knowledge, seed=seed, selector_used=False)
            start = time.perf_counter()
            try:
                random.seed(seed)
                np.random.seed(seed % 2**32)
                torch.manual_seed(seed)
                torch.cuda.manual_seed_all(seed)
                with Image.open(Path(config.image_dir)/d['Image_Filename']) as opened:
                    image = opened.convert('RGB')
                response = pipeline._direct_reasoning(image, d['Question'], options, knowledge)
                thinking, final = split_thinking_and_answer(response)
                prediction = extract_answer(response)
                record.update(status='ok', raw_response=response, final_reasoning_thinking=thinking,
                    final_answer_text=final, prediction=prediction, is_correct=prediction==str(d['Answer']))
            except Exception as exc:
                record.update(status='error', error=f'{type(exc).__name__}: {exc}', is_correct=False)
            record['elapsed_seconds'] = round(time.perf_counter()-start,3)
            with output.open('a',encoding='utf-8') as f:
                f.write(json.dumps(record,ensure_ascii=False)+'\n')
    latest = {str(r['id']):r for r in rows(output)}
    correct = [i for i in ids if latest.get(i,{}).get('is_correct')]
    ok = sum(latest.get(i,{}).get('status')=='ok' for i in ids)
    summary = dict(planned=len(ids), completed=len(latest), ok=ok, errors=len(latest)-ok,
        pending=len(ids)-len(latest), correct=len(correct), accuracy=round(100*len(correct)/len(ids),4),
        corrected_ids=correct, baseline_correct=0, target_correct=3, target_met=len(correct)>=3,
        knowledge_version=pack['version'], seed=args.seed,
        note='Error-only development fold. Not full-route accuracy or a matched-seed causal estimate.')
    save(args.output_dir/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
