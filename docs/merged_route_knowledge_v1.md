# 四路线统一知识合并版 v1

原文件、历史结果均保留。根据fold知识包route字段、回放结果ID及冻结基线selected_route核对归属。

按路线合并原映射知识与该路线全部fold包，不再按题目ID选择知识。保留原句，仅在路线内部做Unicode NFKC和空白标准化去重；不进行语义删改，也不把近似规则视为重复。未对语义冲突作自动裁决。

|路线|原路线知识|fold新增（去重前）|移除重复|最终规则数|
|---|---:|---:|---:|---:|
|line0_pure_vlm|18|36|0|54|
|line1_base|19|37|0|56|
|line2_orientation|24|44|0|68|
|line3_bbox|13|25|0|38|

计数单位是一条原始规则字符串，并非句子数；同一知识在不同路线出现时分别计数。

知识目录：`knowledge_packs/merged_routes_v1/rules/`。配置：`configs/auto_revision_v4_merged_knowledge_v1.yaml`。manifest保存来源哈希、逐条来源及路线核对记录，不发布逐题答案或原始结果。

运行新合并版（本次未启动）：

```bash
python scripts/run_spatiallab.py --config configs/auto_revision_v4_merged_knowledge_v1.yaml
```

原配置默认74条检查不变；新配置显式声明合并后的规则总数。整体pipeline、路由策略、模型、几何模块均不改。新版本未评测，不能沿用757/1400的错误fold合并成绩。知识包含基于SpatialLab错误分析编写的规则，后续外部训练/评测必须披露此开发来源，不能据此声称完全未使用SpatialLab开发信号。
