# Pilot-A / Pilot-B 执行与验收协议 v0.2

## 1. 文件职责与总原则

本文件是 Stage 0 v0.2 的实现验收规范。它回答四个问题：

1. 当前 MILP 是否正确、数值稳定并具有真实的分支搜索难度；
2. SCIP 分支候选、LP 图和 strong-branching 标签接口是否可靠；
3. 更好的分支选择是否存在足够的结构性改进空间；
4. GNN 的端到端开销是否可能小于其节省的求解时间。

正式训练标签、正式训练、ID test 和 OOD 均不得早于 Pilot-A 通过。Pilot-B 只验证已选模型的实现、计时与回退，不允许用其结果重新调模型、生成器或求解预算。

v0.2 的目标不是保证 GNN 获胜，而是在接触正式测试集之前给出可审计的 `GO / REVISE / STOP` 结论。任何失败都必须留下结果，不得删除或替换不利实例。

## 2. 阶段边界

### 2.1 Pilot-A：训练前验收

Pilot-A 使用与正式数据完全隔离的 60 个场景，小、中、大各 20 个。按以下顺序执行：

1. `A0`：生成器、单位、系数、MILP 与小实例最优解核对；
2. `A1`：全部 60 个场景运行原生 SCIP 默认分支，并在 60 s 保存检查点；
3. `A2`：同一批 60 个运行继续至 300 s，直接校准正式时限；
4. `A3`：候选映射与 strong-branching 教师接口验收；
5. `A4`：完整标签采样路径验收，而非只检查根节点；
6. `A5`：full-strong 结构性 headroom 与 shadow inference 开销验收；
7. `A6`：输出冻结报告和 `GO / REVISE / STOP` 决定。

Pilot-A 可以生成诊断标签，但这些标签必须在验收后删除，不得进入训练或验证。

### 2.2 Pilot-B：训练后彩排

Pilot-B 只能在以下条件全部满足后执行：

- Pilot-A 已记录为 `GO`；
- 生成器、模型、数据划分、特征、教师、GNN 结构和求解参数均已冻结；
- 三个训练种子的 validation 求解诊断已经完成；
- 入选 checkpoint 已由预声明规则确定。

Pilot-B 必须使用实际入选 checkpoint，而不是固定使用训练种子 0。四个必需方法均在全部 60 个 pilot 场景上运行 60 s；medium 和 large 各按 seed 取前 5 个场景，预先把零基 `repeat_index=0` 标为续跑运行，并把该同一求解过程继续至 300 s；若它在 60 s 前已终止，则保持终态而不重启。Pilot-B 失败只允许修复不改变研究含义的实现错误；任何会影响可行域、实例分布、模型输入、标签、训练或求解参数的修改都要求建立新版本并重新执行 Pilot-A。60 s 与 300 s 的方法排序是否反转必须报告，但不是通过门、调参理由或 checkpoint 重选依据。

## 3. A0：静态、单位与模型验收

### 3.1 必须通过的单元测试

- 固定随机种子可逐字节重建场景表、用户表、候选表和接入边表；
- dB/线性量、W/Hz、Hz、bit/s、Wh/J 的转换与 `units.md` 一致；
- 内部建模统一采用 MHz、Mbit/s 和 kJ 缩放，导入与导出时可无损还原；
- 每个预处理删除对象只有一个主原因码，并保存全部判定输入；
- 极小实例用枚举或独立方法得到的最优目标与 SCIP 一致；
- `y=x=b=z=0, delta=q` 的构造解按模型定义可行；
- 加入逐边紧上界和有效不等式前后，极小实例的整数可行域与最优值一致；
- 逐边安全删边只在 `M_ul < b_min - 1 Hz` 时执行；相等或差值不超过 1 Hz 的边保留，并用边界样例测试不会误删；
- 目标四个分量与总目标可由解文件独立重算；
- 所有方法加载同一模型和同一 SCIP 参数文件，只有分支规则不同；v0.2 参数文件标识为 `scip_10_0_2_stage0_v0_2.set`，开始 Pilot-A 前保存并核对其内容哈希。

### 3.2 冻结参考能量审计

冻结参数下，满 20 MHz 的通信能耗为 6,000 J，固定悬停、基础设备与起降能耗为 1,182,000 J，往返巡航能耗系数为约 110 J/m。满带宽能量约束只在飞行距离约 2,982 m 之后可能生效，而当前全部主 ID/OOD 候选的最大预期距离约为 2,797 m。

因此 v0.2 将主参考能量约束解释为安全可行性约束，并预期其在主参考场景中不活跃。实现必须重新计算并记录每个候选的能量 slack，但不得声称该约束删除候选或驱动部署，除非运行日志提供相反证据。

若后续研究要求能量成为主要决策冲突，必须建立新版本、提供任务时长或平台参数依据并重新生成所有数据；不得为了增加 SCIP 难度而临时降低电池容量。

## 4. A1/A2：默认 SCIP 难度画像

### 4.1 每实例必记字段

生成与预处理：

- split、scale、scenario id、seed 和内容哈希；
- 原始/保留候选数以及按原因删除的候选数；
- 原始/保留接入边数以及按原因删除的边数；
- 零度用户数和关键零度用户数。

原始模型和 presolve：

- 变量总数、二进制/整数/连续变量数；
- 约束和非零元数量；
- presolve 后对应数量；
- fixed、aggregated、multi-aggregated 和 deleted 变量数量；
- presolve 时间、根 LP 时间、根 cuts 轮数和 LP 迭代数。

搜索：

- 根节点是否结束；
- 首 incumbent 时间、目标和来源；
- 总墙钟时间、节点数、LP 迭代数、最大深度和终止状态；
- incumbent、dual bound 和固定跨度 normalized gap；
- 深度 0--8 的 LP 分支回调数、GNN-eligible 节点数；
- 每个 eligible 节点的 `nlpcands`、`npriolpcands`、`nfracimplvars` 及 `y/x/z` 类型计数。

方案结构：

- `H_C`、`Q_C`、`R_all`、`D_frac` 和总目标；
- 部署 UAV 数、服务用户数和关键用户达标数；
- UAV 带宽、位置回传、共享网关和能量约束的最小/中位 slack 与活跃数量；
- 是否同时满足全部关键用户 `z_u=1`、独立 evaluator 重算 `Q_C<=1e-8` 且共享网关利用率至少 0.95。

### 4.2 时间分箱

每个规模分别报告：

- root solved；
- `0 < time <= 1 s`；
- `1 < time <= 2 s`；
- `2 < time <= 10 s`；
- `10 < time <= 60 s`；
- 60 s timeout。

全部 60 个实例都保存 60 s 检查点并在相同配置下继续至 300 s。60 s 与 300 s 的终止状态、bound、节点和 normalized gap 必须成对报告；这些运行不用于筛选正式实例。

## 5. A3：SCIP 候选映射与教师接口验收

### 5.1 当前 LP 候选集合

GNN 和教师允许评分的集合严格定义为 `getLPBranchCands()` 返回数组的前 `npriolpcands` 个当前 transformed LP candidates。不得把随后附加的 fractional implicit integer variables、非优先候选或原始模型中已被 presolve 固定/聚合的变量加入掩码。

每次 LP 分支回调都必须重新建立以下映射：

`current transformed Variable <-> current LP Column <-> graph variable row`

原始业务变量编号只用于追溯语义，不要求与 transformed variable 或 LP column 一一对应。不得按变量名、原始建模顺序或上一次回调的 LP position 直接复用映射。

验收测试至少覆盖：

- 未发生 presolve 聚合的节点；
- fixed、aggregated 和 multi-aggregated 原始变量；
- cuts 加入后 LP 行列变化；
- 局部变量界变化；
- 无 LP candidates、只有非优先候选以及 mapping 故障回退。

任何不一致必须返回 `DIDNOTRUN`，让固定的 SCIP 默认分支器继续；只有实际创建了分支子节点才返回 `BRANCHED`。

### 5.2 strong-branching 教师硬门

正式标签生成前必须完成独立 interface spike：

1. 首选包装并验证 SCIP native vanilla full strong 的全候选分数接口；
2. 对离线标签查询明确并保存 `collectscores=true`、`scoreall=true`、`integralcands=false`、`idempotent=true` 和 `donotbranch=true`；
3. native 最佳候选与项目并列最佳集合比较，不要求浮点 argmax 唯一；
4. 候选身份、顺序与有效性标志必须精确相等；上下分支增益和综合分数逐项满足 `|a-b| <= 1e-9 + 1e-7*max(|a|,|b|)`；
5. 在人工和真实节点上核对候选数、上下分支增益、综合分数和最佳集合，所有实际执行的对比回调都进入 parity 分母。

如果 PySCIPOpt 6.2 下无法稳定复现 native 接口，则允许改用逐候选 `getVarStrongbranch()` 定义的 Python-side oracle，但必须：

- 将教师名称和论文措辞统一改为 `project-defined Python-side all-candidate strong-branching oracle`；
- 冻结上下增益到综合分数的公式和数值处理；
- 完成与 SCIP native 选择的 parity 测试；
- 在 `decisions.md` 新增版本化决定。

不得把教学式 Python 循环静默称为 native vanilla full strong。

## 6. A4：标签路径验收

全部 60 个 Pilot-A 场景中，只要根节点存在至少一个优先 LP 分支候选，就必须尝试一次根教师查询；完整根标签率的分母是每档全部此类实例，不得根据耗时、候选数或预期成功率筛选，任一档零分母不能按 `0/0` 通过。深度 1--8 的完整抽样轨迹在每档按场景 seed 从小到大选择前 5 个根节点可分支实例；任一档不足 5 个即判教师接口/机会门失败。除总有效率外，必须按规模、深度、候选数和变量类型报告：

- 查询节点数、完整标签数和丢弃数；
- 根与非根标签耗时分布；
- 120 s 实例级中断率；
- 丢弃原因；
- strong score 为零的比例；
- 并列集合大小以及 top-1/top-2 相对分差；
- 教师所选 `y/x/z` 类型分布；
- 每实例实际标签数。

每档完整根标签率必须至少为 80%。低于该值，或困难/深层节点的缺失率明显高于容易/浅层节点而无法通过加权报告解释时，结论为 `REVISE`，不得生成正式训练集。

## 7. A5：AI 机会、教师 headroom 与推理经济性

### 7.1 full-strong headroom

medium 和 large 分别按场景种子选择最多 10 个可分支实例；每档不足 5 个则 headroom 门失败。用相同模型、参数、时限和单线程设置比较 SCIP default 与 full strong。

full strong 的墙钟时间不作为教师可部署性的判断；此处主要比较配对节点数和 LP 迭代数，以判断分支选择是否有结构性改进空间。该求解运行必须覆盖离线查询的 `donotbranch=true`：native 规则使用 `donotbranch=false`，Python-side 规则则在评分后通过 SCIP 对所选变量真正建枝；没有提交分支的运行无效。主 headroom 中位下降只在双方均于 300 s 内证明最优的配对上计算，每档至少需要 5 个可比配对；不足即失败。超时对仍完整保留并另列，不能把 full strong 因单节点较慢而处理较少节点误判成更小的搜索树。

### 7.2 shadow inference

使用与拟议主 GNN 相同的图提取、张量转换、网络结构和单线程 CPU 设置执行 shadow inference，但最终返回 `DIDNOTRUN`，由 SCIP 默认分支。分别记录：

- 图结构提取时间；
- 动态特征更新时间；
- CPU 张量构造/复制时间；
- forward 时间；
- 候选掩码和后处理时间；
- 每实例累计 AI 开销及其相对默认求解时间比例。

shadow 模型无需训练，但结构、隐藏维度和调用条件必须与拟议主模型一致。

## 8. Pilot-A 硬门与决定规则

以下数值是 v0.2 的七道工程 stop/go 标准，不是普适理论结论。缩放等价、独立目标/界复算和系统性数值错误审计属于 A0 前置正确性条件，不另算第八道门。

1. medium 和 large 分别判定，`root solved 或总时间 <= 2 s` 的实例比例不得超过 50%，两档都通过；
2. medium 和 large 分别判定，至少 50% 的实例在深度 0--8 内具有不少于 10 个 GNN-eligible 节点，两档都通过；
3. medium 和 large 分别在规定的可分支配对子集上判定；full strong 相对 default 的每实例节点数或 LP 迭代数降幅，其中至少一个指标的配对中位数必须达到 20%，两档都通过；
4. medium 和 large 分别判定 shadow inference 的每实例累计 AI 开销占 default 墙钟时间比例的中位数不得超过 10%，两档都通过；
5. small/medium/large 中全部根节点可分支实例都必须尝试查询，各档完整根标签率必须至少达到 80%；
6. medium/large 中同时满足全部关键用户 `z_u=1`、独立 evaluator 重算 `Q_C<=1e-8` 且共享网关利用率 `sum_u S_u/C_G>=0.95` 的实例比例不得超过 80%，否则目标冲突被判定为退化；
7. 候选映射必须零错误；教师 parity 按身份/顺序精确匹配和 `atol=1e-9, rtol=1e-7` 的数值规则必须零不一致；可恢复异常必须全部触发已定义回退。

决定规则：

- 全部硬门通过：`GO`，冻结当前生成器与模型，允许正式标签生成；
- 任一接口、可行域、单位或数值正确性门失败：`REVISE`；
- 难度、机会、headroom、经济性或目标冲突门失败：`REVISE`，建立下一版本后重新执行完整 Pilot-A；
- 在现实可辩护的规模阶梯上连续失败，或 full strong 无结构性 headroom：`STOP learned branching`，保留负结果并重新选择 AI 任务。

不得用多个门的平均表现抵消任一 P0 正确性门失败。

## 9. Pilot-A 失败后允许的修改

允许且必须版本化：

- 修复公式、单位、候选映射、教师或计时实现错误；
- 在保持现实密度或明确业务情景的前提下按预声明规模阶梯增加用户和候选点；
- 从 pilot-only 数据校准资源冲突分布，并重新生成全部正式分区；
- 用有来源的任务包络重新定义能量活跃场景；
- 将昂贵的全 GNN 改为 root-only 或根部 GNN、后续廉价策略的混合版本。

禁止：

- 关闭或削弱 SCIP presolve、cuts、heuristics；
- 使用更松的 Big-M 制造搜索树；
- 根据 GNN 的表现选择实例或参数；
- 查看 ID test/OOD 后修改生成器；
- 从正式结果中删除根节点可解、GNN 未调用或 GNN 变慢的实例；
- 不留决策记录地反复搜索一个“刚好让 AI 赢”的分布。

## 10. Pilot-B 与正式计时规则

### 10.1 模型选择

三个训练种子都必须在同一 validation solve 子集上报告 validation loss、节点、LP 迭代、墙钟时间和尾部减速。checkpoint 选择规则在运行前冻结；Pilot-B 使用由该规则实际选出的 checkpoint。

只部署变量版本复用同一 checkpoint，仅改变候选掩码，因此只能解释为“同一模型的部署候选掩码消融”，不能解释为独立训练 deployment-only GNN 的能力。

### 10.2 运行顺序与计时

- 方法顺序采用按实例预生成的平衡顺序，使每个方法在各顺序位置出现次数尽量相同；
- 正式求解不并发，SCIP 与 PyTorch 均为单线程；
- 外部单调时钟包住整个 `optimize()`，同时保存 SCIP 内部时间；
- 验证 SCIP time limit 是否包含 Python callback；若不能，必须以外部硬限制和一致终止规则修订协议；
- 默认运行不超过 10 s 的配置重复 3 次，主时间采用中位数；节点、LP 迭代和解状态仍应确定性一致；
- 对预声明的 300 s 续跑子集，方法顺序清单在运行前把零基 `repeat_index=0` 标为续跑；该次从 60 s 检查点继续而不重启，其他两个短任务重复只运行至 60 s；
- 60 s 与 300 s 排序变化只作报告，不改变 Pilot-B 通过状态、checkpoint 或任何冻结参数；
- 正式墙钟包含图提取、传输、forward、后处理和低开销日志。

## 11. 指标与统计

### 11.1 固定跨度 normalized gap

冻结参考权重的逐分量安全解析范围为 `[-0.21,0.79]`，不声称端点可达；目标跨度固定为 1.0。对最大化问题，存在 incumbent 时定义：

`normalized_gap(t) = max(0, dual_bound(t) - incumbent(t)) / 1.0`

该指标对目标加常数保持不变，是正式 nPDI 和 1% normalized gap 诊断的 gap 定义。计时起点向所有方法提交并验证同一平凡可行解 `y=x=b=z=0, delta=q`。有效 dual 在 SCIP 首次返回有限上界前取参考权重的逐分量解析上界 `alpha_H+alpha_R=0.79`，之后取 `min(0.79, SCIP dual)`；若仍无 incumbent，视为实现错误并将运行标记为无效，不能静默填零。权重敏感性使用对应 profile 的 `alpha_H+alpha_R`，不得硬套 0.79；其权重和仍为 1，因此归一化跨度仍为 1.0。SCIP 原生相对 gap 仍保存为调试字段，但不作为跨 0 目标的主 nPDI 定义。

正式无量纲指标定义为：

`normalized_PDI = (1 / 300 s) * integral_[0,300 s] normalized_gap(t) dt`

积分按 incumbent 或有效 dual 更新事件构造的分段常数轨迹计算，不作结果驱动的额外截断或平滑。

### 11.2 声明顺序

1. 主指标：300 s 内的 normalized primal-dual integral，全部实例场景级配对；
2. 确认性指标：证明最优比例、最终 normalized gap；
3. 效率指标：共同证明最优实例上的配对时间，以及全部实例的节点和 LP 迭代；
4. 安全指标：P90/P95 减速、超时变化、GNN 调用与回退分布；
5. 模仿指标：validation 标签上的 top-k、遗憾和标签分布，只作诊断。

### 11.3 推断单位

- 配对单位和 bootstrap 单位均为基础场景，不是分支节点；
- ID 按 small/medium/large 分层，先在层内重采样，再按冻结比例合并；
- paired bootstrap 使用 10,000 次固定种子重采样并报告 95% 区间；
- 主结果包含全部场景；`GNN-eligible` 子集只用于解释机制，不能替代主结论；
- win/tie/loss 的时间 tie 容差固定为相对默认时间的 1%；短任务使用三次中位数后再判定，不得在正式结果后改值。

## 12. 泄漏与复现

- 场景、其变体和全部树节点始终位于同一 split；
- 特征均值、标准差、裁剪阈值和任何数据驱动预处理只在 training 场景拟合；
- 图和特征缓存按 split 使用不同目录，缓存键包含场景内容哈希、模型版本和 SCIP build；
- 正式生成前对所有场景内容哈希查重，跨 split 重复为硬错误；
- 场景生成、标签节点抽样、训练初始化、方法顺序和 bootstrap 使用互相独立且被记录的种子；
- test/OOD 不生成 strong 标签，不参与 checkpoint、阈值、tie 容差或架构选择；
- 保存生成器、模型代码、参数文件、环境、checkpoint 和分析脚本哈希。

## 13. 预算口径

`300 实例 × 4 方法 × 300 s = 100 CPU h` 只表示正式四方法全部跑满的上界。v0.1 已列组件按各自时限上限相加约 137.5 h；再计入 Pilot-A 默认 SCIP 校准和三 seed validation solve diagnostics，可量化部分约 144 h。加入 20% contingency 后当前执行规划包络约 172.8 h。该数既不是最低消耗也不是总上限，因为 headroom/shadow、Pilot-B 300 秒子集、短任务重复、失败重跑、接口开发、数据生成和分析尚未完全定界。

预算报告必须分别列出：

- 正式求解 CPU h；
- pilot 与敏感性 CPU h；
- 专家标签 CPU h；
- 训练 CPU/GPU h；
- full-strong 与审计 CPU h；
- 失败重跑和开发性运行。

预算不足只能减少预先声明的非主分析或建立新版本，不能静默缩短某个方法的正式时限。

## 14. 必需产物

Pilot-A 完成后必须生成：

- `pilot_a_manifest.json`：代码、配置、数据、环境和硬件哈希；
- `pilot_a_instances.csv`：每实例汇总；
- `pilot_a_nodes.parquet`：仅 pilot 的节点级候选与映射诊断；
- `pilot_a_labels.parquet`：随后删除的诊断标签及丢弃原因；
- `pilot_a_report.md`：分层统计、图表、各硬门结果和最终决定；
- `pilot_a_decision.json`：`GO / REVISE / STOP`、失败门和下一版本编号。

Pilot-B 完成后必须生成独立 manifest 和报告，并明确确认“未根据 Pilot-B 结果重新调参”。正式实验只有在两个 manifest、入选 checkpoint 哈希与冻结配置相互一致时才允许开始。
