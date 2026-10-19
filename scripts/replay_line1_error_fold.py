"""Replay frozen line1 errors using cached geometry and one final model call."""
import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
ROUTE = 'line1_base'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read_rows(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, default=ROOT/'configs/auto_revision_v4.yaml')
    p.add_argument('--fold-dir', type=Path, default=ROOT/'configs/line1_error_folds_seed42')
    p.add_argument('--fold', choices=['fold1','fold2','fold3'], default='fold1')
    p.add_argument('--knowledge', type=Path, default=ROOT/'knowledge_packs/line1_error_fold1_v1.json')
    p.add_argument('--output-dir', type=Path, default=ROOT/'outputs/line1_error_fold1_knowledge_v1_seed42')
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    from kar3d.config import ExperimentConfig
    config = ExperimentConfig.load(args.config)
    fold = json.loads((args.fold_dir/'folds.json').read_text(encoding='utf-8'))
    source = Path(fold['source_predictions'])
    if fold['route'] != ROUTE or sha(source) != fold['source_sha256']:
        raise ValueError('Frozen fold route/source mismatch')
    baseline_rows = read_rows(source)
    baseline = {str(r['id']):r for r in baseline_rows}
    data_path = config.resolve_project_path(ROOT, config.data_path)
    image_dir = config.resolve_project_path(ROOT, config.image_dir)
    data_rows = json.loads(data_path.read_text(encoding='utf-8'))
    data = {str(r['id']):r for r in data_rows}
    if len(data)!=len(data_rows) or len(baseline)!=len(baseline_rows):
        raise ValueError('Duplicate input IDs')
    ids_path = args.fold_dir/(args.fold+'.ids')
    ids = ids_path.read_text(encoding='utf-8').split()
    if not ids or len(ids)!=len(set(ids)) or len(ids)!=fold['folds'][args.fold]['count']:
        raise ValueError('Invalid fold IDs/count')
    pack = json.loads(args.knowledge.read_text(encoding='utf-8'))
    if pack['route']!=ROUTE:
        raise ValueError('Wrong knowledge route')
    knowledge = '\n\n'.join(s['title']+'\n'+'\n'.join('- '+r for r in s['rules']) for s in pack['sections'])
    if not knowledge.strip():
        raise ValueError('Empty knowledge')
    for i in ids:
        b,d = baseline[i],data[i]
        if b['selected_route']!=ROUTE or b['status']!='ok' or b['is_correct'] is not False:
            raise ValueError('Not a frozen line1 error: '+i)
        if b['image_filename']!=d['Image_Filename'] or str(b['answer'])!=str(d['Answer']):
            raise ValueError('Dataset mismatch: '+i)
        if not isinstance(b.get('scene_graph'),list):
            raise ValueError('Missing cached scene graph: '+i)
        if not (image_dir/d['Image_Filename']).is_file():
            raise FileNotFoundError(d['Image_Filename'])
    meta = dict(route=ROUTE, ids=ids, seed=args.seed, seed_policy='seed + integer sample ID',
        baseline=str(source), baseline_sha256=sha(source), ids_sha256=sha(ids_path),
        knowledge_version=pack['version'], knowledge_sha256=sha(args.knowledge),
        config_sha256=sha(args.config), dataset_sha256=sha(data_path),
        protocol='cached scene graph and relations; one final image+knowledge call; no selector',
        implementation_sha256={f:sha(ROOT/f) for f in ['scripts/replay_line1_error_fold.py',
        'src/kar3d/perception.py','src/kar3d/evaluation.py']})
    if args.check:
        print(json.dumps(dict(valid=True, planned=len(ids), route=ROUTE,
            knowledge_version=pack['version'], knowledge_words=len(knowledge.split()),
            baseline_sha256=sha(source)), indent=2))
        return
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir/'manifest.json'
    if manifest_path.exists() and json.loads(manifest_path.read_text(encoding='utf-8'))!=meta:
        raise ValueError('Settings changed; use a new output directory')
    save(manifest_path, meta)
    output = args.output_dir/'predictions.jsonl'
    latest = {str(r['id']):r for r in read_rows(output)} if output.exists() else {}
    if set(latest)-set(ids):
        raise ValueError('Foreign output IDs')
    pending = [i for i in ids if latest.get(i,{}).get('status')!='ok']
    if pending:
        import numpy as np
        import torch
        from PIL import Image
        from tqdm import tqdm
        from kar3d.perception import Ovis3DPerceptionModule
        from kar3d.evaluation import extract_answer, split_thinking_and_answer
        perception = Ovis3DPerceptionModule(model_path=str(config.model_path))
        for i in tqdm(pending,desc='line1_error_fold_knowledge'):
            d,b=data[i],baseline[i]
            scene=b['scene_graph']
            relations=b.get('spatial_relations_text') or ''
            evidence=relations+('\n\n' if relations else '')+'--- EXTERNAL DOMAIN KNOWLEDGE ---\n'+knowledge
            options='\n'.join(f"{j}. {d.get(f'Option_{j}', '')}" for j in range(1,5))
            seed=args.seed+int(i)
            record=dict(id=i, selected_route=ROUTE, image_filename=d['Image_Filename'],
                question=d['Question'], options_text=options, answer=str(d['Answer']),
                category=d.get('Category'), sub_category=d.get('Sub_Category'),
                baseline_prediction=b['prediction'], baseline_is_correct=False,
                scene_graph=scene, spatial_relations_text=relations, knowledge_text=knowledge,
                cached_scene_graph_sha256=digest(scene), cached_relations_sha256=digest(relations),
                seed=seed, selector_used=False)
            start=time.perf_counter()
            try:
                random.seed(seed)
                np.random.seed(seed % 2**32)
                torch.manual_seed(seed)
                torch.cuda.manual_seed_all(seed)
                with Image.open(image_dir/d['Image_Filename']) as opened:
                    image=opened.convert('RGB')
                response=perception.perform_final_reasoning(image,d['Question'],options,scene,evidence,task_route=ROUTE)
                thinking,final=split_thinking_and_answer(response)
                prediction=extract_answer(response)
                record.update(status='ok',raw_response=response,final_reasoning_thinking=thinking,
                    final_answer_text=final,prediction=prediction,answer_valid=prediction in ['1','2','3','4'],
                    is_correct=prediction==str(d['Answer']))
            except Exception as exc:
                record.update(status='error',error=f'{type(exc).__name__}: {exc}',is_correct=False)
                print(record['error'],file=sys.stderr)
            record['elapsed_seconds']=round(time.perf_counter()-start,3)
            latest[i]=record
            with output.open('a',encoding='utf-8') as f:
                f.write(json.dumps(record,ensure_ascii=False)+'\n')
            write_summary(args.output_dir,latest,ids,pack['version'],args.seed)
    print(json.dumps(write_summary(args.output_dir,latest,ids,pack['version'],args.seed),indent=2))


def write_summary(out, latest, ids, version, seed):
    correct=[i for i in ids if latest.get(i,{}).get('is_correct')]
    ok=sum(latest.get(i,{}).get('status')=='ok' for i in ids)
    summary=dict(planned=len(ids),completed=len(latest),ok=ok,errors=len(latest)-ok,pending=len(ids)-len(latest),
        correct=len(correct),accuracy=round(100*len(correct)/len(ids),4),corrected_ids=correct,
        baseline_correct=0,target_correct=3,target_met=len(correct)>=3,
        invalid_answers=sum(r.get('status')=='ok' and not r.get('answer_valid') for r in latest.values()),
        knowledge_version=version,seed=seed,
        note='Error-only development fold; not full-route gain or matched-seed causal knowledge benefit.')
    save(out/'summary.json',summary)
    return summary


if __name__=='__main__':
    main()
