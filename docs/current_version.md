# 当前使用版本与复现入口

整理日期：2026-10-19。

## 主流程与基线

配置：`configs/auto_revision_v4.yaml`。主入口：`scripts/run_spatiallab.py`。模型为 Ovis2.5-9B，深度为 Depth Pro；模型、深度权重、数据和图片路径写在配置中，换机器时须按实际位置调整。

自动路由只读取题干，四条路线是 `line0_pure_vlm`、`line1_base`、`line2_orientation`、`line3_bbox`。历史名称 `pure_vlm` 不代表当前基线没有知识注入。路线与知识映射在 `knowledge/route_map.json`。元数据路由用于 oracle 对照。

```bash
conda activate ovis
export OMP_NUM_THREADS=8
python scripts/check_assets.py --config configs/auto_revision_v4.yaml
python scripts/run_spatiallab.py --config configs/auto_revision_v4.yaml
```

原基线结果目录：`outputs/auto_revision_v4_seed42/`。1400题，697题正确，49.7857%。原逐题文件 SHA256：`9a0f65b53f3856174b557b9f8eb21ebddbe19feded3445bf780d475046f55b80`。该目录是冻结实验记录；运行新完整实验前请复制配置，修改 `run_name` 为新的名字。

## 当前使用的错误 fold 知识回放

这些脚本复用原图、路由、场景图和关系，只运行一次最终推理。标准答案用于评分，不提供给推理模型。未重跑前面的阶段。

| 路线 | 脚本 | 本轮运行 fold | 知识文件 |
|---|---|---|---|
|line0|`scripts/replay_line0_error_fold.py`|fold1、fold2|`knowledge_packs/line0_error_fold{1,2}_v1.json`|
|line1|`scripts/replay_line1_error_fold.py`|fold1、fold3|`knowledge_packs/line1_error_fold{1,3}_v1.json`|
|line2|`scripts/replay_line2_error_fold.py`|fold2、fold3|`knowledge_packs/line2_error_fold{2,3}_v1.json`|
|line3|`scripts/replay_line3_error_fold.py`|fold2|`knowledge_packs/line3_error_fold2_v1.json`|

表内花括号表示多个实际文件，不是程序自动分配规则。每个知识包的分析及命令见 `docs/line*_error_fold*_knowledge_v1.md`。冻结 ID 和来源哈希见 `configs/line*_error_folds_seed42/`。导出的 `errors.jsonl` 包含逐题原始证据，和数据、模型、输出一样仅保存在服务器，不发布到仓库。

```bash
python scripts/replay_line3_error_fold.py \
  --fold fold2 \
  --knowledge knowledge_packs/line3_error_fold2_v1.json \
  --output-dir outputs/line3_error_fold2_knowledge_v1_seed42
```

回放默认 seed 为42，逐题使用 `42 + int(id)`，具体协议及源码哈希保存在各运行的 manifest 中。继续已完成实验只会复用原输出；代码或输入哈希改变时应使用新输出目录。

## 合并分析结果

`scripts/merge_error_fold_results.py` 将上述7份回放全部323个 ID 替换回基线副本，包括仍答错的样本。其余1077条不变。输出到独立目录 `outputs/auto_revision_v4_seed42_merged_error_folds_v1/`，已有该目录时拒绝覆盖。

|记录|正确数|准确率|
|---|---:|---:|
|原始完整基线|697/1400|49.7857%|
|错误 fold 回放合并副本|757/1400|54.0714%|

合并副本增加60道正确，4.2857个百分点。逐题来源与替换字段保存在 `replacements.json`、`merge_manifest.json` 和每条的 `merge_provenance`；原上游轨迹来自基线，最终推理全文、thinking、知识和答案来自回放。它是基于错误集开发后的合并分析，不能作为统一知识包完整重跑或独立泛化测试的成绩。当前也没有一个已验证可复现54.0714%的统一知识包主流程。

## 本次提交范围

包含当前主流程修复、配置、四路线错误 fold 知识包和回放入口、冻结 ID、合并工具、解析重评分工具及相关说明。原有可选参照物覆盖模块因主流程依赖而一并保留，默认关闭。旧的自适应选卡、v2/v3知识候选、临时上传包和中间分析文件留在服务器，未作为当前默认版本提交。历史源码已跟踪的文件予以保留。

数据集、模型、缓存、输出、环境、临时文件和含逐题原始数据的 `errors.jsonl` 不随代码提交。完整结果继续从服务器的 `outputs/` 读取。

## 验证

运行轻量测试：

```bash
python -m pytest -q tests/test_knowledge.py tests/test_routing.py \
  tests/test_evaluation.py tests/test_pipeline_trace.py tests/test_reference_coverage.py
```

CPU检查回放输入：在回放命令末尾加 `--check`。它会检查冻结基线哈希、名单、路线、图像路径和知识版本，不启动模型推理。

本次整理验证：精确代码快照的上述5组测试共19项通过；四条路线默认 fold 的 `--check` 全部通过。服务器没有启用 GPU，本次整理未启动推理实验。
