# Stage 0 符号表

> **本文件只回答"符号是什么意思"。** 规范见 `scope.md`，理由见 `decisions.md`，数值见 `experiment_space.yaml`，单位与换算见 `units.md`，验收门见 `pilot_protocol_v0.2.md`。
>
> **本文件不写数值。** 需要数值时按 `yaml: 键路径` 查 `experiment_space.yaml`。
>
> **约定**：花体大写表示集合，普通大写或希腊字母表示已知参数或派生量，小写表示索引、坐标、参数或决策变量；上标 `A` 表示接入（access），上标 `bh` 表示回传（backhaul）。下标 `t`/`r` 表示发射端/接收端，`G` 表示固定网关，`D` 表示 drone，`s` 表示集结点，`PA` 表示功率放大器。

---

## 1. 集合与索引

| 符号 | 含义 |
|---|---|
| \(\mathcal U\) | 全部用户集合 |
| \(\mathcal C\subseteq\mathcal U\) | 关键用户集合；每实例满足 \(|\mathcal C|\ge1\) |
| \(\mathcal L^0\) | 确定性预处理前的原始 UAV 候选位置集合 |
| \(\mathcal L\subseteq\mathcal L^0\) | 预处理后保留的候选位置集合 |
| \(\mathcal E^{\mathrm{acc}}\subseteq\mathcal U\times\mathcal L\) | 达到接入物理可用门槛的用户—位置边集合 |
| \(\mathcal B_n\) | 节点 \(n\) 的 `getLPBranchCands()` 结果中前 `npriolpcands` 个 transformed LP 优先候选。**这是唯一允许评分的集合** |
| \(\mathcal Y_n\subseteq\mathcal B_n\) | 节点 \(n\) 的 strong-branching 并列最佳候选集合 |
| \(\mathcal V_n^{\mathrm{LP}}\) | 节点 \(n\) 当前 LP 的列变量集合；随 presolve、cuts、局部界和 LP 重建变化 |
| \(\mathcal R_n^{\mathrm{graph}}\) | 节点 \(n\) 二部图中对应当前 LP 列的变量侧行集合 |
| \(u,\ l,\ n,\ i\) | 用户、候选位置、树节点、当前节点候选的索引 |
| \(e\) | 传播环境类别索引（urban / suburban / dense urban） |
| \(k\) | `accuracy@k` 的排名截断位置。**小写 \(k\) 不表示最大 UAV 数量** |

---

## 2. MILP 已知参数

| 符号 | 单位 | 含义 |
|---|---:|---|
| \(K\) | 正整数 | 同质 UAV 最大可部署数量 |
| \(B\) | Hz | 每架已部署 UAV 的接入总带宽 |
| \(b_{\min}\) | Hz | 激活一条关联后必须分配的最小等效平均带宽 |
| \(d_u\) | bit/s | 用户 \(u\) 的有效需求上限；超过它的服务不增加目标收益 |
| \(q_u\) | bit/s | 关键用户 \(u\) 的最低达标速率，满足 \(0<q_u\le d_u\) |
| \(q_{\mathrm{crit}}\) | bit/s | 统一的关键用户达标速率；第一版所有关键用户 \(q_u=q_{\mathrm{crit}}\) |
| \(\eta_{ul}\) | bit/s/Hz | 接入边 \((u,l)\) 的预计算有效净荷频谱效率 |
| \(C_l^{\mathrm{bh}}\) | bit/s | 位置 \(l\) 的预计算固定回传容量 |
| \(C_G\) | bit/s | 所有已部署 UAV 共用的网关总容量 |
| \(E_l^{\mathrm{fixed}}\) | J | 前往位置 \(l\)、返回并驻站服务的固定任务能耗 |
| \(E^{\mathrm{use}}\) | J | 保留电量后允许用于本任务的能量 |
| \(T\) | s | 到达候选位置后的驻站悬停服务时间，**不含往返巡航时间** |
| \(p_A\) | W/Hz | 接入发射机**天线端口传导** RF 功率谱密度，**不是 EIRP PSD** |
| \(\xi_{\mathrm{PA}}\) | \((0,1]\) | 直流输入到天线端口 RF 输出的功放效率 |
| \(M_l^E\) | Hz | 位置 \(l\) 在能量余量下允许的接入总带宽上界 |
| \(M_{ul}\) | Hz | 边 \((u,l)\) 的紧带宽连接上界，取代统一的松上界 \(B\) |

> **易混符号**：\(d_u\) 是"需求"；\(d_{ul}\) 是接入三维距离；\(d_l^{\mathrm{fly}}\) 是飞行距离。三者不能互换。

---

## 3. MILP 决策变量

| 符号 | 定义域 | 含义 |
|---|---:|---|
| \(y_l\) | \(\{0,1\}\) | 是否在位置 \(l\) 部署 UAV |
| \(x_{ul}\) | \(\{0,1\}\) | 用户 \(u\) 是否关联位置 \(l\)；只对 \((u,l)\in\mathcal E^{\mathrm{acc}}\) 建立 |
| \(b_{ul}\) | \(\mathbb R_{\ge0}\)，Hz | 该关联在整个静态任务窗口的等效平均使用带宽 |
| \(z_u\) | \(\{0,1\}\) | 关键用户达标计数变量 |
| \(\delta_u\) | \([0,q_u]\)，bit/s | 关键用户最低速率缺口辅助变量 |

> \(z_u\) 与 \(\delta_u\) 的语义**依赖最优目标方向**：现有单向连接约束与目标权重使它们在最优解中取得预期值，**不把它们称为任意可行解中的严格双向指示量**。

---

## 4. LP 松弛强化量

\[
M_l^E=\max\left\{0,\ \frac{E^{\mathrm{use}}-E_l^{\mathrm{fixed}}}{T\,(p_A/\xi_{\mathrm{PA}})}\right\}
=\max\left\{0,\ \frac{(E^{\mathrm{use}}-E_l^{\mathrm{fixed}})\,\xi_{\mathrm{PA}}}{T\,p_A}\right\}
\]

\[
M_{ul}=\min\left\{B,\ \frac{d_u}{\eta_{ul}},\ \frac{C_l^{\mathrm{bh}}}{\eta_{ul}},\ \frac{C_G}{\eta_{ul}},\ M_l^E\right\}
\]

两种写法数值等价。只有满足 \(E_l^{\mathrm{fixed}}\le E^{\mathrm{use}}\) 的位置才进入 \(\mathcal L\)，因此实际上 \(M_l^E\ge0\) 恒成立；保留 \(\max\{0,\cdot\}\) 只为防止浮点边界产生负上界。

模型采用 \(b_{\min}x_{ul}\le b_{ul}\le M_{ul}x_{ul}\) 替代 \(b_{ul}\le Bx_{ul}\)，并加入有效不等式

\[
z_u\le\sum_{l:(u,l)\in\mathcal E^{\mathrm{acc}}}x_{ul},\qquad u\in\mathcal C.
\]

**二者都不删除原模型的任何整数可行解**（相同整数壳）；若实现测试发现整数最优值变化，视为 **P0 错误**。

> **命名统一**：能量带宽上界在全部文件中统一记为 \(M_l^E\)。早期草稿中的 `B_E_l` 是同一个量的旧名，已废弃。

---

## 5. 派生服务量与目标

| 符号 | 单位 | 含义 |
|---|---:|---|
| \(r_{ul}:=\eta_{ul}b_{ul}\) | bit/s | 接入边的平均服务速率；**派生量，不是独立决策变量** |
| \(S_u=\sum_{l:(u,l)\in\mathcal E^{\mathrm{acc}}}\eta_{ul}b_{ul}\) | bit/s | 用户 \(u\) 从其至多一个关联 UAV 获得的总平均服务速率 |
| \(H_C=|\mathcal C|^{-1}\sum_{u\in\mathcal C}z_u\) | \([0,1]\) | 关键用户达标比例 |
| \(Q_C=|\mathcal C|^{-1}\sum_{u\in\mathcal C}\delta_u/q_u\) | \([0,1]\) | 关键用户平均相对服务缺口 |
| \(R_{\mathrm{all}}=\left(\sum_{u}S_u\right)/\left(\sum_{u}d_u\right)\) | \([0,1]\) | 全体用户有效需求满足比例 |
| \(D_{\mathrm{frac}}=K^{-1}\sum_{l\in\mathcal L}y_l\) | \([0,1]\) | 可用 UAV 中实际部署的比例 |
| \(\alpha_H,\alpha_Q,\alpha_R,\alpha_D\) | 正数，和为 1 | 依次为达标、缺口、全体服务、部署惩罚的权重 |
| \(F\) | 无量纲 | 最终归一化加权目标值 |

\[
\max\ F=\alpha_HH_C-\alpha_QQ_C+\alpha_RR_{\mathrm{all}}-\alpha_DD_{\mathrm{frac}}
\]

所有分母都是实例生成后已知的常数，且没有两个决策变量相乘，因此模型是 **MILP 而不是 MIQP**。

---

## 6. 几何与接入链路预计算

| 符号 | 单位 | 含义 |
|---|---:|---|
| \((X_u,Y_u),(X_l,Y_l)\) | m | 用户与候选位置的横纵坐标。**大写坐标用于避免与 \(x_{ul}\)、\(y_l\) 冲突** |
| \(h_u,\ h_D\) | m | 用户终端高度、本实例固定 UAV 高度 |
| \(\rho_{ul},\ d_{ul}\) | m | 水平距离、三维接入链路距离 |
| \(\theta_{ul}\) | degree | 从用户指向 UAV 的仰角 |
| \(P_{ul}^{\mathrm{LoS}}\) | \([0,1]\) | 接入链路视距传播概率 |
| \(a_e,\ b_e\) | 经验量 | 环境 \(e\) 的 Al-Hourani LoS 概率参数。**其数值按以度为单位的仰角使用** |
| \(L_{ul}^{A}\) | dB | 接入平均路径损耗 |
| \(f_A,\ c\) | Hz, m/s | 接入中心频率、真空光速 |
| \(\eta_{\mathrm{LoS}}^{A},\eta_{\mathrm{NLoS}}^{A}\) | dB | LoS/NLoS 额外平均损耗。**它们不是频谱效率 \(\eta_{ul}\)** |
| \(M_F^{A}\) | dB | 接入固定可靠性或阴影衰落裕量 |
| \(G_t^{A},G_r^{A}\) | dBi | 接入发射与接收天线增益 |
| \(L_{\mathrm{dev}}^{A}\) | dB | 接入固定设备损耗 |
| \(g_{ul}^{A}\) | 无量纲 | 合并天线增益、设备损耗和路径损耗后转为线性的净链路增益 |
| \(NF_A,\ F_A=10^{NF_A/10}\) | dB, 无量纲 | 接入接收机噪声系数与线性噪声因子。**下标 A 区别于目标值 \(F\)** |
| \(k_B,\ T_0\) | J/K, K | 玻尔兹曼常数、参考绝对温度 |
| \(N_0^{A}=k_BT_0F_A\) | W/Hz | 含接收机噪声因子的接入噪声 PSD |
| \(M_I^{A}\) | dB | 干扰加噪声相对纯噪声的固定抬升量 |
| \(I_0^{A}=N_0^{A}(10^{M_I^{A}/10}-1)\) | W/Hz | 接入固定保守干扰 PSD |
| \(\gamma_{ul},\ \gamma_{\min}^{A}\) | 无量纲 | 接入线性 SINR 及生成接入边所需的最低值 |
| \(\zeta_A\in(0,1]\) | 无量纲 | 扣除导频、控制和保护间隔后的净荷比例 |
| \(\Gamma_A\ge1\) | 无量纲 | 相对理想 Shannon 容量的实现差距因子 |
| \(\eta_{\max}^{A},\ \eta_{\min}\) | bit/s/Hz | 接入原始频谱效率上限、用于 SINR 门槛工程近似的最低原始 MCS 频谱效率 |

运算符：\(\pi\) 圆周率，`sqrt` 平方根，`atan2` 保留象限的反正切，`exp` 自然指数，`log10`/`log2` 以 10/2 为底的对数。公式见 `scope.md` §6.1。

---

## 7. 回传链路与网关

| 符号 | 单位 | 含义 |
|---|---:|---|
| \(\mathbf p_G,\ h_G\) | m | 固定网关的二维坐标向量与高度 |
| \(\rho_l^{\mathrm{bh}},d_l^{\mathrm{bh}},\theta_l^{\mathrm{bh}}\) | m, m, degree | 位置 \(l\) 至网关的水平距离、三维距离、仰角 |
| \(P_l^{\mathrm{LoS,bh}}\) | \([0,1]\) | 回传链路 LoS 概率 |
| \(f_{\mathrm{bh}},\ p_{\mathrm{bh}}\) | Hz, W/Hz | 专用回传中心频率、天线端口传导 PSD |
| \(L_l^{\mathrm{bh}},\ g_l^{\mathrm{bh}}\) | dB, 无量纲 | 回传平均路径损耗与线性净链路增益 |
| \(G_t^{\mathrm{bh}},G_r^{\mathrm{bh}},L_{\mathrm{dev}}^{\mathrm{bh}},M_F^{\mathrm{bh}}\) | dBi, dB | 回传天线增益、设备损耗、可靠性裕量 |
| \(NF_{\mathrm{bh}},F_{\mathrm{bh}}\) | dB, 无量纲 | 回传噪声系数与线性噪声因子 |
| \(N_0^{\mathrm{bh}},I_0^{\mathrm{bh}},M_I^{\mathrm{bh}}\) | W/Hz, W/Hz, dB | 回传噪声 PSD、固定保守干扰 PSD、抬升量 |
| \(\gamma_l^{\mathrm{bh}},\gamma_{\min}^{\mathrm{bh}}\) | 无量纲 | 回传线性 SINR 及最低可用门槛 |
| \(\zeta_{\mathrm{bh}},\Gamma_{\mathrm{bh}},\eta_{\max}^{\mathrm{bh}}\) | — | 回传净荷比例、实现差距、原始频谱效率上限 |
| \(A_l^{\mathrm{bh}}\in\{0,1\}\) | — | 位置 \(l\) 的回传可用标志；为 0 时该位置不进入 \(\mathcal L\) |
| \(B_{\mathrm{total}}^{\mathrm{bh}},\ B_{\mathrm{eq}}^{\mathrm{bh}}=B_{\mathrm{total}}^{\mathrm{bh}}/K\) | Hz | 专用回传频段总带宽、按最大 UAV 数预分的每架份额 |
| \(\eta_l^{\mathrm{bh}}\) | bit/s/Hz | 位置 \(l\) 的预计算有效回传频谱效率 |
| \(C_l^{\mathrm{bh}}=A_l^{\mathrm{bh}}B_{\mathrm{eq}}^{\mathrm{bh}}\eta_l^{\mathrm{bh}}\) | bit/s | 位置 \(l\) 的固定回传容量 |
| \(\beta_G,\ C_G^{\min},C_G^{\max}\) | 无量纲, bit/s | 网关容量相对总需求的比例、共享容量下限与上限 |

\[
C_G=\operatorname{clip}\left(\beta_G\sum_{u\in\mathcal U}d_u,\ C_G^{\min},\ C_G^{\max}\right)
\]

回传复用接入的"几何—平均路径损耗—线性增益—噪声与干扰—SINR—截顶频谱效率"计算顺序，但使用带 `bh` 标记的独立参数。\(\gamma_{\min}^{A}\) 与 \(\gamma_{\min}^{\mathrm{bh}}\) 当前数值相同，**语义仍分别保留**。

---

## 8. 能量模型

| 符号 | 单位 | 含义 |
|---|---:|---|
| \(\mathbf p_l,\ \mathbf p_s\) | m | 候选位置与固定集结点的二维水平坐标向量 |
| \(d_l^{\mathrm{fly}}=\|\mathbf p_l-\mathbf p_s\|_2\) | m | 集结点至位置 \(l\) 的单程水平飞行距离 |
| \(E_{\mathrm{TOL}}\) | J | 起飞、爬升、下降、着陆的固定代理能耗（`TOL` = take-off and landing，同时吸收垂直爬升与下降） |
| \(P_{\mathrm{cr}},\ v_{\mathrm{cr}}\) | W, m/s | 固定巡航推进功率与巡航速度 |
| \(P_{\mathrm{hov}},\ P_{\mathrm{base}}\) | W | 驻站悬停推进功率、航电/机载计算/固定回传设备的基础功率 |
| \(E_{\mathrm{bat}},\ \rho_{\mathrm{res}}\in(0,1)\) | J, 无量纲 | 额定电池能量、返航与电池保护的保留比例 |
| \(E^{\mathrm{use}}=(1-\rho_{\mathrm{res}})E_{\mathrm{bat}}\) | J | 任务可用能量 |
| \(E_l^{\mathrm{tx}}=T\frac{p_A}{\xi_{\mathrm{PA}}}\sum_{u:(u,l)\in\mathcal E^{\mathrm{acc}}}b_{ul}\) | J | 位置 \(l\) 上接入射频发射产生的直流侧任务能耗 |

\[
E_l^{\mathrm{fixed}}=E_{\mathrm{TOL}}+2\frac{P_{\mathrm{cr}}}{v_{\mathrm{cr}}}d_l^{\mathrm{fly}}+T(P_{\mathrm{hov}}+P_{\mathrm{base}}),
\qquad
E_l^{\mathrm{fixed}}y_l+E_l^{\mathrm{tx}}\le E^{\mathrm{use}}y_l
\]

数字 2 表示去程和返程。\(\|\cdot\|_2\) 是二维欧氏范数。

---

## 9. GNN、strong branching 与模仿诊断

| 符号 | 单位 | 含义 |
|---|---:|---|
| \(s_{ni}\) | 求解器分数 | 节点 \(n\) 上候选 \(i\) 的 strong-branching 专家分数 |
| \(s_{n,\max}=\max_{i\in\mathcal B_n}s_{ni}\) | 求解器分数 | 该节点全部有效候选的最大专家分数 |
| \(\tau_{\mathrm{tie}}\) | 无量纲 | 并列判定的相对容差 |
| \(t_{ni}\) | \([0,1]\) | 行为克隆的目标概率 |
| \(\hat s_{ni},\ \hat p_{ni}\) | — | GNN 对候选 \(i\) 的未归一化分数，以及只在 \(\mathcal B_n\) 上 masked softmax 后的概率 |
| \(N_{\mathrm{lab}}\) | 正整数 | 当前损失中包含的已标注树节点数 |
| \(\mathcal L_{\mathrm{BC}}\) | 无量纲 | 候选掩码下的行为克隆交叉熵损失 |
| \(i_n^\star\) | 候选索引 | GNN 在节点 \(n\) 选出的最高分合法候选 |
| \(\operatorname{regret}_n\) | 无量纲 | 所选候选相对专家最大分数的归一化遗憾 |
| \(N_n^{\mathrm{LP}}\) | 非负整数 | `nlpcands`，LP fractional candidate 数 |
| \(N_n^{\mathrm{prio}}\) | 非负整数 | `npriolpcands`；\(|\mathcal B_n|=N_n^{\mathrm{prio}}\) |
| \(N_n^{\mathrm{impl}}\) | 非负整数 | `nfracimplvars`，**不进入 \(\mathcal B_n\)** |
| \(\phi_n\) | 映射 | 本次回调中 \(\mathcal B_n\to\mathcal R_n^{\mathrm{graph}}\) 的可核验映射 |

\[
\mathcal Y_n=\left\{i\in\mathcal B_n:\ |s_{ni}-s_{n,\max}|\le\tau_{\mathrm{tie}}\max(1,|s_{n,\max}|)\right\}
\]

\[
t_{ni}=\begin{cases}1/|\mathcal Y_n|,&i\in\mathcal Y_n\\0,&i\notin\mathcal Y_n\end{cases}
\qquad
\mathcal L_{\mathrm{BC}}=-\frac{1}{N_{\mathrm{lab}}}\sum_n\sum_{i\in\mathcal B_n}t_{ni}\log\hat p_{ni}
\qquad
\operatorname{regret}_n=\frac{s_{n,\max}-s_{n,i_n^\star}}{\max(1,|s_{n,\max}|)}
\]

- 交叉熵中的 `log` 使用**自然对数**；改变底数只按常数缩放损失，但实现和报告统一用自然对数。
- 这些模仿指标**只在有专家标签的训练或验证节点上定义**；正式 ID 测试与 OOD 主结果不生成专家标签。
- \(\phi_n\) 只要求当前候选与当前 LP 图列之间可双向核验，**不表示原始变量、transformed variables 和 LP columns 全局一一对应**。每次 LP 分支回调都必须重建 \(\phi_n\)，不得复用上一个节点的 LP position。

---

## 10. 数据与实验控制量

| 符号 | 含义 | 数值 |
|---|---|---|
| \(N_{\mathrm{ID}}\) | 同分布基础场景总数 | `yaml: frozen_reference_parameters.id_base_scenario_count` |
| \(N_{\mathrm{train}},N_{\mathrm{val}},N_{\mathrm{test}}\) | 训练/验证/ID 测试场景数 | `yaml: evaluation_protocol.dataset_split` |
| \(N_{\mathrm{pilot}}\) | pilot 场景数（Pilot-A 与 Pilot-B 共用同一批） | `yaml: frozen_reference_parameters.pilot_scenario_count` |
| \(N_{\mathrm{OOD}}^{f}\) | 每个 OOD 因素族的场景数 | `yaml: frozen_reference_parameters.ood_scenario_count_per_family` |
| \(p_{\mathrm{query}}\) | 深度 1–8 节点的 strong branching 查询概率 | `yaml: frozen_reference_parameters.expert_query_probability` |
| \(d_{\max}^{\mathrm{GNN}}\) | 在线调用 GNN 的最大树深。**这里的 \(d\) 是 depth，不是距离或需求** | `yaml: frozen_reference_parameters.max_gnn_tree_depth_inclusive` |
| \(N_{\mathrm{call}}^{\max}\) | 单实例最大 GNN 调用次数 | `yaml: frozen_reference_parameters.max_gnn_calls_per_instance` |
| \(t_{\mathrm{label}}^{\max}\) | 单实例专家标签生成墙钟上限 | `yaml: frozen_reference_parameters.max_labels_per_labeled_train_or_validation_instance` 同组 |
| \(t_{\mathrm{solve}}^{\max}\) | 单次正式 SCIP 求解墙钟上限 | `yaml: frozen_reference_parameters.formal_solver_time_limit_s` |
| \(\Delta_F\) | 冻结权重逐分量安全解析区间的跨度 | `yaml: predeclared_one_factor_sensitivity.protocol.fixed_objective_span_for_all_normalized_weight_profiles` |
| \(F^{\mathrm{inc}}(t),\ F^{\mathrm{dual}}(t)\) | 时刻 \(t\) 的 incumbent 目标值与有效 dual 上界 | — |
| \(g_{\mathrm{norm}}(t)\) | 固定跨度 normalized bound gap | — |
| \(\mathrm{nPDI}\) | 时间平均 normalized primal-dual integral | — |

\[
g_{\mathrm{norm}}(t)=\frac{\max\{0,\ F^{\mathrm{dual}}(t)-F^{\mathrm{inc}}(t)\}}{\Delta_F},
\qquad
\mathrm{nPDI}=\frac{1}{t_{\mathrm{solve}}^{\max}}\int_0^{t_{\mathrm{solve}}^{\max}}g_{\mathrm{norm}}(t)\,dt
\]

**四条使用纪律**：

1. 计时起点向所有方法提交并验证相同的平凡可行解 \(y=x=b=z=0,\ \delta_u=q_u\)，因此正常运行从起点即有 incumbent；**仍无 incumbent 则记为实现错误和无效运行，不静默填零**。
2. 有效 dual 在 SCIP 首次给出有限上界前取该权重 profile 的逐分量解析上界 \(\alpha_H+\alpha_R\)，之后取 \(\min(\alpha_H+\alpha_R,\ \text{SCIP dual})\)。**权重敏感性必须用各自 profile 的 \(\alpha_H+\alpha_R\)**；因所有 profile 正权重和为 1，\(\Delta_F\) 恒为 1.0。
3. 积分按 incumbent 或有效 dual 的**更新事件**构造分段常数轨迹计算，**不作结果驱动的截断或平滑**。
4. **SCIP 原生相对 gap 只保存为诊断字段**；目标跨越 0 时它不是正式 nPDI 的定义。

---

## 11. 运算符与书写约定

| 写法 | 含义 |
|---|---|
| \(|\mathcal S|\) | 集合元素数量；竖线包围标量时表示绝对值，由上下文区分 |
| \(\sum\) | 对下标给定的集合或索引范围求和 |
| \(\|\mathbf v\|_2\) | 向量欧氏范数 |
| \(\operatorname{clip}(v,\underline c,\overline c)\) | 把 \(v\) 限制在下界与上界之间 |
| \(\min,\max\) | 取最小值、最大值 |
| \(:=\) | 左侧由右侧定义，**不是新增决策约束** |
| \(\mathbb R_{\ge0}\) | 全部非负实数 |

软件版本、配置键、随机种子、文件哈希和硬件名称**不是数学符号**，直接按 `experiment_space.yaml` 与实验清单记录。
