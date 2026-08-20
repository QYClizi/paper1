# Stage 0 单位与优化缩放规范

> **本文件只回答"单位怎么用、怎么换算、怎么自检"。** 符号见 `notation.md`，规范见 `scope.md`，理由见 `decisions.md`，数值见 `experiment_space.yaml`，验收门见 `pilot_protocol_v0.2.md`。
>
> **两层单位体系**：场景文件和物理预计算使用 SI；送入 SCIP 的线性模型使用等价的 MHz / Mbit/s / kJ 缩放。**两层之间只能通过集中转换函数连接，不能在约束构造代码中临时猜测单位。**

---

## 1. 场景存储与物理预计算单位

| 物理量 | 内部单位 | YAML 后缀 | 说明 |
|---|---|---|---|
| 距离、高度、坐标 | m | `_m` | 坐标也统一用米 |
| 面积 | m² | `_m2` | 不把 km² 数值直接写入几何计算 |
| 时间 | s | `_s` | 求解时限、标签时限、任务时长均用秒 |
| 速度 | m/s | `_m_per_s` | |
| 频率 | Hz | `_hz` | 配置中已换算成 Hz |
| 带宽 | Hz | `_bandwidth_hz` / `_hz` | MHz 必须先乘 \(10^6\) |
| 数据速率 | bit/s | `_bps` | Mbit/s 必须先乘 \(10^6\) |
| 频谱效率 | bit/s/Hz | `_bits_per_s_per_hz` | **不等同于速率** |
| 功率 | W | `_w` | |
| 功率谱密度 | W/Hz | `_w_per_hz` | 乘实际使用带宽后才得到 W |
| 能量 | J | `_j` | Wh 必须先乘 3600 |
| 绝对温度 | K | `_k` | |
| 几何角度 | degree | `_deg` | **Al-Hourani 模型用度**；三角函数返回弧度必须显式转换 |
| 路径损耗、裕量、噪声系数 | dB | `_db` | 对数量，**不得直接当线性乘数** |
| 天线增益 | dBi | `_dbi` | |
| SINR 计算值 | linear | `_linear` | **Shannon 型公式和阈值比较必须用线性 SINR** |
| SINR 报告值 | dB | `_db` | 只用于日志、图表、论文展示 |
| 概率、比例、效率 | 无量纲 \([0,1]\) | `_probability` / `_fraction` / `_efficiency` | 20% 写作 `0.20`，**不能写作 `20`** |
| 数量、索引、随机种子 | 整数 | `_count` / `_index` / `_seed` | 不附带物理单位 |

优化模型中的缩放量必须使用 `_mhz`、`_mbps`、`_kj` 后缀或 `scaled_` 前缀，**禁止复用 `_hz`、`_bps`、`_j` 字段名保存缩放后的数值**。

**前缀换算**：\(1\ \mathrm{km}=10^3\ \mathrm m\)；\(1\ \mathrm{GHz}=10^9\ \mathrm{Hz}\)；\(1\ \mathrm{MHz}=10^6\ \mathrm{Hz}\)；\(1\ \mathrm{Mbit/s}=10^6\ \mathrm{bit/s}\)；\(1\ \mathrm{Wh}=3600\ \mathrm J\)；\(1\ \mathrm{kWh}=3.6\times10^6\ \mathrm J\)。通信速率采用**十进制**前缀，不使用二进制的 Mibit/s。

---

## 2. SCIP 线性模型的数值缩放

### 2.1 缩放定义

\[
\widetilde b_{ul}=b_{ul}/10^6\ [\mathrm{MHz}];\qquad
\widetilde S_u,\widetilde d_u,\widetilde q_u,\widetilde C_l^{\mathrm{bh}},\widetilde C_G=(\cdot)/10^6\ [\mathrm{Mbit/s}];\qquad
\widetilde E=E/10^3\ [\mathrm{kJ}]
\]

频谱效率 \(\eta\) 的**数值不变**，因为 \(\eta\ [\mathrm{bit/s/Hz}]\times\widetilde b\ [\mathrm{MHz}]=\widetilde r\ [\mathrm{Mbit/s}]\)。所以缩放后服务等式仍写成 \(\widetilde S_u=\sum_l\eta_{ul}\widetilde b_{ul}\)。

逐边上界先在 SI 层计算并验证，再转换为 \(\widetilde M_{ul}=M_{ul}/10^6\) 进入约束 \(\widetilde b_{ul}\le\widetilde M_{ul}x_{ul}\)。

### 2.2 缩放后的通信能耗系数（最容易出错的一处）

当带宽以 MHz 建模、能量以 kJ 建模时，通信能耗项必须写成

\[
\frac{T(p_A/\xi_{\mathrm{PA}})(10^6\widetilde b)}{10^3}
=\underbrace{1000\,T\frac{p_A}{\xi_{\mathrm{PA}}}}_{\textstyle \kappa_E\ [\mathrm{kJ/MHz}]}\widetilde b
\]

**不得把 SI 公式中的 \(T(p_A/\xi_{\mathrm{PA}})b\) 原样作用于 MHz 数值，否则会产生 \(10^6\) 倍错误。**

### 2.3 边界转换五条

1. 场景生成器**只输出 SI 字段**；
2. `model_scaling` 层**一次性**生成 SCIP 所需的全部缩放字段；
3. SCIP solution **先转换回 SI**，再由独立 evaluator 重算物理约束和目标；
4. 原始日志同时保存 SI 值和缩放值的 schema 版本，**不依赖显示格式反推**；
5. 论文表格**从 SI 结果生成**，不能直接读取 SCIP 内部缩放列后省略单位。

---

## 3. 对数量与线性量换算

\[
P_{\mathrm W}=10^{(P_{\mathrm{dBm}}-30)/10},\qquad
g_{\mathrm{lin}}=10^{G_{\mathrm{dB}}/10},\qquad
F_{\mathrm{lin}}=10^{NF_{\mathrm{dB}}/10},\qquad
\gamma_{\mathrm{lin}}=10^{\gamma_{\mathrm{dB}}/10}
\]

路径损耗、天线增益、设备损耗和可靠性裕量**可以在 dB 域按正负号相加减**，得到的净 dB 增益**必须再转换成线性增益后才能进入功率或 SINR 公式**。

---

## 4. PSD、带宽、速率与能量

\[
P=p_{\mathrm{PSD}}B,\qquad r=\eta B,\qquad E=Pt
\]

量纲必须分别满足 \(\mathrm{W/Hz}\times\mathrm{Hz}=\mathrm W\)、\(\mathrm{bit/s/Hz}\times\mathrm{Hz}=\mathrm{bit/s}\)、\(\mathrm W\times\mathrm s=\mathrm J\)。

**本项目冻结的是天线端口传导 PSD**，因此天线增益没有包含在 \(p_{\mathrm{PSD}}\) 中，链路预算仍需单独加入发射天线增益；**不得把该 PSD 误写成 EIRP PSD 后再次加入天线增益**。

---

## 5. Shannon 型频谱效率与角度

\[
\eta_{\mathrm{eff}}=\zeta\min\left(\eta_{\max},\ \log_2\left(1+\frac{\gamma_{\mathrm{lin}}}{\Gamma}\right)\right)
\qquad
\theta_{\mathrm{deg}}=\frac{180}{\pi}\operatorname{atan2}(\Delta h,\rho)
\]

- **禁止把 dB SINR 直接代入频谱效率公式**，必须先转成线性值。
- 必须先得到**度数**才能代入 Al-Hourani 参数化的 LoS 概率公式。

---

## 6. 冻结数值的单位自检样例

下表是 A0 必须通过的量纲与数值自检。**输入一律从 YAML 读取，测试必须重新计算，不得把右列结果硬编码进代码。**

| 检查 | 输入来源（`yaml: frozen_reference_parameters.…`） | 期望结果 |
|---|---|---:|
| 接入满带宽传导功率 \(p_A\times B\) | `access_transmit_psd_w_per_hz`, `access_bandwidth_per_uav_hz` | \(1\ \mathrm W\) |
| 两块电池 Wh→J | `rated_battery_energy_j` | \(1{,}895{,}040\ \mathrm J\) |
| 保留后可用能量 \((1-\rho_{\mathrm{res}})E_{\mathrm{bat}}\) | `battery_reserve_fraction` | \(1{,}516{,}032\ \mathrm J\) |
| 9 dB 噪声系数转线性 | `access_noise_factor_linear` | \(7.943282347\) |
| 线性 SINR 转 dB | `access_minimum_sinr_linear` | 约 \(-4.5243\ \mathrm{dB}\) |
| 固定悬停+基础+起降能量 \(E_{\mathrm{TOL}}+T(P_{\mathrm{hov}}+P_{\mathrm{base}})\) | `takeoff_landing_energy_j`, `mission_service_duration_s`, `hover_power_w`, `baseline_equipment_power_w` | \(1{,}182{,}000\ \mathrm J=1182\ \mathrm{kJ}\) |
| 满带宽接入通信能量 \(T(p_A/\xi_{\mathrm{PA}})B\) | 上述 + `power_amplifier_efficiency` | \(6000\ \mathrm J=6\ \mathrm{kJ}\) |
| 缩放能耗系数 \(\kappa_E=1000\,T\,p_A/\xi_{\mathrm{PA}}\) | 同上 | \(0.3\ \mathrm{kJ/MHz}\) |
| 往返巡航距离系数 \(2P_{\mathrm{cr}}/v_{\mathrm{cr}}\) | `cruise_power_w`, `cruise_speed_m_per_s` | \(110\ \mathrm{J/m}\) |
| 满带宽下能量约束开始可能绑定的单程距离 \(d_{\mathrm{bind}}\) | 上述各项 | 约 \(2982\ \mathrm m\) |

> **关于 \(d_{\mathrm{bind}}\) 的使用纪律**：把它与"全部主 ID/OOD 候选到集结点的**实测**最大单程距离"比较，即可判定能量约束是否静态冗余（见 `scope.md` §5.6）。**实测最大距离必须由 A0 用实际生成的候选点算出并记录，不得引用任何文档中的估算值。**

---

## 7. 实现与审计规则

1. YAML 中带单位后缀的数值**已经是内部单位**，读取后不得再次乘前缀。
2. 场景生成器输出必须在字段名或 schema 中保留单位后缀，**禁止使用含义不明的 `distance`、`rate`、`power`**。
3. 链路与能量预计算只接收线性功率、线性增益、线性 SINR、Hz、bit/s、W、J；SCIP 模型只接收经集中转换的 MHz、Mbit/s、kJ。**dB/dBi/dBm 只在链路预计算和报告边界出现。**
4. `null` 表示未设置可选上限；字符串 `none`、数值 `0` 和 YAML 空值**不是同一含义**。
5. 浮点比较使用显式容差，**不能用字符串格式化后的展示值进行可行性判断**。
6. 每次生成数据必须执行量纲断言，至少检查：非负距离、概率范围、正带宽、PSD×带宽=功率、频谱效率×带宽=速率、能量预算。
7. 论文表格可以展示 km、MHz、Mbit/s、Wh、dB，但**表头必须写明单位**，并由内部 SI 值统一转换生成。
8. 每次构造模型必须对**至少一个随机边**同时用 SI 公式与缩放公式计算服务速率和通信能耗，断言还原后在容差内一致。
9. 求解完成后必须在 SI 层独立检查全部约束；**SCIP 缩放模型可行但 SI 复算失败属于 P0 错误**。
10. normalized gap 和 nPDI 是无量纲统计量；墙钟积分**在除以统一时限后**才称为本项目的无量纲 nPDI。
11. 逐边上界的删边判断统一在 **SI 的 Hz 层**执行：仅当 \(M_{ul}<b_{\min}-1\ \mathrm{Hz}\) 时删除；相等或差值不超过 1 Hz 时保留，再把保留边的上界转换成 MHz。
12. 场景规范序列化用于哈希前，**必须先把所有 NumPy 标量转成 Python 原生类型**，并固定浮点的规范化规则；否则 SHA-256 不可复现（见 `scope.md` §9）。
