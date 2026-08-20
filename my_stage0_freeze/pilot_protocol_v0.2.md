# Pilot-A / Pilot-B 执行与验收协议

> **本文件是七道 stop/go 门的唯一规范定义。** 其他文件只能引用，不得复述阈值。
> 规范见 `scope.md`，理由见 `decisions.md`，符号见 `notation.md`，单位见 `units.md`，数值见 `experiment_space.yaml`。

本文件回答四个问题：

1. 当前 MILP 是否正确、数值稳定并具有真实的分支搜索难度；
2. SCIP 分支候选、LP 图和 strong-branching 标签接口是否可靠；
3. 更好的分支选择是否存在足够的结构性改进空间；
4. GNN 的端到端开销是否可能小于其节省的求解时间。

**正式训练标签、正式训练、ID test 和 OOD 均不得早于 Pilot-A 通过。** Pilot-B 只验证已选模型的实现、计时与回退，**不允许用其结果重新调模型、生成器或求解预算**。

目标不是保证 GNN 获胜，而是在接触正式测试集之前给出可审计的 `GO / REVISE / STOP` 结论。**任何失败都必须留下结果，不得删除或替换不利实例。**

---

## 1. 阶段边界

### 1.1 Pilot-A（训练前）

使用与正式数据完全隔离的 pilot 场景（小/中/大各三分之一，数量见 `yaml: frozen_reference_parameters.pilot_scenario_count`）。产物编号：

| 编号 | 内容 |
|---|---|
| `A0` | 生成器、单位、系数、MILP 与小实例最优解核对 |
| `A1` | 全部 pilot 场景运行原生 SCIP 默认分支，60 s 保存检查点 |
| `A2` | 同一批运行继续至 300 s，直接校准正式时限 |
| `A3` | 候选映射与 strong-branching 教师接口验收 |
| `A4` | 完整标签采样路径验收（不是只检查根节点） |
| `A5` | full-strong 结构性 headroom 与 shadow inference 开销验收 |
| `A6` | 输出冻结报告和 `GO / REVISE / STOP` 决定 |

> **A0–A6 是产物编号，不是强制执行次序。** 推荐执行次序为
> `A0 → A1/A2 → A5-headroom → 判门 1、3、6 → A3 → A4 → 判门 2、5、7 → A5-shadow → 判门 4 → A6`。
> 理由：门 3 是七道门中**唯一可能直接判 `STOP` 的门**，而它只需要把 SCIP 内置 `vanillafullstrong` 分支规则的 priority 调高即可执行，不需要候选映射，也不需要教师接口 spike（离线打标签才需要 `donotbranch=true` 的 C 层接口；headroom 要的恰恰是 `donotbranch=false`）。先跑最便宜的 kill switch，可以在投入接口开发之前得到"方向是否成立"的答案。
> A5 的 shadow inference 部分依赖最终 GNN 结构，因此天然排在最后。

Pilot-A 可以生成诊断标签，但**这些标签必须在验收后删除，不得进入训练或验证**。

### 1.2 Pilot-B（训练后彩排）

只能在以下条件**全部**满足后执行：

- Pilot-A 已记录为 `GO`；
- 生成器、模型、数据划分、特征、教师、GNN 结构和求解参数均已冻结；
- 三个训练种子的 validation 求解诊断已完成；
- 入选 checkpoint 已由预声明规则确定并写入 manifest。

**必须使用实际入选 checkpoint，而不是固定使用训练种子 0。** 四个必需方法在全部 pilot 场景上运行 60 s；medium 和 large 各按 seed 取前 5 个场景，预先把零基 `repeat_index=0` 标为续跑运行，并把**该同一求解过程**继续至 300 s；若它在 60 s 前已终止，则保持终态而不重启。

Pilot-B 失败只允许修复**不改变研究含义**的实现错误；任何会影响可行域、实例分布、模型输入、标签、训练或求解参数的修改都要求建立新版本并**重新执行 Pilot-A**。

60 s 与 300 s 的方法排序是否反转必须报告，但**不是通过门、调参理由或 checkpoint 重选依据**。

---

## 2. A0：静态、单位与模型验收（七道门的前置正确性条件）

### 2.1 必须通过的单元测试

- 固定随机种子可**逐字节重建**场景表、用户表、候选表和接入边表；
- dB/线性量、W/Hz、Hz、bit/s、Wh/J 的转换与 `units.md` 一致；
- 内部建模统一采用 MHz/Mbit/s/kJ 缩放，导入与导出**可无损还原**；
- 每个预处理删除对象**只有一个主原因码**，并保存全部判定输入；
- 极小实例用枚举或独立方法得到的最优目标与 SCIP 一致；
- 构造解 \(y=x=b=z=0,\ \delta=q\) 按模型定义可行；
- 加入逐边紧上界和有效不等式**前后**，极小实例的整数可行域与最优值一致；
- 逐边安全删边只在 \(M_{ul}<b_{\min}-1\ \mathrm{Hz}\) 时执行；相等或差值不超过 1 Hz 的边保留，并用**边界样例**测试不会误删；
- 目标四个分量与总目标可由解文件**独立重算**；
- 所有方法加载同一模型和同一 SCIP 参数文件（标识见 `yaml: frozen_reference_parameters.scip_parameter_file_id`），开始 Pilot-A 前保存并核对其内容哈希。

### 2.2 必须新增的实测项

- **实测最大单程飞行距离**：用实际生成的候选点与集结点坐标算出全部主 ID/OOD 的最大 \(d_l^{\mathrm{fly}}\)，与 `units.md` §6 的 \(d_{\mathrm{bind}}\) 比较，据此判定能量约束是否静态冗余并记录。**不得引用任何文档中的估算值。**
- **逐位置能量 slack**：全部候选位置的能量 slack 分布。
- **续跑等价性**：同一实例"先跑 60 s 再续到 300 s"与"直接连续跑 300 s"必须得到相同的节点数、LP 迭代数和终止状态。这个测试不通过，A2 与 Pilot-B 的续跑子集就没有意义。
- **平凡解注入生效**：提交后求解器确实接受该解（检查返回值，不是只调用），且其目标值与独立 evaluator 一致。

---

## 3. A1/A2：默认 SCIP 难度画像

### 3.1 每实例必记字段

**生成与预处理**：split、scale、scenario id、seed、内容哈希；原始/保留候选数及按原因删除数；原始/保留接入边数及按原因删除数；零度用户数与关键零度用户数。

**原始模型与 presolve**：变量总数与二进制/整数/连续数；约束与非零元数量；presolve 后对应数量；fixed / aggregated / multi-aggregated / deleted 变量数量；presolve 时间、根 LP 时间、根 cuts 轮数、LP 迭代数。

**搜索**：根节点是否结束；首 incumbent 时间、目标与来源；总墙钟、节点数、LP 迭代数、最大深度、终止状态；incumbent、dual bound、固定跨度 normalized gap 与 nPDI；深度 0–8 的 LP 分支回调数与 GNN-eligible 节点数；每个 eligible 节点的 `nlpcands`、`npriolpcands`、`nfracimplvars` 及 \(y/x/z\) 类型计数。

**方案结构**：\(H_C\)、\(Q_C\)、\(R_{\mathrm{all}}\)、\(D_{\mathrm{frac}}\) 与总目标；部署 UAV 数、服务用户数、关键用户达标数；UAV 带宽/位置回传/共享网关/能量约束的最小与中位 slack 及活跃数量；**是否同时满足门 6 的三个条件**。

### 3.2 时间分箱

每个规模分别报告：root solved / \(0<t\le1\) s / \(1<t\le2\) s / \(2<t\le10\) s / \(10<t\le60\) s / 60 s timeout。

全部实例都保存 60 s 检查点并在**相同配置**下继续至 300 s。60 s 与 300 s 的终止状态、bound、节点和 normalized gap 必须**成对报告**。这些运行不用于筛选正式实例。

---

## 4. A3：候选映射与教师接口验收

### 4.1 候选集合与映射

允许评分的集合严格定义为 `getLPBranchCands()` 返回数组的**前 `npriolpcands` 个当前 transformed LP candidates**。不得把随后附加的 fractional implicit integer variables、非优先候选或已被 presolve 固定/聚合的变量加入掩码。

每次 LP 分支回调都必须重新建立
`current transformed Variable <-> current LP Column <-> graph variable row`。
原始业务变量编号只用于追溯语义。**不得按变量名、原始建模顺序或上一次回调的 LP position 直接复用映射。**

**验收测试至少覆盖**：未发生 presolve 聚合的节点；fixed / aggregated / multi-aggregated 原始变量；cuts 加入后的 LP 行列变化；局部变量界变化；无 LP candidates；只有非优先候选；mapping 故障回退。

任何不一致必须返回 `DIDNOTRUN` 让固定的 SCIP 默认分支器继续；**只有实际创建了分支子节点才返回 `BRANCHED`**。

### 4.2 strong-branching 教师硬门

正式标签生成前必须完成独立的 `expert_interface_spike`：

1. 首选包装并验证 SCIP native vanilla full strong 的全候选分数接口；
2. 离线标签查询明确并保存 `collectscores=true`、`scoreall=true`、`integralcands=false`、`idempotent=true`、`donotbranch=true`；
3. 能在当前 LP 节点**完整评分全部 `npriolpcands`**；
4. 调用遵守 SCIP strong-branching 的 start/end 生命周期且**不破坏后续求解状态**；
5. 分数、有效标志、上下分支结果、候选顺序和最终最佳集合可稳定保存；
6. 同一固定实例、版本、参数和种子**重复运行得到相同的有效候选与选择**；
7. 根节点以及深度 1–8 的抽样节点均通过映射和完整性检查。

**parity 判据（Pilot-A 前冻结）**：候选身份、顺序和有效性标志必须**精确一致**；上下分支增益与综合分数逐项满足 \(|a-b|\le10^{-9}+10^{-7}\max(|a|,|b|)\)；native 选择的候选必须属于用冻结 \(\tau_{\mathrm{tie}}\) 得到的项目并列最佳集合（**不要求浮点 argmax 唯一**）。每个实际执行的对比回调都进入分母，任一违反均记为一次 parity 错误。

若在冻结版本下无法稳定复现 native 接口，则允许改用逐候选 `getVarStrongbranch()` 定义的 Python-side oracle，但必须：

- 将教师名称和论文措辞统一改为 `project-defined Python-side all-candidate strong-branching oracle`；
- 冻结上下增益到综合分数的公式和数值处理；
- 完成与 SCIP native 选择的 parity 测试；
- 在 `decisions.md` 新增版本化决定。

**不得把教学式 Python 循环静默称为 native vanilla full strong。**

---

## 5. A4：标签路径验收

全部 pilot 场景中，**只要根节点存在至少一个优先 LP 分支候选，就必须尝试一次根教师查询**；完整根标签率的分母是每档全部此类实例，**不得根据耗时、候选数或预期成功率筛选**；任一档零分母**不能按 `0/0` 通过**。

深度 1–8 的完整抽样轨迹在每档按场景 seed 从小到大选择**前 5 个**根节点可分支实例；任一档不足 5 个即判教师接口/机会门失败。轨迹必须实际执行冻结的采样规则（根必查、深度 1–8 按概率抽样、每实例最大标签数、未抽样节点 pseudo-cost、单实例标签时限），参数见 `yaml: confirmed_approach.supervision.sampling`。

**除总有效率外，必须按规模、深度、候选数和变量类型报告**：查询节点数/完整标签数/丢弃数；根与非根标签耗时分布；实例级中断率；丢弃原因；strong score 为零的比例；并列集合大小与 top-1/top-2 相对分差；教师所选 \(y/x/z\) 类型分布；每实例实际标签数。

**只测根节点不算接口通过。** 全部 Pilot-A 标签在结束后丢弃。

---

## 6. A5：AI 机会、教师 headroom 与推理经济性

### 6.1 full-strong headroom

medium 和 large 分别按场景种子从小到大选择**最多 10 个**根后仍可分支实例；**每档不足 5 个则该门失败**。用相同模型、参数、时限和单线程设置比较 SCIP default 与 full strong。

- 该运行必须覆盖离线查询的 `donotbranch=true`：native 规则使用 `donotbranch=false`，Python-side 规则则在评分后通过 SCIP **对所选变量真正建枝**。**没有提交分支的运行无效。**
- **full strong 的墙钟时间不作为教师可部署性的判断**；此处比较的是配对节点数和 LP 迭代数，用以判断分支选择是否有结构性改进空间。
- 主 headroom 只在**双方均于 300 s 内证明最优**的配对上计算，每档至少需要 5 个可比配对；不足即判该门不可证而失败。
- 超时对仍完整保留并另列状态。**不能把 full strong 因单节点较慢而处理较少节点误判成更小的搜索树。**

**统计量的精确定义（v0.3 消歧）**：对每个可比配对 \(j\) 计算逐实例降幅

\[
\Delta^{\mathrm{node}}_j=1-\frac{\text{nodes}^{\mathrm{fullstrong}}_j}{\text{nodes}^{\mathrm{default}}_j},
\qquad
\Delta^{\mathrm{lp}}_j=1-\frac{\text{lpiters}^{\mathrm{fullstrong}}_j}{\text{lpiters}^{\mathrm{default}}_j}
\]

门 3 判定使用 \(\operatorname{median}_j\Delta^{\mathrm{node}}_j\) 与 \(\operatorname{median}_j\Delta^{\mathrm{lp}}_j\)，即**逐实例配对降幅的中位数**，而不是"中位节点数之比"。二者不是同一统计量；本协议以前者为准，早期表述中的"中位节点数下降"应按此理解。

### 6.2 shadow inference

使用与拟议主 GNN **完全相同**的图提取、张量转换、网络结构、隐藏维度、调用条件和单线程 CPU 设置执行，但最终返回 `DIDNOTRUN` 由 SCIP 默认分支。**shadow 模型无需训练**——本门测量的是调用成本而非准确率，固定的未训练 checkpoint 即可。

分别记录：图结构提取时间、动态特征更新时间、CPU 张量构造/复制时间、forward 时间、候选掩码与后处理时间、日志开销；以及每实例累计 AI 开销及其相对 default 求解时间的比例。

---

## 7. 七道硬门与决定规则

> 以下数值是本版本的工程 stop/go 标准，**不是普适理论结论，也不是论文效果结论**。它们在运行 Pilot-A 前冻结。
> A0 的缩放等价、独立目标/界复算和系统性数值错误审计是**前置正确性条件**，不另算第八道门。

| # | 类别 | 门 | 判定范围 |
|---|---|---|---|
| 1 | 难度 | `root solved 或总时间 ≤ 2 s` 的实例比例 **≤ 50%** | medium、large 分别判定，两档都须通过 |
| 2 | 机会 | 至少 **50%** 实例在深度 0–8 内具有 **≥ 10 个** GNN-eligible 节点 | medium、large 分别判定，两档都须通过 |
| 3 | headroom | 逐实例配对降幅的中位数 \(\operatorname{median}_j\Delta^{\mathrm{node}}_j\) 或 \(\operatorname{median}_j\Delta^{\mathrm{lp}}_j\) **至少一项 ≥ 20%** | medium、large 分别在 §6.1 的可比配对子集上判定，两档都须通过 |
| 4 | 经济性 | shadow inference 的每实例"累计 AI 开销 / default 墙钟"比值**中位数 ≤ 10%** | medium、large 分别判定，两档都须通过 |
| 5 | 标签 | 完整根标签率 **≥ 80%** | small、medium、large 各自判定；全部根节点可分支实例都必须尝试查询 |
| 6 | 信息量 | 同时满足全部关键用户 \(z_u=1\)、独立 evaluator 重算 \(Q_C\le10^{-8}\) 且共享网关利用率 \(\sum_uS_u/C_G\ge0.95\) 的实例比例 **≤ 80%** | medium、large 分别判定 |
| 7 | 正确性 | 候选映射**零错误**；教师 parity 按 §4.2 的身份/顺序精确规则与 `atol=1e-9, rtol=1e-7` 数值规则**零不一致**；全部故障注入触发预期回退 | 全局 |

门 1–4 是机会与经济性门，门 5–7 是标签、科学信息量与接口正确性门。

**决定规则**：

- 全部硬门通过 → **`GO`**，冻结当前生成器与模型，允许正式标签生成；
- 任一接口、可行域、单位或数值正确性门失败 → **`REVISE`**；
- 难度、机会、headroom、经济性或目标冲突门失败 → **`REVISE`**，建立下一版本后重新执行完整 Pilot-A；
- 在现实可辩护的规模阶梯上连续失败，或 full strong 无结构性 headroom → **`STOP learned branching`**，保留负结果并重新选择 AI 任务。

**不得用多个门的平均表现抵消任一 P0 正确性门失败。**

---

## 8. Pilot-A 失败后的处置

**允许且必须版本化**：

- 修复公式、单位、候选映射、教师或计时实现错误；
- 在保持现实密度或明确业务情景的前提下，按**预声明的规模阶梯**增加用户和候选点；
- 从 pilot-only 数据校准资源冲突分布，并重新生成全部正式分区；
- 用有来源的任务包络重新定义能量活跃场景；
- 将昂贵的全 GNN 改为 root-only 或"根部 GNN + 后续廉价策略"的混合版本。

**禁止**：

- 关闭或削弱 SCIP presolve、cuts、heuristics；
- 使用更松的 Big-M 制造搜索树；
- 根据 GNN 的表现选择实例或参数；
- 查看 ID test / OOD 后修改生成器；
- 从正式结果中删除根节点可解、GNN 未调用或 GNN 变慢的实例；
- 不留决策记录地反复搜索一个"刚好让 AI 赢"的分布。

---

## 9. Pilot-B 与正式计时规则

### 9.1 模型选择

三个训练种子都必须在同一 validation solve 子集上报告 validation loss、节点、LP 迭代、墙钟时间和尾部减速。**checkpoint 选择规则在运行前冻结；Pilot-B 使用由该规则实际选出的 checkpoint。**

只部署变量版本复用同一 checkpoint，仅改变候选掩码，因此**只能解释为"同一模型的部署候选掩码消融"**，不能解释为独立训练 deployment-only GNN 的能力。

### 9.2 运行顺序与计时

计时与顺序的完整规范见 `scope.md` §8.3。Pilot-B 额外必须验证的两件事：

- **SCIP 的 time limit 在 Python callback 存在时的实际语义**，并报告同步调用造成的任何时限越界；若不能保证，必须以外部硬限制和一致终止规则修订协议；
- **续跑子集**：方法顺序清单在运行前把零基 `repeat_index=0` 标为续跑；该次从 60 s 检查点继续而**不重启**，其他两个短任务重复只运行至 60 s。

---

## 10. 必需产物

**Pilot-A 完成后**：

| 文件 | 内容 |
|---|---|
| `pilot_a_manifest.json` | 代码、配置、数据、环境和硬件哈希 |
| `pilot_a_instances.csv` | 每实例汇总（§3.1 全部字段） |
| `pilot_a_nodes.parquet` | 仅 pilot 的节点级候选与映射诊断 |
| `pilot_a_labels.parquet` | 随后删除的诊断标签及丢弃原因 |
| `pilot_a_report.md` | 分层统计、图表、各硬门结果和最终决定 |
| `pilot_a_decision.json` | `GO / REVISE / STOP`、失败门和下一版本编号 |

**Pilot-B 完成后**：独立 manifest 和报告，并明确确认"**未根据 Pilot-B 结果重新调参**"。

**正式实验只有在两个 manifest、入选 checkpoint 哈希与冻结配置相互一致时才允许开始。**

---

## 11. 预算报告口径

预算组件与规划包络见 `yaml: evaluation_protocol.full_project_compute_budget` 与 `scope.md` §11。

预算报告必须**分别列出**：正式求解 CPU h、pilot 与敏感性 CPU h、专家标签 CPU h、训练 CPU/GPU h、full-strong 与审计 CPU h、失败重跑和开发性运行。

**预算不足只能减少预先声明的非主分析或建立新版本，不能静默缩短某个方法的正式时限。**
