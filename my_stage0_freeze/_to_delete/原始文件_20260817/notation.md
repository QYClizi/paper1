# Stage 0 符号表 v0.2

## 文件职责

本文件是论文、实现和实验日志中数学符号的集中索引；研究选择及理由见 `decisions.md`，完整规范见 `scope.md`，程序参数值见 `experiment_space.yaml`，单位和换算规则见 `units.md`，训练前后的验收边界见 `pilot_protocol_v0.2.md`。

除非特别说明，花体大写字母表示集合，普通大写或希腊字母表示已知参数或派生量，小写字母表示索引、坐标、参数或决策变量；上标 `A` 表示接入（access），上标 `bh` 表示回传（backhaul）。

## 集合与索引

| 符号 | 含义 |
|---|---|
| \(\mathcal U\) | 全部用户集合；`scope.md` 中的纯文本别名为 `U`。 |
| \(\mathcal C\subseteq\mathcal U\) | 关键用户集合；每个实例满足 \(\lvert\mathcal C\rvert\ge 1\)。 |
| \(\mathcal L^0\) | 禁飞区、能量和回传过滤前的原始 UAV 候选位置集合。 |
| \(\mathcal L\subseteq\mathcal L^0\) | 确定性预处理后保留的 UAV 候选位置集合。 |
| \(\mathcal E^{\mathrm{acc}}\subseteq\mathcal U\times\mathcal L\) | 达到接入物理可用门槛的用户—候选位置边集合。 |
| \(\mathcal B_n\) | SCIP 在节点 \(n\) 的 `getLPBranchCands()` 结果中前 `npriolpcands` 个当前 transformed LP 优先候选组成的集合；这是 v0.2 唯一允许评分的集合。 |
| \(\mathcal Y_n\subseteq\mathcal B_n\) | 节点 \(n\) 上按照并列规则得到的 strong-branching 最佳候选集合。 |
| \(\mathcal V_n^{\mathrm{LP}}\) | 节点 \(n\) 当前 LP 的列变量集合；它会随 presolve、cuts、局部界和 LP 重建变化。 |
| \(\mathcal R_n^{\mathrm{graph}}\) | 节点 \(n\) 的二部图中对应当前 LP 列的变量侧行集合。 |
| \(u\) | 用户索引，\(u\in\mathcal U\)。 |
| \(l\) | UAV 候选位置索引，\(l\in\mathcal L^0\)；进入 MILP 后通常有 \(l\in\mathcal L\)。 |
| \(n\) | 分支定界树节点索引。 |
| \(i\) | 当前树节点中合法分支候选的索引。 |
| \(e\) | 传播环境类别索引，例如 urban、suburban 或 dense urban。 |
| \(k\) | `accuracy@k` 中的排名截断位置；小写 \(k\) 不表示最大 UAV 数量。 |

下标 `t` 和 `r` 分别表示发射端与接收端，`G` 表示固定网关，`D` 表示无人机高度语境中的 drone，`s` 表示 UAV 集结点，`PA` 表示功率放大器。

## MILP 已知参数

| 符号 | 单位或范围 | 含义 |
|---|---:|---|
| \(K\) | 正整数 | 同质 UAV 的最大可部署数量。 |
| \(B\) | Hz | 每架已部署 UAV 的接入总带宽。 |
| \(b_{\min}\) | Hz | 激活一条用户关联后必须分配的最小等效平均带宽。 |
| \(d_u\) | bit/s | 用户 \(u\) 的有效需求上限；超过它的服务不增加目标收益。 |
| \(q_u\) | bit/s | 关键用户 \(u\) 的最低达标速率，满足 \(0<q_u\le d_u\)。 |
| \(q_{\mathrm{crit}}\) | bit/s | 当前统一的关键用户达标速率，v0.1 中所有关键用户均有 \(q_u=q_{\mathrm{crit}}\)。 |
| \(\eta_{ul}\) | bit/s/Hz | 接入边 \((u,l)\) 的预计算有效净荷频谱效率。 |
| \(C_l^{\mathrm{bh}}\) | bit/s | 候选位置 \(l\) 的预计算固定回传容量。 |
| \(C_G\) | bit/s | 所有已部署 UAV 共用的网关总容量。 |
| \(E_l^{\mathrm{fixed}}\) | J | UAV 前往位置 \(l\)、返回并驻站服务产生的固定任务能耗。 |
| \(E^{\mathrm{use}}\) | J | 每架 UAV 在保留电量后允许用于本任务的能量。 |
| \(T\) | s | UAV 到达候选位置后的驻站悬停服务时间，不含往返巡航时间。 |
| \(p_A\) | W/Hz | 接入发射机天线端口处的固定传导射频功率谱密度，不是 EIRP PSD。 |
| \(\xi_{\mathrm{PA}}\) | 无量纲，\((0,1]\) | 从直流输入到接入天线端口射频输出的功率放大器效率。 |
| \(M_l^E\) | Hz | 位置 \(l\) 在能量余量下允许的接入总带宽上界。 |
| \(M_{ul}\) | Hz | 边 \((u,l)\) 的紧带宽连接上界，用于替代统一的松上界 \(B\)。 |

这里的 \(d_u\) 是“需求”；带两个下标的 \(d_{ul}\) 是接入三维距离，带 `fly` 标记的 \(d_l^{\mathrm{fly}}\) 是飞行距离，三者不能互换。

## MILP 决策变量

| 符号 | 定义域 | 含义 |
|---|---:|---|
| \(y_l\) | \(\{0,1\}\) | 是否在候选位置 \(l\) 部署一架 UAV。 |
| \(x_{ul}\) | \(\{0,1\}\) | 用户 \(u\) 是否关联位置 \(l\) 上的 UAV；只对 \((u,l)\in\mathcal E^{\mathrm{acc}}\) 建立。 |
| \(b_{ul}\) | \(\mathbb R_{\ge0}\)，Hz | 关联边 \((u,l)\) 在整个静态任务窗口中的等效平均使用带宽。 |
| \(z_u\) | \(\{0,1\}\) | 关键用户达标计数变量；单向连接约束与目标正权重使其在最优解中正确表示是否达标。 |
| \(\delta_u\) | \([0,q_u]\)，bit/s | 关键用户缺口辅助变量；下界约束与目标负权重使其在最优解中等于实际非负缺口。 |

`z_u` 和 `delta_u` 的上述语义依赖最优目标方向，因此不把它们称为任意可行解中的严格双向指示量。

v0.2 的逐位置能量带宽上界和逐边紧上界定义为

\[
M_l^E=\frac{(E^{\mathrm{use}}-E_l^{\mathrm{fixed}})\xi_{\mathrm{PA}}}
{Tp_A},
\qquad
M_{ul}=\min\left\{B,\frac{d_u}{\eta_{ul}},
\frac{C_l^{\mathrm{bh}}}{\eta_{ul}},
\frac{C_G}{\eta_{ul}},M_l^E\right\}.
\]

只有满足 \(E_l^{\mathrm{fixed}}\le E^{\mathrm{use}}\) 的位置才进入 \(\mathcal L\)，所以 \(M_l^E\ge0\)。模型采用

\[
b_{ul}\le M_{ul}x_{ul}
\]

替代 \(b_{ul}\le Bx_{ul}\)，并加入有效不等式

\[
z_u\le\sum_{l:(u,l)\in\mathcal E^{\mathrm{acc}}}x_{ul}.
\]

二者都不删除原模型的任何整数可行解；若实现测试发现最优值变化，视为 P0 错误。

## 派生服务量与目标

| 符号 | 单位或范围 | 含义 |
|---|---:|---|
| \(r_{ul}=\eta_{ul}b_{ul}\) | bit/s | 接入边 \((u,l)\) 的平均服务速率；它是派生量，不是独立决策变量。 |
| \(S_u=\sum_{l:(u,l)\in\mathcal E^{\mathrm{acc}}}\eta_{ul}b_{ul}\) | bit/s | 用户 \(u\) 从其至多一个关联 UAV 获得的总平均服务速率。 |
| \(H_C=\lvert\mathcal C\rvert^{-1}\sum_{u\in\mathcal C}z_u\) | \([0,1]\) | 关键用户达标比例。 |
| \(Q_C=\lvert\mathcal C\rvert^{-1}\sum_{u\in\mathcal C}\delta_u/q_u\) | \([0,1]\) | 关键用户平均相对服务缺口。 |
| \(R_{\mathrm{all}}=\frac{\sum_{u\in\mathcal U}S_u}{\sum_{u\in\mathcal U}d_u}\) | \([0,1]\) | 全体用户有效需求满足比例。 |
| \(D_{\mathrm{frac}}=K^{-1}\sum_{l\in\mathcal L}y_l\) | \([0,1]\) | 可用 UAV 中实际部署的比例。 |
| \(F\) | 无量纲 | 最终归一化加权目标值。 |
| \(\alpha_H,\alpha_Q,\alpha_R,\alpha_D\) | 正数且和为 1 | 依次为关键用户达标、关键用户缺口、全体服务和部署惩罚的权重。 |

最终目标为

\[
\max F=\alpha_HH_C-\alpha_QQ_C+\alpha_RR_{\mathrm{all}}-\alpha_DD_{\mathrm{frac}}.
\]

所有分母都是实例生成后已知的常数，且没有两个决策变量相乘，所以 v0.2 仍是 MILP，不是 MIQP。

## 几何与接入链路预计算

| 符号 | 单位或范围 | 含义 |
|---|---:|---|
| \((X_u,Y_u)\) | m | 用户 \(u\) 的横、纵坐标；大写坐标用于避免与变量 \(x_{ul}\)、\(y_l\) 冲突。 |
| \((X_l,Y_l)\) | m | 候选位置 \(l\) 的横、纵坐标。 |
| \(h_u\) | m | 用户终端高度。 |
| \(h_D\) | m | 本实例固定 UAV 高度。 |
| \(\rho_{ul}\) | m | 用户 \(u\) 与位置 \(l\) 的水平距离。 |
| \(d_{ul}\) | m | 用户 \(u\) 与位置 \(l\) 的三维接入链路距离。 |
| \(\theta_{ul}\) | degree | 从用户指向 UAV 的仰角。 |
| \(P_{ul}^{\mathrm{LoS}}\) | \([0,1]\) | 接入链路的视距传播概率。 |
| \(a_e,b_e\) | 模型经验量 | 环境 \(e\) 的 Al-Hourani LoS 概率参数；其数值按以度为单位的仰角使用。 |
| \(L_{ul}^{A}\) | dB | 接入平均路径损耗。 |
| \(f_A\) | Hz | 接入中心频率。 |
| \(c\) | m/s | 真空光速。 |
| \(\eta_{\mathrm{LoS}}^{A},\eta_{\mathrm{NLoS}}^{A}\) | dB | 接入 LoS 与 NLoS 的额外平均损耗；它们不是频谱效率 \(\eta_{ul}\)。 |
| \(M_F^{A}\) | dB | 接入固定可靠性或阴影衰落裕量。 |
| \(G_t^{A},G_r^{A}\) | dBi | 接入发射与接收天线增益。 |
| \(L_{\mathrm{dev}}^{A}\) | dB | 接入链路的固定设备损耗。 |
| \(g_{ul}^{A}\) | 无量纲 | 把天线增益、设备损耗和路径损耗合并并转为线性尺度后的净链路增益。 |
| \(NF_A\) | dB | 接入接收机噪声系数。 |
| \(F_A=10^{NF_A/10}\) | 无量纲 | 接入接收机线性噪声因子；下标 `A` 区别于目标值 \(F\)。 |
| \(k_B\) | J/K | 玻尔兹曼常数。 |
| \(T_0\) | K | 计算热噪声时使用的参考绝对温度。 |
| \(N_0^{A}=k_BT_0F_A\) | W/Hz | 包含接收机噪声因子的接入噪声 PSD。 |
| \(M_I^{A}\) | dB | 接入干扰加噪声相对纯噪声的固定抬升量。 |
| \(I_0^{A}=N_0^{A}(10^{M_I^{A}/10}-1)\) | W/Hz | 接入固定保守干扰 PSD。 |
| \(\gamma_{ul}\) | 无量纲 | 接入链路的线性 SINR。 |
| \(\gamma_{\min}^{A}\) | 无量纲 | 生成接入边所需的最低线性 SINR。 |
| \(\zeta_A\) | \((0,1]\) | 扣除导频、控制和保护间隔后的接入净荷比例。 |
| \(\Gamma_A\) | \([1,\infty)\) | 接入相对理想 Shannon 容量的实现差距因子。 |
| \(\eta_{\max}^{A}\) | bit/s/Hz | 接入原始频谱效率上限。 |
| \(\eta_{\min}\) | bit/s/Hz | 用于工程近似 SINR 门槛的最低原始 MCS 频谱效率。 |

其中 \(\pi\) 是圆周率，`sqrt` 是平方根，`atan2` 是保留象限的反正切函数，`exp` 是自然指数函数，`log10` 和 `log2` 分别是以 10 和 2 为底的对数。

## 回传链路与网关

| 符号 | 单位或范围 | 含义 |
|---|---:|---|
| \(\mathbf p_G,h_G\) | m | 固定网关的二维坐标向量与高度。 |
| \(\rho_l^{\mathrm{bh}},d_l^{\mathrm{bh}},\theta_l^{\mathrm{bh}}\) | m、m、degree | 位置 \(l\) 至网关的水平距离、三维距离和仰角。 |
| \(P_l^{\mathrm{LoS,bh}}\) | \([0,1]\) | 位置 \(l\) 至网关回传链路的 LoS 概率。 |
| \(f_{\mathrm{bh}}\) | Hz | 专用回传中心频率。 |
| \(p_{\mathrm{bh}}\) | W/Hz | 回传发射机天线端口处的固定传导射频 PSD。 |
| \(L_l^{\mathrm{bh}},g_l^{\mathrm{bh}}\) | dB、无量纲 | 回传平均路径损耗和线性净链路增益。 |
| \(G_t^{\mathrm{bh}},G_r^{\mathrm{bh}}\) | dBi | 回传发射与接收天线增益。 |
| \(L_{\mathrm{dev}}^{\mathrm{bh}},M_F^{\mathrm{bh}}\) | dB | 回传固定设备损耗和可靠性裕量。 |
| \(NF_{\mathrm{bh}},F_{\mathrm{bh}}\) | dB、无量纲 | 回传接收机噪声系数及其线性噪声因子，\(F_{\mathrm{bh}}=10^{NF_{\mathrm{bh}}/10}\)。 |
| \(N_0^{\mathrm{bh}},I_0^{\mathrm{bh}}\) | W/Hz | 回传噪声 PSD 和固定保守干扰 PSD。 |
| \(M_I^{\mathrm{bh}}\) | dB | 回传干扰或附加噪声抬升量。 |
| \(\gamma_l^{\mathrm{bh}},\gamma_{\min}^{\mathrm{bh}}\) | 无量纲 | 回传线性 SINR 及其最低可用门槛。 |
| \(\zeta_{\mathrm{bh}},\Gamma_{\mathrm{bh}},\eta_{\max}^{\mathrm{bh}}\) | 无量纲、无量纲、bit/s/Hz | 回传净荷比例、实现差距和原始频谱效率上限。 |
| \(A_l^{\mathrm{bh}}\) | \(\{0,1\}\) | 原始候选位置 \(l\in\mathcal L^0\) 的回传可用标志；为 0 时该位置不进入 \(\mathcal L\)。 |
| \(B_{\mathrm{total}}^{\mathrm{bh}}\) | Hz | 专用回传频段总带宽。 |
| \(B_{\mathrm{eq}}^{\mathrm{bh}}=B_{\mathrm{total}}^{\mathrm{bh}}/K\) | Hz | 按最大 UAV 数预先等分给每架 UAV 的固定回传带宽份额。 |
| \(\eta_l^{\mathrm{bh}}\) | bit/s/Hz | 位置 \(l\) 的预计算有效回传频谱效率。 |
| \(C_l^{\mathrm{bh}}=A_l^{\mathrm{bh}}B_{\mathrm{eq}}^{\mathrm{bh}}\eta_l^{\mathrm{bh}}\) | bit/s | 位置 \(l\) 的固定回传容量。 |
| \(\beta_G\) | 无量纲 | 网关容量相对于场景总需求的比例。 |
| \(C_G^{\min},C_G^{\max}\) | bit/s | 网关共享容量的下限和上限。 |

网关共享容量预计算为

\[
C_G=\operatorname{clip}\left(\beta_G\sum_{u\in\mathcal U}d_u,
C_G^{\min},C_G^{\max}\right),
\]

其中 `clip` 的三个输入依次是未截断容量、容量下限和容量上限，其他字母均在本节及 MILP 参数表中定义。

回传链路复用接入链路的“几何—平均路径损耗—线性增益—噪声与干扰—SINR—截顶频谱效率”计算顺序，但使用带 `bh` 标记的独立无线参数；\(\gamma_{\min}^{A}\) 与 \(\gamma_{\min}^{\mathrm{bh}}\) 当前数值相同，语义仍分别保留。

## 能量模型

| 符号 | 单位或范围 | 含义 |
|---|---:|---|
| \(\mathbf p_l,\mathbf p_s\) | m | 候选位置 \(l\) 与固定集结点的二维水平坐标向量。 |
| \(d_l^{\mathrm{fly}}=\|\mathbf p_l-\mathbf p_s\|_2\) | m | 集结点至候选位置 \(l\) 的单程水平飞行距离。 |
| \(E_{\mathrm{TOL}}\) | J | 起飞、爬升、下降和着陆的固定代理能耗。 |
| \(P_{\mathrm{cr}}\) | W | 固定巡航推进功率。 |
| \(v_{\mathrm{cr}}\) | m/s | 固定巡航速度。 |
| \(P_{\mathrm{hov}}\) | W | 驻站悬停推进功率。 |
| \(P_{\mathrm{base}}\) | W | 航电、机载计算和固定回传设备的基础功率。 |
| \(E_{\mathrm{bat}}\) | J | UAV 额定电池能量。 |
| \(\rho_{\mathrm{res}}\) | \((0,1)\) | 为返航和电池保护保留的电量比例。 |
| \(E^{\mathrm{use}}=(1-\rho_{\mathrm{res}})E_{\mathrm{bat}}\) | J | 扣除保留量后的任务可用能量。 |
| \(E_l^{\mathrm{tx}}=T\frac{p_A}{\xi_{\mathrm{PA}}}\sum_{u:(u,l)\in\mathcal E^{\mathrm{acc}}}b_{ul}\) | J | 位置 \(l\) 上接入射频发射产生的直流侧任务能耗。 |

固定能耗和完整位置能量约束分别为

\[
E_l^{\mathrm{fixed}}=E_{\mathrm{TOL}}
+2\frac{P_{\mathrm{cr}}}{v_{\mathrm{cr}}}d_l^{\mathrm{fly}}
+T(P_{\mathrm{hov}}+P_{\mathrm{base}}),
\]

\[
E_l^{\mathrm{fixed}}y_l+E_l^{\mathrm{tx}}
\le E^{\mathrm{use}}y_l.
\]

数字 2 表示集结点至候选位置的去程和返程；其余字母均在本节、MILP 参数表或决策变量表中定义。

`TOL` 是 take-off and landing 的标签，并在本项目中同时吸收垂直爬升和下降的代理能耗；\(\|\cdot\|_2\) 表示二维欧氏范数。

## GNN、强分支与模仿诊断

| 符号 | 单位或范围 | 含义 |
|---|---:|---|
| \(s_{ni}\) | 求解器分数 | 节点 \(n\) 上候选 \(i\) 的 strong-branching 专家分数。 |
| \(s_{n,\max}=\max_{i\in\mathcal B_n}s_{ni}\) | 求解器分数 | 节点 \(n\) 上全部有效候选的最大专家分数。 |
| \(\tau_{\mathrm{tie}}\) | 无量纲 | 判断候选是否与最大专家分数并列的相对容差。 |
| \(t_{ni}\) | \([0,1]\) | 行为克隆的目标概率；若 \(i\in\mathcal Y_n\)，则为 \(1/\lvert\mathcal Y_n\rvert\)，否则为 0。 |
| \(\hat s_{ni}\) | 模型分数 | GNN 为节点 \(n\) 上合法候选 \(i\) 输出的未归一化分数。 |
| \(\hat p_{ni}\) | \([0,1]\) | 只在合法候选集合 \(\mathcal B_n\) 上对 \(\hat s_{ni}\) 做 masked softmax 后的概率。 |
| \(N_{\mathrm{lab}}\) | 正整数 | 当前训练或验证损失中包含的已标注树节点数量。 |
| \(\mathcal L_{\mathrm{BC}}\) | 无量纲 | 候选掩码下的行为克隆交叉熵损失。 |
| \(i_n^\star\) | 候选索引 | GNN 在节点 \(n\) 选出的最高分合法候选。 |
| \(\operatorname{regret}_n\) | 无量纲 | GNN 所选候选相对于专家最大分数的归一化遗憾。 |
| \(N_n^{\mathrm{LP}}\) | 非负整数 | `getLPBranchCands()` 报告的 LP fractional candidate 数。 |
| \(N_n^{\mathrm{prio}}\) | 非负整数 | `npriolpcands`；\(\lvert\mathcal B_n\rvert=N_n^{\mathrm{prio}}\)。 |
| \(N_n^{\mathrm{impl}}\) | 非负整数 | `nfracimplvars`，即 API 附加的 fractional implicit integer 数，不进入 \(\mathcal B_n\)。 |
| \(\phi_n\) | 映射 | 当前回调中从候选 \(\mathcal B_n\) 到图变量行 \(\mathcal R_n^{\mathrm{graph}}\) 的可核验映射。 |

并列集合、目标分布、损失和验证遗憾分别定义为

\[
\mathcal Y_n=\left\{i\in\mathcal B_n:\ |s_{ni}-s_{n,\max}|\le
\tau_{\mathrm{tie}}\max(1,|s_{n,\max}|)\right\},
\]

\[
t_{ni}=\begin{cases}
1/|\mathcal Y_n|,&i\in\mathcal Y_n,\\
0,&i\notin\mathcal Y_n,
\end{cases}
\qquad
\mathcal L_{\mathrm{BC}}=-\frac{1}{N_{\mathrm{lab}}}
\sum_n\sum_{i\in\mathcal B_n}t_{ni}\log \hat p_{ni},
\]

\[
\operatorname{regret}_n=
\frac{s_{n,\max}-s_{n,i_n^\star}}
{\max(1,|s_{n,\max}|)}.
\]

这些模仿指标只在有专家标签的训练或验证节点上定义；正式 ID 测试与 OOD 主结果不生成专家标签。
交叉熵中的 `log` 使用自然对数；改变对数底只会按常数缩放损失，但实现和报告统一采用自然对数。

映射 \(\phi_n\) 只要求当前候选与当前 LP 图列之间可双向核验，不表示原始模型全部变量、SCIP transformed variables 和 LP columns 全局一一对应。每次 LP 分支回调都必须重建 \(\phi_n\)，不得复用上一个节点的 LP position。

## 数据与实验控制量

| 符号 | 取值或单位 | 含义 |
|---|---|---|
| \(N_{\mathrm{ID}}\) | 非负整数 | 同分布基础场景总数；v0.2 在 Pilot-A 通过前沿用 v0.1 的 800 个计划值，但尚未解锁正式生成。 |
| \(N_{\mathrm{train}},N_{\mathrm{val}},N_{\mathrm{test}}\) | 非负整数 | 训练、验证和 ID 测试场景数，依次为 560、120、120。 |
| \(N_{\mathrm{pilot}}\) | 非负整数 | pilot 场景数，v0.2 为 60，并拆成训练前 Pilot-A 与训练后 Pilot-B 两次用途。 |
| \(N_{\mathrm{OOD}}^{f}\) | 非负整数 | OOD 因素族 \(f\) 的场景数；每个因素族为 60。 |
| \(p_{\mathrm{query}}\) | 概率 | 根节点之后、允许深度范围内查询 strong branching 的节点采样概率，沿用值为 0.05。 |
| \(d_{\max}^{\mathrm{GNN}}\) | 非负整数 | 在线调用 GNN 的最大树深，沿用值为 8；这里的 \(d\) 表示 depth，不是距离或需求。 |
| \(N_{\mathrm{call}}^{\max}\) | 非负整数 | 单实例允许的最大 GNN 调用次数，沿用值为 64。 |
| \(t_{\mathrm{label}}^{\max}\) | s | 单个训练或验证实例的专家标签生成墙钟上限，沿用值为 120 s。 |
| \(t_{\mathrm{solve}}^{\max}\) | s | 单次正式 SCIP 求解墙钟上限，沿用值为 300 s。 |
| \(\Delta_F\) | 无量纲，固定为 1.0 | 冻结参考权重逐分量安全解析区间 \([-0.21,0.79]\) 的跨度；不声称端点可达，只用于与平移无关的 bound-gap 归一化。 |
| \(F^{\mathrm{inc}}(t)\) | 无量纲 | 最大化问题在时刻 \(t\) 的 incumbent 目标值，即有效 primal bound。 |
| \(F^{\mathrm{dual}}(t)\) | 无量纲 | 最大化问题在时刻 \(t\) 的有效 dual upper bound。 |
| \(g_{\mathrm{norm}}(t)\) | \([0,\infty)\) | 固定跨度 normalized bound gap。 |
| \(\mathrm{nPDI}\) | 无量纲 | 在统一时限内对 \(g_{\mathrm{norm}}\) 积分后再除以时限的时间平均 normalized primal-dual integral。 |

存在 incumbent 时，v0.2 的主 gap 和 nPDI 定义为

\[
g_{\mathrm{norm}}(t)=
\frac{\max\{0,F^{\mathrm{dual}}(t)-F^{\mathrm{inc}}(t)\}}{\Delta_F},
\qquad
\mathrm{nPDI}=\frac{1}{t_{\mathrm{solve}}^{\max}}
\int_0^{t_{\mathrm{solve}}^{\max}}g_{\mathrm{norm}}(t)\,dt.
\]

计时起点向所有方法提交并验证相同的平凡可行解 `y=x=b=z=0, delta=q`，因此正常运行从起点即有 incumbent；若仍无 incumbent，按 `pilot_protocol_v0.2.md` 记为实现错误和无效运行。有效 dual 在 SCIP 首次给出有限上界前，冻结参考权重取逐分量解析上界 `alpha_H+alpha_R=0.79`，随后取 `min(0.79, SCIP dual)`；其他权重 profile 使用各自的 `alpha_H+alpha_R`。SCIP 原生相对 gap 继续保存为诊断字段，但不作为目标跨 0 时的正式 nPDI 定义。

## 运算符与书写约定

| 写法 | 含义 |
|---|---|
| \(\lvert\mathcal S\rvert\) | 集合 \(\mathcal S\) 的元素数量；当竖线包围标量时表示绝对值，需由上下文区分。 |
| \(\sum\) | 对下标给定的集合或索引范围求和。 |
| \(\|\mathbf v\|_2\) | 向量 \(\mathbf v\) 的欧氏范数。 |
| \(\operatorname{clip}(v,\underline c,\overline c)\) | 把数值 \(v\) 限制在下界 \(\underline c\) 与上界 \(\overline c\) 之间。 |
| \(\min,\max\) | 分别取给定数值中的最小值和最大值。 |
| \(:=\) | 左侧量由右侧表达式定义，而不是新增决策约束。 |
| \(\mathbb R_{\ge0}\) | 全部非负实数的集合。 |

软件版本、配置键、随机种子、文件哈希和硬件名称不是数学符号，直接按照 `experiment_space.yaml` 与实验清单记录。
