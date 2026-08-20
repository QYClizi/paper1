# Stage 0 研究规范（唯一生效）

> **本文件的地位**：这是当前实现、Pilot、训练与评测的唯一生效规范。
> **数值不写在这里。** 所有冻结数值的唯一真相源是 `experiment_space.yaml`；本文件出现数值时一律以 `yaml: 键路径` 的形式引用，代码只读 YAML，不得从本文件抄数字。
> **验收门不写在这里。** 七道 stop/go 门的规范定义、阈值和判定规则只在 `pilot_protocol_v0.2.md`。
> **理由不写在这里。** 每条选择"为什么这么定、排除了什么"见 `decisions.md`。
> 本文件只回答一件事：**规范是什么。**
>
> 协议标识 `stage0-v0.2`（`yaml: version`）。历史 v0.1 叙述层已在本次精简中合并去除；被 v0.2 推翻的旧条款不再出现在任何文件里，仅保留文末的修订对照表以备论文追溯。

---

## 1. 研究问题与总体方法

### 1.1 待解决问题

灾后地面接入基础设施受损、环境条件已知。在 UAV 可用数量、链路容量和能量预算等硬约束下，并考虑关键用户最低服务达标评价，联合优化：

1. UAV 基站部署位置；
2. 用户关联；
3. 下行接入带宽分配，以及固定回传容量约束下的业务流量承载。

区域内用户只能通过已部署 UAV 获得接入服务；残存地面设施只作为固定回传网关，不直接服务区域内用户，也不作为用户关联选项。第一版不优化地面基站修复或地面—空中接入选择。

### 1.2 总体方法

使用监督式图神经网络辅助数学优化求解器，对求解器当前节点中的合法分支候选进行**评分和排序**，而不是由神经网络直接产生最终方案。

求解器始终负责：

- 学习组件不从已定义的数学模型中排除任何可行解；
- 验证返回解的可行性和约束满足；
- 计算有效的原始界、对偶界和 MIP gap；
- 状态为 optimal 时提供模型与数值容差意义下的全局最优性证明；
- 达到非零 gap 容差时只声称该容差内的质量保证；
- 达到时间等资源限制时报告 incumbent、best bound 和 optimality gap，不声称每个实例均已证明最优。

术语：`incumbent` 是当前已找到的最好可行解；`best bound` 是分支定界搜索得到的、用于约束未知最优目标值的当前有效界；`optimality gap` 是二者之间的差距。

基于固定物理和运营规则的确定性预处理属于数学模型定义的一部分；SCIP 仍可执行数学上有效的 presolve 和 cuts。GNN 不从预处理后建立的模型中删除候选位置或用户连接，不执行永久变量固定或无安全证明的剪枝；GNN 失败、超时或不适用时，求解器使用默认分支策略。第一版不把 warm start 作为 GNN 的主任务。

### 1.3 研究定位与边界

定位为 `auditable and feasible-region-preserving learning-augmented branch-and-bound`（可审计且由学习组件保持既定可行域的学习增强分支定界）。

**是否能够控制尾部减速并实现可靠的跨场景泛化，必须由实验结果支持，不能在实验前作为既成结论。** 第一版不扩展到隐私、对抗攻击、因果推断或一般性 AI 公平研究。

设计原则：以快速完成项目为明确目标；模块输入、输出和职责边界必须明确；在符合现实需求并保留研究意义的前提下优先选择实现最简单、开发速度最快的结构；不为提高表面复杂度而加入非核心变量、无线机制或求解模块。

---

## 2. 建模边界（全部已冻结）

| 维度 | 冻结选择 | 明确排除 |
|---|---|---|
| 时间 | 单个静态灾后快照，实例内无时间下标 | 多时段联合优化、轨迹优化、跨时段移动/调度/能量耦合 |
| 不确定性 | 确定性；实例输入求解前全部准确已知 | 定位误差、需求随机性、信道估计误差、二次故障、在线信息更新 |
| 部署位置 | 有限水平候选点集合，规则网格生成后过滤；高度是场景参数 | 连续水平坐标优化、高度作为决策变量 |
| 机队 | 同质 UAV，同实例共用通信/功率/能量参数 | 多机型、按个体身份区分能力 |
| 用户关联 | 每用户至多关联一架已部署 UAV，可不被服务或部分服务 | 多连接聚合、数据拆分、重复传输 |
| 接入资源 | 下行、连续 OFDMA 带宽抽象、频谱效率优化前给定 | 上行单独建模、带宽预留后空闲、功率优化 |
| 接入/回传隔离 | 预划分互不重叠频段，各自预算优化前给定 | 动态互借、跨层干扰计算、接入—回传联合调度 |
| 回传拓扑 | 单网关、每架 UAV 单跳直连、容量优化前算好 | UAV–UAV 中继、多跳路由、流量守恒、回传带宽优化 |
| 能耗 | 固定集结点、固定巡航直达、简化任务能耗，只作硬约束 | 飞行路径/速度/悬停时长优化、完整旋翼飞行动力学、能耗进目标 |

网格间距不小于运营安全水平间距（`yaml: frozen_reference_parameters.operational_horizontal_separation_m`），因此保留候选点已满足最小分离要求，模型不再增加候选点两两冲突约束。**问题规模优先通过区域大小、用户数量和候选网格范围改变，不通过把网格间距缩小到运营安全距离以下制造规模。**

---

## 3. 场景、坐标与确定性预处理

- 优化与数据文件内部统一使用以米为单位的本地二维平面坐标；经纬度必须先投影，不得直接代入欧氏距离公式。
- 场景输入：服务区域多边形、规则网格间距、固定 UAV 高度、禁飞或不可部署多边形及其安全缓冲距离。
- 网关从预定义锚点（边中点、角点类型）中选取，保存锚点编号、坐标、高度和随机种子；UAV 集结点默认与该网关共址（`yaml: derived_parameters.staging_site_position_m`）。
- **建模前的确定性过滤，按此顺序执行**：
  1. 禁飞区或安全缓冲区内的候选点；
  2. 固定任务能耗超过任务可用能量的候选点（\(E_l^{\mathrm{fixed}}>E^{\mathrm{use}}\)）；
  3. 没有可用单跳回传链路的候选点（\(A_l^{\mathrm{bh}}=0\)）；
  4. 未达到固定接入 SINR 门槛的用户—候选位置边。
- **所有过滤规则、阈值、被删除对象及原因必须写入预处理日志，每个删除对象只有一个主原因码。** 上述过滤是公开、固定且与学习输出无关的模型定义，不属于 GNN 候选筛选。
- 预处理后允许并记录没有任何可用接入边的用户，不为其任意补回最近边；只有一个候选位置都未保留时才拒绝并重新生成整个场景。Pilot 必须报告零度用户比例。
- 数据接口冻结为四类逻辑表：**场景表**（区域、网关、集结点、UAV 与任务参数）、**用户表**（坐标、类别、需求、最低标准）、**候选点表**（坐标、高度、固定能耗、回传容量）、**接入链路表**（用户—位置编号、链路增益、SINR、频谱效率、可用标志）。

场景生成的全部数值规则见 `yaml: reference_scenario_generator`。

---

## 4. 关键用户与服务目标

- **关键用户**定义为现场应急任务人员携带的任务关键通信终端（消防、搜救、现场医护、应急指挥）。**普通用户**是灾区内受影响公众的终端。
- 用户类别在场景生成时依据终端角色给定，是确定性实例输入；**GNN 不识别、预测或修改用户类别**。
- 只设一个关键用户等级，同类内部等权，统一最低下行服务速率 \(q_{\mathrm{crit}}\)（`yaml: frozen_reference_parameters.common_critical_minimum_downlink_rate_bps`）。该数值是本研究的任务级平均服务门槛，**不是法规或 3GPP 强制 SLA**。
- 关键用户位置分布与普通用户相同，避免把"关键身份"与某一空间模式变成学习捷径。
- 服务项按权重排序：① 最大化达标关键用户数；② 最小化关键用户相对缺口总和；③ 最大化全体用户总有效服务量（超过需求的部分不增值）；④ 小权重的 UAV 部署数量惩罚。
- 能耗只作硬预算约束，**不进入目标函数**。
- 资源不足时未能让全部关键用户达标**不会使模型不可行**；模型选择能让最多关键用户达标的方案。
- **术语纪律**：本模型只能称为"归一化的优先级加权单目标"或"归一化加权复合单目标"。**不得**称为 `lexicographic optimization`、`hierarchical optimization` 或 `strict-priority optimization`，**不得**声称关键用户在所有情况下都绝对优先服务——因为这是加权混合目标，即使物理资源足够也不能把"所有关键用户必然先达标"写成数学保证。

---

## 5. MILP 规范

符号定义见 `notation.md`，单位与缩放见 `units.md`，数值见 `yaml: frozen_reference_parameters`。

### 5.1 集合与变量

集合 \(\mathcal U\)（全部用户）、\(\mathcal C\subseteq\mathcal U\)（关键用户，每实例 \(|\mathcal C|\ge1\)）、\(\mathcal L^0\)（预处理前候选位置）、\(\mathcal L\subseteq\mathcal L^0\)（保留候选位置）、\(\mathcal E^{\mathrm{acc}}\)（保留接入边）。

决策变量：\(y_l\in\{0,1\}\)（部署）、\(x_{ul}\in\{0,1\}\)（关联）、\(b_{ul}\ge0\)（等效平均使用带宽）、\(z_u\in\{0,1\}\)（关键用户达标计数）、\(\delta_u\in[0,q_u]\)（关键用户缺口）。

**\(z_u\) 与 \(\delta_u\) 的语义依赖最优目标方向**：现有单向连接约束与目标权重保证它们在**最优解**中正确取值，但不得把它们描述为任意可行解中的严格双向指示变量。

### 5.2 派生量与约束

派生服务率：\(S_u=\sum_{l:(u,l)\in\mathcal E^{\mathrm{acc}}}\eta_{ul}b_{ul}\)，单位 bit/s。速率 \(r_{ul}:=\eta_{ul}b_{ul}\) 是派生量，不是独立变量。

| 约束 | 表达式 | 范围 |
|---|---|---|
| UAV 数量 | \(\sum_{l\in\mathcal L}y_l\le K\) | 全局 |
| 单关联 | \(\sum_{l:(u,l)\in\mathcal E^{\mathrm{acc}}}x_{ul}\le1\) | 每个 \(u\) |
| 部署连接 | \(x_{ul}\le y_l\) | 每条边 |
| 带宽连接（强化） | \(b_{\min}x_{ul}\le b_{ul}\le M_{ul}x_{ul}\) | 每条边 |
| UAV 接入带宽 | \(\sum_{u:(u,l)\in\mathcal E^{\mathrm{acc}}}b_{ul}\le By_l\) | 每个 \(l\) |
| 需求封顶 | \(0\le S_u\le d_u\) | 每个 \(u\) |
| 关键用户达标连接 | \(S_u\ge q_uz_u\) | 每个 \(u\in\mathcal C\) |
| 关键用户缺口 | \(\delta_u\ge q_u-S_u,\ 0\le\delta_u\le q_u\) | 每个 \(u\in\mathcal C\) |
| 位置回传 | \(\sum_{u:(u,l)\in\mathcal E^{\mathrm{acc}}}\eta_{ul}b_{ul}\le C_l^{\mathrm{bh}}y_l\) | 每个 \(l\) |
| 网关共享容量 | \(\sum_{u\in\mathcal U}S_u\le C_G\) | 全局 |
| 位置能量 | \(E_l^{\mathrm{fixed}}y_l+T\frac{p_A}{\xi_{\mathrm{PA}}}\sum_{u:(u,l)\in\mathcal E^{\mathrm{acc}}}b_{ul}\le E^{\mathrm{use}}y_l\) | 每个 \(l\) |
| 有效不等式（强化） | \(z_u\le\sum_{l:(u,l)\in\mathcal E^{\mathrm{acc}}}x_{ul}\) | 每个 \(u\in\mathcal C\) |

达标连接约束**只定义 \(z_u\) 何时可以取 1**，不要求所有关键用户的 \(z_u\) 必须为 1。

### 5.3 归一化加权目标

\[
H_C=\frac{1}{|\mathcal C|}\sum_{u\in\mathcal C}z_u,\quad
Q_C=\frac{1}{|\mathcal C|}\sum_{u\in\mathcal C}\frac{\delta_u}{q_u},\quad
R_{\mathrm{all}}=\frac{\sum_{u\in\mathcal U}S_u}{\sum_{u\in\mathcal U}d_u},\quad
D_{\mathrm{frac}}=\frac{\sum_{l\in\mathcal L}y_l}{K}
\]

\[
\max\ F=\alpha_HH_C-\alpha_QQ_C+\alpha_RR_{\mathrm{all}}-\alpha_DD_{\mathrm{frac}}
\]

四个权重为正、和为 1、满足 \(\alpha_H>\alpha_Q>\alpha_R>\alpha_D>0\)（`yaml: frozen_reference_parameters.objective_weights`）。**训练、ID 测试和 OOD 测试使用同一组权重，禁止在测试集上重新调权。**

所有分母都是实例生成后已知的常数，且没有两个决策变量相乘，因此模型是 **MILP 而不是 MIQP**。

### 5.4 LP 松弛强化

两处强化都由原模型已有约束推出，**不删除任何原整数可行解**（相同整数壳），只收紧 LP 松弛：

**逐位置能量带宽上界与逐边紧上界**（统一命名为 \(M_l^E\) 与 \(M_{ul}\)，见 `notation.md`）：

\[
M_l^E=\max\left\{0,\frac{E^{\mathrm{use}}-E_l^{\mathrm{fixed}}}{T(p_A/\xi_{\mathrm{PA}})}\right\},\qquad
M_{ul}=\min\left\{B,\frac{d_u}{\eta_{ul}},\frac{C_l^{\mathrm{bh}}}{\eta_{ul}},\frac{C_G}{\eta_{ul}},M_l^E\right\}
\]

**有效不等式** \(z_u\le\sum_lx_{ul}\)：因 \(q_u>0\) 且已有 \(q_uz_u\le S_u\)、单关联、带宽连接和服务率定义，它不改变整数可行域，但显式连接达标变量与关联变量并强化松弛。

实现规则：

- 单侧安全容差——**只有 \(M_{ul}<b_{\min}-1\ \mathrm{Hz}\) 时才删除该边或固定 \(x_{ul}=b_{ul}=0\)**，原因码 `edge_upper_bound_below_b_min`；相等或差值不超过 1 Hz 时一律保留。这个 1 Hz 只防止浮点误删，不把不可行边变成可行边。删边判断统一在 SI 的 Hz 层执行。
- **不得故意保留松的 \(B\) 型 Big-M 来制造 learned branching 优势。** 松上界只允许出现在极小实例的等价性测试里。
- 强化必须在 default、pseudo-cost、GNN 主方法、部署掩码消融和教师参考的**全部方法**中保持一致。
- 若实现测试发现整数最优值变化，视为 **P0 错误**。

### 5.5 内部数值缩放

输入与归档保存 SI；优化模型内部统一使用 MHz / Mbit/s / kJ。转换只能通过集中的 `model_scaling` 层完成，不得在约束构造代码中临时猜测单位。完整规则、缩放后的能耗系数 \(\kappa_E\) 与边界转换五条见 `units.md`。

**必须对同一小实例同时计算 SI 版与缩放版的目标、约束 slack 和最优解，确认在容差内一致后才能进入 Pilot-A。**

### 5.6 能量约束的表述边界

在当前冻结参数下（推导与自检数值见 `units.md`），满带宽运行时能量约束开始可能绑定的单程水平距离，**严格大于**全部主 ID/OOD 候选点到集结点的最大距离。因此：

- 该约束在全部主 ID/OOD 候选位置上是**静态冗余约束**；
- **能量过滤不得被声称删除了主数据候选点**，除非将来日志确实证明发生删除；
- 主论文只能把它称为"任务安全可行性约束"或"安全预算检查"，**不得把主结果包装成由能量冲突驱动的部署优化**；
- 仍保留该约束与逐位置 slack 日志，以验证实现、维护安全语义、为后续版本留接口；
- 要让能量成为活跃研究因素，必须建立新版本、引用现实任务时长/电池/保留比例/平台功耗依据、预先定义合理取值范围并重新生成受影响数据。**不得仅为增加 SCIP 难度而缩小电池或拉长任务时间。**
- A0 必须用实际生成的候选点重算最大飞行距离与逐位置能量 slack 并记录，不得直接引用文档中的估算值。

---

## 6. 无线与能量预计算

全部公式的符号见 `notation.md`，单位与 dB/线性换算规则见 `units.md`，参数数值见 `yaml: frozen_reference_parameters` 与 `yaml: fixed_physical_constants_and_conventions`。

### 6.1 接入链路

主传播模型采用 **Al-Hourani 概率 LoS/NLoS 平均大尺度路径损耗**，主场景环境类别为 urban；suburban 与 dense urban 只作传播敏感性设置。**不为每条链路随机抽取 LoS 状态、快衰落或阴影衰落样本**，而使用确定的平均路径损耗和固定可靠性裕量。

计算顺序（几何 → 平均路径损耗 → 线性增益 → 噪声与干扰 → SINR → 截顶有效频谱效率）：

\[
\rho_{ul}=\sqrt{(X_l-X_u)^2+(Y_l-Y_u)^2},\quad
d_{ul}=\sqrt{\rho_{ul}^2+(h_D-h_u)^2},\quad
\theta_{ul}=\tfrac{180}{\pi}\operatorname{atan2}(h_D-h_u,\rho_{ul})
\]

\[
P_{ul}^{\mathrm{LoS}}=\frac{1}{1+a_e\exp(-b_e(\theta_{ul}-a_e))}
\]

\[
L_{ul}^{A}=20\log_{10}\frac{4\pi f_Ad_{ul}}{c}+P_{ul}^{\mathrm{LoS}}\eta_{\mathrm{LoS}}^{A}+(1-P_{ul}^{\mathrm{LoS}})\eta_{\mathrm{NLoS}}^{A}+M_F^{A}
\]

\[
g_{ul}^{A}=10^{(G_t^{A}+G_r^{A}-L_{\mathrm{dev}}^{A}-L_{ul}^{A})/10},\quad
N_0^{A}=k_BT_0F_A,\quad
I_0^{A}=N_0^{A}(10^{M_I^{A}/10}-1)
\]

\[
\gamma_{ul}=\frac{p_Ag_{ul}^{A}}{N_0^{A}+I_0^{A}},\qquad
\eta_{ul}=\zeta_A\min\left(\eta_{\max}^{A},\log_2\left(1+\frac{\gamma_{ul}}{\Gamma_A}\right)\right)
\]

当 \(\gamma_{ul}<\gamma_{\min}^{A}\) 时不生成接入边。

**三条易错点必须写进实现与论文**：

1. 仰角必须用**度**，这是 Al-Hourani 原始参数的约定；
2. \(p_A\) 是**天线端口传导 PSD，不是 EIRP PSD**，所以链路增益公式仍单独加入 \(G_t^{A}\)；不得把它当 EIRP 后再次加天线增益；
3. 因为信号、噪声和干扰总功率均随带宽同比例增长，**\(\gamma_{ul}\) 不依赖优化中的 \(b_{ul}\)**——这正是模型保持线性的原因。

固定保守干扰只用噪声抬升参数 \(M_I^{A}\) 表示，代表可复现的保守干扰情景，**不声称等于实际部署组合产生的瞬时互扰**。第一版不优化功率、不根据部署组合动态重算干扰、不混用 Al-Hourani 与 3GPP 参数；3GPP 空中终端模型只可作单独且明确标注的外部敏感性检查。

### 6.2 回传链路与网关

复用同一计算流程，Al-Hourani 环境参数 \(a_e,b_e\) 与 LoS/NLoS 额外损耗与接入共用，但频率、PSD、天线增益、设备损耗、可靠性裕量、噪声因子、实现差距和频谱效率上限使用独立参数。

\[
B_{\mathrm{eq}}^{\mathrm{bh}}=\frac{B_{\mathrm{total}}^{\mathrm{bh}}}{K},\qquad
C_l^{\mathrm{bh}}=A_l^{\mathrm{bh}}B_{\mathrm{eq}}^{\mathrm{bh}}\eta_l^{\mathrm{bh}},\qquad
C_G=\operatorname{clip}\left(\beta_G\sum_{u\in\mathcal U}d_u,C_G^{\min},C_G^{\max}\right)
\]

未部署 UAV 对应的回传带宽份额**不在优化中动态重新分配**。网关共享总容量 \(C_G\) 独立表示网关处理、卫星终端或核心网瓶颈，**不设为所有位置回传容量之和**。

因此研究问题中的"回传资源分配"在第一版具体解释为**回传容量约束下的业务流量分配**，而不是物理回传带宽分配。

在当前参考数值下 ID 场景可能没有候选点因回传 SINR 门槛被删除；**这不构成错误**，因为位置相关的单链路回传容量仍然保留。论文只有在日志实际观察到删除时才能声称该门槛过滤了候选位置。

### 6.3 能量

\[
d_l^{\mathrm{fly}}=\|\mathbf p_l-\mathbf p_s\|_2,\qquad
E_l^{\mathrm{fixed}}=E_{\mathrm{TOL}}+2\frac{P_{\mathrm{cr}}}{v_{\mathrm{cr}}}d_l^{\mathrm{fly}}+T(P_{\mathrm{hov}}+P_{\mathrm{base}}),\qquad
E^{\mathrm{use}}=(1-\rho_{\mathrm{res}})E_{\mathrm{bat}}
\]

\(T\) 只表示到达候选位置后的**驻站悬停服务时间**，不包含往返巡航时间，因此固定能耗公式不会重复计算飞行时间。安全余量只通过 \(\rho_{\mathrm{res}}\) 计算，**不再重复加入 \(E_l^{\mathrm{fixed}}\)**。固定回传设备与机载计算能耗吸收到 \(P_{\mathrm{base}}\)，回传业务量不另外改变能耗。

参考平台是"中型企业多旋翼数量级抽象"，**不声称精确复刻某一具体商品**；参数来源见 `yaml: parameter_sources`。

### 6.4 频谱与合规声明

标准化研究配置**不表示可以在实际灾区未经授权使用相应频谱**。带宽敏感性保持 PSD 不变，因此它是"固定 PSD 下的带宽—总功率包络"敏感性，**不能描述成总发射功率不变的纯带宽比较**。UAV 高度是通信研究输入，**不代表实际任务天然获得飞行许可**。

---

## 7. GNN 接口契约

### 7.1 候选范围（唯一定义）

- GNN 只在 SCIP 的 **LP branching callback** 中运行。
- 调用 `getLPBranchCands()` 后，设返回候选序列为 `lpcands`、优先候选数为 `npriolpcands`，则**唯一合法学习候选集合是 `lpcands[0:npriolpcands]`**（记为 \(\mathcal B_n\)）。
- `nlpcands`、`npriolpcands`、`nfracimplvars` 三者均须记录。后续非优先候选与 fractional implicit integer variables **不得**由 GNN 直接选择。
- 不存在优先 LP 候选时返回 `DIDNOTRUN`，交给 SCIP 既定默认分支链。
- 候选可包含 \(y_l\)、\(x_{ul}\)、\(z_u\) 及模型中其他实际存在的整数变量；连续变量 \(b_{ul}\)、\(\delta_u\) 不是分支候选。
- GNN 用候选掩码只输出分数和排序，**不预测最终变量取值，也不决定分支方向**。SCIP 建立分支子节点并继续负责可行性、界、剪枝和终止判断。
- **消融**：只对部署变量评分的版本不是主方法，只作候选范围影响分析。它**复用同一个已选中的 checkpoint**，仅把候选掩码进一步限制为部署变量，不单独重训；若当前无合法部署变量候选，该节点使用 SCIP 默认分支。因此它只能解释为"同一模型的部署候选掩码消融"，不能解释为独立训练 deployment-only GNN 的能力。

### 7.2 动态图映射契约

- 原始建模变量、transformed variables 和当前 LP columns **不要求也通常不会一一对应**。presolve 可能固定、聚合或删除变量，cuts 也会改变当前 LP 行集合。
- **每次回调必须**从当前 transformed problem/LP 重新取得变量、列、行和非零系数，重建映射
  `current transformed Variable <-> current LP Column <-> graph variable node`。
- 映射只能使用本次 SCIP 对象身份、transformed 名称/稳定运行内编号和当前列位置，**不得依赖原始创建顺序、变量名或跨节点缓存的列下标**。
- 回调内断言：每个 `lpcands[0:npriolpcands]` 恰好映射到一个当前图变量节点；GNN 返回值恰好覆盖该候选掩码；最终选择的变量仍属于同一候选集合。
- 任一断言失败：记录原始/transformed 标识、节点和原因 → 当前节点回退默认分支 → 触发该实例 circuit breaker。
- 必须覆盖的单元测试见 `pilot_protocol_v0.2.md` §5.1。

### 7.3 专家标签

- 监督专家为 strong branching 全候选评分，用于**离线训练与验证标签生成**。具体实现（native 还是 project-defined oracle）由 Pilot-A 的接口 spike 决定，见 §7.4。
- 专家仅评估当前 LP 松弛中分数化的合法整数候选，尽可能为全部候选保存原生综合分数；**不把未分数化的整数变量额外加入 \(\mathcal B_n\)**。
- 采样：每个可分支训练/验证实例根节点（深度 0）强制查询一次；深度 1–8 的节点以固定概率抽样；每实例最大标签数与单实例标签时限见 `yaml: confirmed_approach.supervision.sampling`。未抽样节点用廉价 pseudo-cost 分支继续探索。
- **正式测试与 OOD 不生成专家标签。** Pilot 允许少量诊断调用，但这些标签全部丢弃。
- **训练和验证场景必须先按基础场景分开，再生成节点标签**；来自同一基础灾害场景的节点不得跨数据分区。
- 每个有效标签至少保存：场景与实例编号、随机种子、节点编号与深度、当前 transformed LP 的变量—约束二部图、完整合法候选集合、稳定变量映射、变量类型、LP 松弛值、全部可得专家分数、专家最佳候选集合、标签生成耗时、以及**已解析的教师实现标识**。
- 丢弃条件：strong branching 未完整评分、标签含非有限数值、候选映射失败、数据生成被资源限制中断。丢弃必须记录原因。

### 7.4 教师实现的条件化命名

优先目标是包装并验证 **SCIP native vanilla full strong** 的全候选分数接口，离线标签查询固定
`collectscores=true, scoreall=true, integralcands=false, idempotent=true, donotbranch=true`。

若在 PySCIPOpt 冻结版本下无法稳定满足 `pilot_protocol_v0.2.md` §5.2 的全部验收条件，则：

- **禁止**把替代实现继续称为 "SCIP native vanilla full strong"；
- 允许建立并冻结逐候选调用的 **`project-defined Python-side all-candidate strong-branching oracle`**，明确定义迭代限制、分数合成、无效分支、上下界和并列处理；
- 论文、图表、配置和代码中**统一使用该名称**；
- 在 `decisions.md` 新增版本化决定；
- **两种 oracle 不得在同一正式标签集中混用。**

若两种路径均不能稳定工作，Pilot-A 失败，不生成正式标签并建立新版本。

### 7.5 训练与 checkpoint

- 第一版采用候选掩码下的**分类交叉熵行为克隆**。并列最佳集合
  \(\mathcal Y_n=\{i\in\mathcal B_n:|s_{ni}-s_{n,\max}|\le\tau_{\mathrm{tie}}\max(1,|s_{n,\max}|)\}\)，
  目标在 \(\mathcal Y_n\) 内均匀分配。该规则避免随机丢弃并列专家选择，也不依赖未明确暴露的求解器内部容差。
- 完整专家分数用于验证集 top-k 准确率和排名误差；**不把分数回归或 learning-to-rank 作为第一版主训练任务，也不把验证诊断冒充测试性能**。
- 第一版**不使用** DAgger、强化学习或求解过程中的在线再训练。
- 三个训练种子均按冻结超参数训练，并在同一固定 validation solve-diagnostic 子集上**实际运行求解**，报告 loss、accuracy、regret、节点、LP 迭代、墙钟、尾部减速和推理占比。
- **唯一 checkpoint 按最低 validation masked cross-entropy 选择，并列时取较小 seed。** 三个 seed 的求解诊断用于揭示稳定性，**不得用 test/OOD 结果改选**。若未来改为按求解时间选择，必须另建版本。
- checkpoint 选择完成后写入 manifest（training_seed、checkpoint_hash、feature_schema_hash、normalizer_hash、training_data_hash）；**Pilot-B 与正式评测必须加载同一 manifest checkpoint**，不得用 seed 0 代替实际入选 seed，Pilot-B 后不得重选。

超参数与预算数值见 `yaml: confirmed_approach.supervision.training`。

### 7.6 在线调用、回退与审计

- 主方法为**有预算的搜索树前部调用**：仅当当前节点存在合法 LP 分支候选，且节点深度与该实例累计调用次数均未超预算时才调用 GNN。
- 任一预算耗尽后，该实例剩余搜索全部交回固定版本与固定参数的 SCIP 默认分支。
- **确定性回退条件**：无合法候选、LP 状态不适用、模型或特征加载失败、候选映射或维度不一致、推理异常、输出含 NaN 或无穷、输出变量不在当前候选集合、设备或内存异常。
- 模型异常、接口版本不兼容或一次同步调用返回后发现超过软延迟阈值 → 触发**实例级 circuit breaker**：完成当前分支后本实例不再调用 GNN。
- **软阈值不是异步强制取消机制**：该次调用完成且输出有效时仍用于当前分支，随后关闭本实例剩余调用；累计预算也在每次调用返回后检查，因此最多允许超出一个已完成调用的耗时。
- 第一版**不使用 softmax 最大值作为"低置信度回退"阈值**，因为未经校准的 softmax 输出不是可靠置信概率。
- **日志分级**：训练/验证标签与预声明审计子集使用完整候选级日志；正式性能计时只记录低开销摘要（不逐候选写入编号、LP 值或全部分数）。完整审计子集为 ID 测试中场景种子最小的 10 个中型和 10 个大型实例，只对入选 checkpoint 单独重跑，**这 20 次审计运行不计入正式性能时间表**。
- 每次完整求解至少记录：数据/模型/代码/SCIP/参数文件版本或哈希、硬件/线程/随机种子、终止状态、目标值、incumbent、best bound、gap、墙钟、节点数、LP 迭代数、GNN 调用次数、累计开销、推理延迟分布、回退原因分布。

字段清单见 `yaml: confirmed_approach.audit_logging`，预算数值见 `yaml: confirmed_approach.online_branching`。

---

## 8. 数据划分与实验协议

### 8.1 划分

- **所有来自同一基础灾害场景的实例变体和分支节点必须进入同一个数据分区**，禁止按节点随机拆分造成场景泄漏。
- ID 数据按 70%/15%/15% 固定划分为训练/验证/测试；各分区的小/中/大场景数、pilot 与 OOD 场景数见 `yaml: evaluation_protocol.dataset_split` 与 `yaml: evaluation_protocol.ood_sets`。
- 三类可解释 OOD：`OOD-size`（超出训练范围的用户数或候选点数）、`OOD-structure`（未见的用户聚集强度或灾区几何）、`OOD-backhaul`（未见网关锚点或更紧的回传瓶颈）。**各子集一次只改变一个主要因素**，不同 OOD 因素不在主诊断集合中全部混合。
- pilot 场景**不进入**最终训练、验证或测试集合；任何必要修改必须建立新版本记录。
- pilot 应包含根节点即可求解、容易、中等和困难实例；**最终测试保留根节点即可求解的实例并如实报告 GNN 未被调用**，不能只筛选对 GNN 有利的实例。
- 最终场景生成器、参数范围和数据划分在测试前锁定；**测试集不得用于选择目标权重、模型超参数、调用预算或回退阈值**。

### 8.2 求解器公平性

- SCIP 与 PySCIPOpt 版本、参数文件标识见 `yaml: frozen_reference_parameters`。
- 所有比较方法必须使用**相同**构建、数学模型、presolve、cuts、primal heuristics、单 CPU 线程、随机种子、时间限制、gap 容差、实例顺序和硬件环境，**只替换被比较的分支策略**。
- **必须先记录所用 SCIP 版本的实际默认分支配置**，避免把同一默认策略用不同名称重复列为两个基线。
- **四种必需比较方法**：未修改的 SCIP 默认分支、纯 pseudo-cost、全合法候选 GNN 主方法、只评分部署变量的 GNN 消融。
- vanilla full strong 只在成本可承受的小中型子集作为**慢专家参考**，不要求作为全部大实例的速度基线。
- `gap = 0` 表示求解器不会因达到正 gap 容差提前停止；限时实例只报告 incumbent、best bound 和最终 gap，另报告终止时是否已达 1% 相对 gap（不额外实现"首次达到 1% 的时刻"事件监听）。

### 8.3 计时

- **正式计时从求解调用开始**，外部单调时钟包住整个 `optimize()`，完整墙钟必须包含特征提取、CPU/GPU 数据传输、GNN 推理、后处理、回退和低开销审计记录；同时保存 SCIP 内部 solving time。离线标签生成和训练成本单独报告。
- 求解前允许一次**不计入正式求解时间**的模型加载和预热，但必须单独报告该成本。
- 正式计时任务**不并发**；数据生成、标签生成和不进入正式计时表的批处理允许跨实例并行，但每个单独求解始终固定单线程。
- 四方法在场景和重复间使用**预先生成、保存到清单的平衡 Latin-square 顺序**；禁止总是先跑 default 或总是最后跑 GNN。
- 先做一次固定顺序之外的计时预跑；default 外部墙钟 ≤10 s 的场景，四种方法正式计时均独立运行 3 次取场景—方法中位数，其余场景各运行 1 次。**三次不能只重复表现较差或较好的方法**；节点、LP 迭代和解状态仍应确定性一致。
- Pilot-B 必须验证 SCIP 的时间限制在 callback 存在时的实际语义，并报告同步调用造成的任何时限越界；若不能保证，必须以外部硬限制和一致终止规则修订协议。

### 8.4 指标与统计

**主 gap 与 nPDI**（定义式见 `notation.md`）：

- 冻结参考权重的逐分量安全解析范围为 \([-0.21,0.79]\)，跨度恰为 \(\Delta_F=1.0\)；不声称端点必然可达。
- 计时起点向所有方法提交并验证**同一确定性平凡可行解** \(y=x=b=z=0,\ \delta_u=q_u\)，使 incumbent 从起点有定义。
- 有效 dual 在 SCIP 首次给出有限上界前取解析上界 \(\alpha_H+\alpha_R\)，之后取 \(\min(\alpha_H+\alpha_R,\ \text{SCIP dual})\)。权重敏感性使用对应 profile 的 \(\alpha_H+\alpha_R\)，**禁止把参考值 0.79 硬套给其他 profile**（因所有 profile 正权重和仍为 1，固定跨度仍是 1.0）。
- 若仍无 incumbent，该次运行标记为**无效**而不是静默填零。
- **SCIP 原生相对 gap 只保留为诊断字段**；目标跨越 0，不得用相对 gap 作为 PDI 的主定义。
- nPDI 的积分按 incumbent 或有效 dual 更新事件构造的**分段常数轨迹**计算，不作结果驱动的截断或平滑。

**主要求解指标**：达到目标 gap 的实例比例、墙钟时间、节点数、LP 迭代数、限时实例的 incumbent/best bound/最终 gap、normalized PDI、相对默认 SCIP 的配对加速比、胜/平/负、P90/P95 尾部减速、超时变化、GNN 调用数、推理总时间占比、回退原因。

**声明顺序**：① 主指标 nPDI（全部实例场景级配对）→ ② 确认性指标（证明最优比例、最终 normalized gap）→ ③ 效率指标（共同证明最优实例上的配对时间；全部实例的节点和 LP 迭代）→ ④ 安全指标（P90/P95 减速、超时变化、调用与回退分布）→ ⑤ 模仿指标（只作诊断）。

**推断统计**：

- **配对单位和 bootstrap 单位均为基础场景，不是分支节点。**
- ID 按 small/medium/large 分层——先在层内重采样，再按冻结比例合并；OOD 家族分别报告。
- paired bootstrap 固定重采样次数与统计种子（`yaml: evaluation_protocol.statistical_protocol`），报告 95% 区间。
- P90/P95 在完整的 120 个 ID 测试实例和每个完整 60 实例 OOD 家族上报告；**30 实例 OOD 子组只报告 P90、最大值和逐实例散点**，不单独作稳定的 P95 结论。
- 超时实例保留其 300 s 的 incumbent、dual bound、normalized gap 和 nPDI；**不得只在双方求优的实例上计算时间**。300 秒超时不能假装成精确的 300 秒求解时间。
- **根节点解决、GNN 从未调用、零 eligible 节点和 GNN 净减速的实例全部进入主结果。**
- `GNN-eligible` 子集只作机制诊断，必须与全体主结果并列标明，**不能替代全体结果或作为主要性能声明**。
- win/tie/loss 的时间 tie 容差固定为相对默认时间的 1%；短任务用三次中位数后再判定，**不得在正式结果后改值**。
- 模仿准确率与 regret 只作学习诊断，**不能代替完整求解性能**。

### 8.5 预声明敏感性

pilot 承载预先声明的轻量 exact-solver-only 敏感性（权重 profile、传播环境、带宽、能量等，见 `yaml: predeclared_one_factor_sensitivity`）：只运行原生 SCIP 默认分支，不生成专家标签、不训练或调用 GNN。**该检查不能改变正式参考权重或任何冻结参数。**

---

## 9. 泄漏防护与可重建性（硬规则）

- 在任何标准化、标签或缓存生成前**先按基础场景划分**；所有特征归一化统计只在 training 场景上拟合，validation/test/OOD 仅应用冻结统计。
- 场景 JSON/YAML 的**规范序列化**内容生成 SHA-256；**不同分区出现相同场景哈希时立即中止**。近重复诊断另外比较用户、候选、网关和禁飞几何哈希并写入报告。
- 原始实例、transformed graph、标签和张量缓存按 `dataset_version/split/scenario_hash/solver_hash` 命名空间隔离；**禁止 validation/test/OOD 命中 training 标签缓存，禁止旧版本缓存被静默复用**。
- 场景生成 seed、标签节点抽样 seed、SCIP seed、训练 seed、方法顺序 seed 和 bootstrap seed **分开配置、分开记录**；不得从实例编号隐式复用同一个随机流。
- test/OOD 在模型、checkpoint、归一化、调用预算、统计脚本和方法顺序清单**全部哈希冻结前不可运行**。任何意外提前访问记录为 protocol violation，并重新建立未访问的测试版本。
- 每次正式实验保存代码、数据生成器、模型 checkpoint、SCIP、参数文件、硬件和随机种子的版本或哈希；所有物理参数记录数值、单位、来源、换算和敏感性范围（`yaml: parameter_provenance_required`）。

---

## 10. 执行顺序与解锁关系

```
实现（生成器 + 强化缩放 MILP + 默认 SCIP + A0 前置门）
  → Pilot-A 七道 stop/go 门 → GO / REVISE / STOP
  → 【仅 GO 解锁】正式场景与标签生成 + 三 seed 训练
  → checkpoint 选择 + manifest 冻结
  → Pilot-B（实际入选 checkpoint）
  → 【仅 Pilot-B 通过且哈希全部对齐解锁】ID test + OOD
```

- **Pilot-A `GO` 单独不解锁正式 test/OOD。**
- 任一必需门失败：建立新版本决策记录后才能重新校准，**不得静默调参或按难度筛选实例**。
- 允许与禁止的修改清单见 `pilot_protocol_v0.2.md` §9。
- **若真实场景在诚实强化后的模型上仍被 SCIP 快速解决，应把"该规模无需 learned branching"作为有效负结果**，并通过新版本重新定义研究问题；不得人为削弱求解器。

**当前状态**：规范已冻结到"可以开始实现 baseline 与 Pilot-A"，尚未授权正式标签生成、GNN 训练、正式测试或 OOD。下一里程碑依次为：缩放 MILP 与单元测试 → SCIP baseline → 候选映射 spike → 专家接口 spike → Pilot-A 报告 → 七个 stop/go 门审计。

---

## 11. 预算口径

`300 实例 × 4 方法 × 300 s = 100 CPU h` **只是正式四方法全部跑满的上界，不是项目总成本**。可量化组件与合计见 `yaml: evaluation_protocol.full_project_compute_budget`。加 20% contingency 后为当前执行规划包络。

该数**既不是最低消耗也不是总上限**，因为 headroom/shadow、Pilot-B 的 300 s 子集、短任务重复、失败重跑、接口开发、数据生成和分析尚未完全定界。

**最终论文必须分别报告**：正式求解 CPU h、pilot 与敏感性 CPU h、专家标签 CPU h、训练 CPU/GPU h、full-strong 与审计 CPU h、失败重跑与开发性运行。预算不足只能减少预先声明的非主分析或建立新版本，**不能静默缩短某个方法的正式时限**。

---

## 附录 A：v0.1 → v0.2 修订对照（论文可引用）

以下 8 条是实现前静态审计推翻的原始设计。上方正文已是修订后的版本，此表仅供论文说明设计演化与审计价值。

| 原始 v0.1 条款 | 现行条款 | 修订性质 |
|---|---|---|
| "全部合法整数分支候选" | 仅 `lpcands[0:npriolpcands]` | 收紧并消除 SCIP API 歧义 |
| 原始变量与图的"稳定映射" | 每次回调基于 transformed problem 与当前 LP columns 重建 | 取代一一对应假设 |
| 专家固定称为 SCIP native vanilla full strong | 先 native spike，失败则改名为 project-defined oracle | 条件化取代 |
| \(b_{ul}\le Bx_{ul}\) | \(b_{ul}\le M_{ul}x_{ul}\) + 冗余有效不等式 | 强化 LP 松弛，不改变整数可行域 |
| 能量参数"接近边界且有作用" | 主 ID/OOD 中静态冗余，只称安全可行性约束 | **纠正已证伪的解释** |
| 单一 pilot sanity check | 训练前 Pilot-A + 训练后 Pilot-B | 完整取代 |
| 1 秒和"绝大多数"等非数值难度门 | 四个机会/经济性门 + 三个标签/目标/接口门 | 完整取代 |
| 相对 gap 驱动 PDI | 固定跨度归一化绝对 gap 驱动 PDI | 完整取代主定义 |
| `100 CPU h` 作为项目成本 | 只是正式四方法最坏成本 | 纠正预算口径 |

---

## 附录 B：需要新建版本才能改动的事项

`yaml: active_protocol.changes_requiring_a_new_protocol_version` 与 `yaml: stage0_completion.requires_new_version_if_changed` 是机器可读清单。人可读摘要：

研究含义、关键用户身份、上下行范围、数学变量/约束/目标结构、确定性预处理规则、GNN 职责与精确性边界、用户或候选规模、需求或容量分布、能量或任务标定、pilot 门阈值、候选或教师语义、**任何冻结参考参数值**。
