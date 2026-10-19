"""Merge route-mapped baseline rules and seven fold packs without rewriting rules."""
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from kar3d.knowledge import RouteKnowledgeInjector

SOURCES={
 'line0_pure_vlm':['line0_error_fold1_v1.json','line0_error_fold2_v1.json'],
 'line1_base':['line1_error_fold1_v1.json','line1_error_fold3_v1.json'],
 'line2_orientation':['line2_error_fold2_v1.json','line2_error_fold3_v1.json'],
 'line3_bbox':['line3_error_fold2_v1.json'],
}


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def norm(t): return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',t)).strip()
def save(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    dest=ROOT/'knowledge_packs/merged_routes_v1'
    if dest.exists(): raise FileExistsError(dest)
    base=RouteKnowledgeInjector(ROOT/'knowledge',ROOT/'knowledge/route_map.json')
    generated={}; provenance={}; counts={}; source_hashes={}; validation={}
    for route,names in SOURCES.items():
        rules=[];lookup={};raw=0
        def add(text,source):
            nonlocal raw
            assert isinstance(text,str) and text.strip()
            raw+=1; key=norm(text)
            if key not in lookup:
                lookup[key]=len(rules);rules.append(text)
            provenance.setdefault(route,{}).setdefault(str(lookup[key]+1),[]).append(source)
        for tag in base.tags_for_route(route):
            for text in base.rules_by_tag[tag]: add(text,{'kind':'original_route_rule','tag':tag})
        baseline_count=raw
        folds={}
        for name in names:
            path=ROOT/'knowledge_packs'/name
            pack=json.loads(path.read_text())
            assert pack['route']==route
            source_hashes[str(path.relative_to(ROOT))]=sha(path)
            n=0
            for section in pack['sections']:
                for text in section['rules']:
                    add(text,{'kind':'fold_rule','file':str(path.relative_to(ROOT)),
                              'version':pack['version'],'section':section['title']});n+=1
            folds[name]=n
            # Audit all original replay rows against their frozen baseline route.
            stem=name.removesuffix('_v1.json')
            result=ROOT/'outputs'/f'{stem}_knowledge_v1_seed42'/'predictions.jsonl'
            baseline_path=ROOT/'outputs/auto_revision_v4_seed42/predictions.jsonl'
            assert result.is_file() and baseline_path.is_file(), str(result)
            baseline={str(r['id']):r for r in map(json.loads,baseline_path.read_text().splitlines())}
            rows=[json.loads(x) for x in result.read_text().splitlines() if x.strip()]
            assert rows
            for row in rows:
                assert baseline[str(row['id'])]['selected_route']==route
                if 'selected_route' in row: assert row['selected_route']==route
            validation[name]={'rows_checked':len(rows),'route':route,'result_sha256':sha(result)}
        generated[route]={route:rules}
        counts[route]={'original_route_rules':baseline_count,'fold_rules':folds,
                       'before_deduplication':raw,'removed_duplicates':raw-len(rules),'merged_rules':len(rules)}
    dest.mkdir();(dest/'rules').mkdir()
    for route,content in generated.items(): save(dest/'rules'/f'{route}.json',content)
    save(dest/'rules/route_map.json',{r:[r] for r in SOURCES})
    for p in sorted((ROOT/'knowledge').glob('*.json')): source_hashes[str(p.relative_to(ROOT))]=sha(p)
    save(dest/'manifest.json',{'version':'merged_routes_v1','policy':'original mapped route rules + corresponding fold rules; retain exact text; deduplicate NFKC/whitespace only within route; no sample-ID selection',
                             'counts':counts,'source_sha256':source_hashes,'fold_route_audit':validation,
                             'rule_sources':provenance,'evaluation_status':'not evaluated; does not reproduce merged-error-fold accuracy'})
    import yaml
    cfg=yaml.safe_load((ROOT/'configs/auto_revision_v4.yaml').read_text())
    cfg.update(run_name='auto_revision_v4_merged_knowledge_v1_seed42',
               knowledge_dir='knowledge_packs/merged_routes_v1/rules',
               route_map_path='knowledge_packs/merged_routes_v1/rules/route_map.json',
               expected_knowledge_rule_count=sum(c['merged_rules'] for c in counts.values()))
    (ROOT/'configs/auto_revision_v4_merged_knowledge_v1.yaml').write_text(yaml.safe_dump(cfg,sort_keys=False))
    check=RouteKnowledgeInjector(dest/'rules',dest/'rules/route_map.json')
    assert check.rule_count==cfg['expected_knowledge_rule_count']
    assert all(len(list(check.iter_route_rules(r)))==counts[r]['merged_rules'] for r in SOURCES)
    table='\n'.join(f'|{r}|{c["original_route_rules"]}|{sum(c["fold_rules"].values())}|{c["removed_duplicates"]}|{c["merged_rules"]}|' for r,c in counts.items())
    (ROOT/'docs/merged_route_knowledge_v1.md').write_text('# 四路线统一知识合并版 v1\n\n原文件、历史结果均保留。根据fold知识包route字段、回放结果ID及冻结基线selected_route核对归属。\n\n按路线合并原映射知识与该路线全部fold包，不再按题目ID选择知识。保留原句，仅在路线内部做Unicode NFKC和空白标准化去重；不进行语义删改，也不把近似规则视为重复。未对语义冲突作自动裁决。\n\n|路线|原路线知识|fold新增（去重前）|移除重复|最终规则数|\n|---|---:|---:|---:|---:|\n'+table+'\n\n计数单位是一条原始规则字符串，并非句子数；同一知识在不同路线出现时分别计数。\n\n知识目录：`knowledge_packs/merged_routes_v1/rules/`。配置：`configs/auto_revision_v4_merged_knowledge_v1.yaml`。manifest保存来源哈希、逐条来源及路线核对记录，不发布逐题答案或原始结果。\n\n运行新合并版（本次未启动）：\n\n```bash\npython scripts/run_spatiallab.py --config configs/auto_revision_v4_merged_knowledge_v1.yaml\n```\n\n原配置默认74条检查不变；新配置显式声明合并后的规则总数。整体pipeline、路由策略、模型、几何模块均不改。新版本未评测，不能沿用757/1400的错误fold合并成绩。知识包含基于SpatialLab错误分析编写的规则，后续外部训练/评测必须披露此开发来源，不能据此声称完全未使用SpatialLab开发信号。\n')
    print(json.dumps(counts,indent=2))


if __name__=='__main__':main()
