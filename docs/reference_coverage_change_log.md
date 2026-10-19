# 对象与参照物覆盖：第一阶段改动记录

日期：2026-10-14。知识注入规则、路线选择、深度/姿态/bbox 表征、符号关系计算和最终推理提示词均保持原样。本改动只在原有对象提取之后增加**可选的覆盖检查与定向补提取**；默认 `off`，不会改变现有实验。

## 问题证据与离线审计

原 v4 的对象提取提示词已要求穷尽，但缓存结果仍有明显遗漏：ID 68 缺 overcoat/mirror，404 缺 flowers，896 缺 rattan basket/ladder，41 缺 doorway；ID 119 还把选项 `Nothing` 当成真实物体。单纯强化“请穷尽”的提示词不能保证解决。

新建 `reference_coverage.py`，**只读推理时可见的问题文字**，保守识别 `between X and Y`、`closest to X`、`further away from X`、`aligned with X and Y`、`inside X`、`near X`、`deeper/shallower than X` 等显式参照。它不读取类别、子类或 GT，不把 `Nothing`、`Not given`、`Can't answer` 等选项当物体。抽象图像位置（如画面中心、角落）也不作为补提取目标。词头匹配只是保守触发器，不等同于精确视觉识别；同名多实例仍待人工复核。

对缓存的 1400 条 v4 预测做 CPU 审计：其中 818 道走场景图路线，46 道被标为“至少一个显式参照物未匹配”，共 61 个缺失提及；20 道原本答错、26 道原本答对。路线分布：line1 35、line2 5、line3 6。另有 1 道抽出了明显非实体选项。这些数字只是文本匹配发现的候选，并非 46 道经人工证实的漏检；26 道原本答对意味着无条件补物体可能误伤。

## 代码行为与输出

- `reference_coverage_mode: off`：完全不检查，保持旧版路径和输出；旧配置默认如此。
- `reference_coverage_mode: audit`：记录问题参照物、未匹配名单及非实体名称，不改场景图，不增加模型调用。
- `reference_coverage_mode: repair`：先去除明确非实体名称；若有显式参照物未匹配，最多再调用**一次现有同路线对象提取器**，请求补充这些可见的参照物。只合并名称匹配、图像坐标有效的候选；line3 还要求 bbox 有效且包含目标点。原第一轮对象保留，不替换整个场景图；原深度/符号关系随后照常计算。
- 每题在 `intermediate_trace.reference_coverage` 记录 `missing_before`、`non_entity_names`、是否补提取、第二次原始输出/解析诊断、实际 `added_names` 和 `missing_after`；额外耗时为 `timings.reference_repair_seconds`。路由、图像、原问题、选项、知识注入和最终推理输入格式不变，最终阶段仍看原图。

实现位置：`src/kar3d/reference_coverage.py`、`src/kar3d/pipeline.py`、`src/kar3d/config.py`、`scripts/run_spatiallab.py`。`--ids` 只用于固定小样本运行，选择写入输出目录的 `selected_ids.json` 以防续跑时换题。两个独立 pilot 配置只差 `run_name` 与 `reference_coverage_mode`。

## 验证状态与风险

服务器已部署上述可选代码与配置；原 `configs/auto_revision_v4.yaml`、原 1400 条结果、知识文件、模型权重均未改动。部署前将服务器上三个原文件备份在 `.reference_upload/*.pre_reference`。新加 7 个 CPU 单元测试均通过；原有 pipeline trace 两项也通过。服务器 `ovis` 环境没有安装 pytest，因此未跑依赖 pytest 的旧测试文件；这不是新测试失败。

首轮 8 题 GPU 对照已完成，详见下文。主要风险是词头匹配漏掉同义词/同名实例、二次提取引入错误空间数值，以及额外耗时。必须检查 `repair_attempted`、`added_names`、`missing_after`、新旧同题翻转和路线是否一致；触发而原本正确的题必须纳入控制。

## 第一轮小样本命令（由用户运行）

固定 8 题：原版错题 `68,404,896,119`；原版答对的控制题 `444,907,1394,192`，覆盖 line1/line2/line3，并包含非实体选项案例。两组配置除开关外相同，请在服务器依次运行：

```bash
conda activate ovis
cd /root/autodl-tmp/paper-1-revision
export OMP_NUM_THREADS=8
IDS=68,404,896,119,444,907,1394,192
python scripts/run_spatiallab.py --config configs/auto_reference_pilot_audit.yaml --ids "$IDS"
python scripts/run_spatiallab.py --config configs/auto_reference_pilot_repair.yaml --ids "$IDS"
```

结果分别写入 `outputs/auto_reference_pilot_audit/` 与 `outputs/auto_reference_pilot_repair/`，两组互不覆盖且可用同一命令续跑。

## 首轮 8 题结果及图像复核

两组均为 8/8 `ok`；audit 组 5/8（62.5%），repair 组 6/8（75%），净增 1 题。8 对样本的选路、路由记录、第一次对象提取原文、知识文本完全一致；repair 保留了 audit 的全部首轮对象。因而本轮三个翻转来自补提取之后的场景图/几何证据与最终推理，不是换路线或换知识造成的。此样本刻意挑选漏提风险题，且样本量极小，**不能作为全量准确率提升证据**。

| ID | audit → repair | 补入对象 | 图像与推理核查 |
| --- | --- | --- | --- |
| 68 | 错 2 → 对 4 | mirror、overcoat | 图中圆镜在中上、外套在右，帽子确实位于两者之间。补齐两个参照点后模型选帽子；原场景图仅有 bench/pillows/hat。 |
| 404 | 对 1 → 错 2 | flowers | 图中花与水龙头都在厨房岛台附近，正确项是 Tap；吊灯在上方。补入的花点位在花束中，但模型主要按深度差比较：花 Z=2.68、灯 Z=2.85、水龙头 Z=3.03，于是误选灯。由这些估计点算的 3D 距离也会把灯排得更近（约 0.62m 对 0.75m），说明这里既有不可靠的跨物体几何证据，也有模型未顾及台面语义的问题；不能简单归咎于“只看 Z”。 |
| 896 | 错 2 → 对 3 | rattan basket；ladder 仍缺 | 图中藤篮位于梯子底部附近，补入的篮筐 bbox/点大致落在图上；模型据估计宽高比较，改选较小的 monkey toy。单张图估尺寸仍有不确定性，不能把这一例当作物理测量准确性的验证。 |

另 5 题答案未变，包含原本答对的 444、907、1394、192；119 在这次首轮提取后已无文本匹配意义上的缺参照，因此没有触发补提取，仍答错。repair 组在 8 题上累计额外补提取约 57 秒；两组各自题内耗时合计约 194 秒与 258 秒，不含模型加载。这只是该小样本机器上的实测，非全量用时承诺。

结论：补参照有真实收益，但已观察到对原本正确题的明确误伤；**暂不启用完整 1400 题，也暂不按单个反例改规则**。保持代码冻结，先在离线审计标出的全部 46 个候选上做固定配对对照（历史 v4 中 20 错、26 对），特别检查对原正确题的误伤率、补入点的可见性和几何可靠性。这 46 题是高风险子集，不代表全数据分布；即使该子集净收益，也还需另取未触发样本检查回归，并最终做全量评估。

## 下一轮：46 个候选的固定配对验证

已准备 `configs/reference_candidates_46.ids` 和 `configs/auto_reference_candidates_{audit,repair}.yaml`，两份配置只差开关和输出名。46 个 ID 来自原 v4 的 CPU 审计，不依据本轮 repair 答案筛选；两组固定同一清单。按首轮单题耗时推算，两组串行计算约 43 分钟，加两次模型加载及机器波动，建议预留至少 1 小时。这不是全量实验。

```bash
conda activate ovis
cd /root/autodl-tmp/paper-1-revision
export OMP_NUM_THREADS=8
IDS=$(tr -d '\r\n' < configs/reference_candidates_46.ids)
python scripts/run_spatiallab.py --config configs/auto_reference_candidates_audit.yaml --ids "$IDS"
python scripts/run_spatiallab.py --config configs/auto_reference_candidates_repair.yaml --ids "$IDS"
```

运行前应确认这三个配置文件已经部署在服务器；GPU 命令由用户执行。新结果与首轮 8 题输出分开保存，不能混写。

## 46 题固定对照结果（已完成，2026-10-15）

用户已完成上述两组实验。两组均为 46/46 `ok`，所选 ID、路由、第一次对象提取原文、知识文本逐题一致。`audit` 答对 **26/46（56.5217%）**，`repair` 答对 **23/46（50.0000%）**；发生 **3 题错→对、6 题对→错**，净减少 3 题。与首轮 8 题的净增 1 题相比，完整候选集结果方向相反，因此不能据首轮小样本启用该修复。

| 变化 | 数量 | ID |
| --- | ---: | --- |
| 错→对 | 3 | 68、896、1077 |
| 对→错 | 6 | 404、405、840、973、1396、1455 |
| 对→对 | 20 | 见原始 JSONL |
| 错→错 | 17 | 见原始 JSONL |

六个退化案例都来自 `line1_base` 的 Relative Positioning；该类别由 22/33 降至 17/33。三个获益分别在 Relative Positioning（68）、3D Geometry（896）和 Depth & Occlusion（1077）。按路线统计，`line1_base` 23/35→19/35，`line2_orientation` 1/5→1/5，`line3_bbox` 2/6→3/6。路线/类别子集很小，仅用于定位问题。

图像、场景图与 thinking 复核：

| ID | 变化 | 主要原因与限制 |
| --- | --- | --- |
| 68 | 错→对 | 补齐镜子与外套，两点在图中可见；模型据此识别中间的帽子。 |
| 896 | 错→对 | 补齐藤篮 bbox 后改选猴子玩具；但梯子仍缺，不能声称完整对象覆盖。 |
| 1077 | 错→对 | 补入花与沙发后改选灯；图中二者均可见，但模型仍混用深度顺序与画面位置，单例正确不验证几何推理可靠。 |
| 404 | 对→错 | 补入花后模型主要看估计深度，误选吊灯；图中水龙头与花同在厨房岛台附近。 |
| 405 | 对→错 | 补入左侧雕像后，模型把右侧建筑柱子当成两个人之间的目标，舍弃了居中的黄衣人；右下白衣人仍未作为独立参照提取。 |
| 840 | 对→错 | “路边”框落在车体/镜面边缘，不能稳定表示镜中道路边缘；模型转而选 `Nothing`，忽略镜内车辆与灯光。 |
| 973 | 对→错 | 补入冰箱后，模型推理拉长且没有给出可解析答案（`Unknown`）；水槽仍未被提取，补一个端点未解决两个参照物的问题。 |
| 1396 | 对→错 | 问题涉及两张沙发，补提取只给出左侧一张；模型在右侧沙发未定位时改选桌子，原本答对的“桌上花瓶”变错。 |
| 1455 | 对→错 | “两栋建筑”只补出左侧一栋，模型把树误判为两建筑之间的物体；图中的天使雕像更符合题目。 |

触发与成本：46 题中 45 题调用了第二次提取，42 题确实加入对象，共加入 54 个对象；6 题补提取后仍有至少一个文本意义上的缺失。三个触发但未加入对象的 ID 为 505、867、1438，其中 `desks consistent` 等短语显示触发规则本身也会误识别。两组逐题 `total_seconds` 合计约 1182 秒与 1603 秒，repair 组多约 421 秒（每题约 9.2 秒）；其中 `reference_repair_seconds` 合计约 273 秒。计时属于本次服务器运行，不包括模型加载和文件系统波动。

**决策：当前 `repair` 实现不用于完整 1400 题，保留默认 `off`。** 这 46 题是预先筛出的疑似漏参照候选，不是随机总体样本，但在目标子集上已经观察到净退化与明确的视觉/推理误伤。后续若重新考虑补提取，需要先解决多实例端点、整句误触发、参照点有效性，以及“近/中间”题中几何证据压过直接图像语义的问题，再使用固定配对集重新验证。按原计划可转入第三关“现有几何证据的使用范围”分析，仍不引入新的空间表征或改知识注入。
