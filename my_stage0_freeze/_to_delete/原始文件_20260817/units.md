# Stage 0 单位与优化缩放规范 v0.2

## 文件职责

本文件规定场景生成、链路预计算、优化模型、日志和论文表格使用的单位及换算规则；数学符号见 `notation.md`，具体冻结数值见 `experiment_space.yaml`，实现验收见 `pilot_protocol_v0.2.md`。

v0.2 区分两层：场景文件和物理预计算使用 SI 基本或明确派生单位；送入 SCIP 的线性模型使用等价的 MHz、Mbit/s 和 kJ 数值缩放，以减少矩阵系数跨度。两层之间只能通过集中转换函数连接，不能在约束构造代码中临时猜测单位。

## 场景存储与物理预计算单位

| 物理量 | 内部单位 | YAML 常用后缀 | 说明 |
|---|---|---|---|
| 水平、三维距离和高度 | m | `_m` | 坐标也统一使用米。 |
| 面积 | m² | `_m2` | 不把 km² 数值直接写入几何计算。 |
| 时间 | s | `_s` | 求解时限、标签时限和任务时长均使用秒。 |
| 速度 | m/s | `_m_per_s` | 巡航速度使用米每秒。 |
| 频率 | Hz | `_hz` | 中心频率在配置中已经换算成 Hz。 |
| 带宽 | Hz | `_bandwidth_hz` 或 `_hz` | MHz 必须先乘 \(10^6\)。 |
| 数据速率 | bit/s | `_bps` | Mbit/s 必须先乘 \(10^6\)。 |
| 频谱效率 | bit/s/Hz | `_bits_per_s_per_hz` | 数值上可简写为 bit/s/Hz，不等同于速率。 |
| 功率 | W | `_w` | 发射、巡航、悬停和基础功率均使用瓦。 |
| 功率谱密度 | W/Hz | `_w_per_hz` | 乘实际使用带宽后才得到 W。 |
| 能量 | J | `_j` | Wh 必须先乘 3600。 |
| 绝对温度 | K | `_k` | 热噪声公式使用开尔文。 |
| 几何角度 | degree | `_deg` | Al-Hourani 概率模型使用度；三角函数接口若返回弧度必须显式转换。 |
| 路径损耗、裕量和噪声系数 | dB | `_db` | 这些是对数量，不得直接当作线性乘数。 |
| 天线增益 | dBi | `_dbi` | 相对于各向同性天线的对数增益。 |
| SINR 计算值 | linear | `_linear` | Shannon 型公式和阈值比较必须使用线性 SINR。 |
| SINR 报告值 | dB | `_db` | 只用于日志、图表和论文展示。 |
| 概率、比例和效率 | 无量纲 \([0,1]\) | `_probability`、`_fraction`、`_efficiency` | 20% 在配置中写作 `0.20`，不能写作 `20`。 |
| 数量、索引和随机种子 | 整数 | `_count`、`_index`、`_seed` | 不附带物理单位。 |

上述表是数据接口的规范单位。优化模型中的缩放量必须使用 `_mhz`、`_mbps`、`_kj` 后缀或 `scaled_` 前缀，禁止复用 `_hz`、`_bps`、`_j` 字段名保存缩放后的数值。

## 前缀和基本换算

| 展示量 | 转换为内部单位 |
|---|---|
| \(1\ \mathrm{km}\) | \(10^3\ \mathrm{m}\) |
| \(1\ \mathrm{GHz}\) | \(10^9\ \mathrm{Hz}\) |
| \(1\ \mathrm{MHz}\) | \(10^6\ \mathrm{Hz}\) |
| \(1\ \mathrm{kHz}\) | \(10^3\ \mathrm{Hz}\) |
| \(1\ \mathrm{Gbit/s}\) | \(10^9\ \mathrm{bit/s}\) |
| \(1\ \mathrm{Mbit/s}\) | \(10^6\ \mathrm{bit/s}\) |
| \(1\ \mathrm{kbit/s}\) | \(10^3\ \mathrm{bit/s}\) |
| \(1\ \mathrm{Wh}\) | \(3600\ \mathrm{J}\) |
| \(1\ \mathrm{kWh}\) | \(3.6\times10^6\ \mathrm{J}\) |

通信速率采用十进制前缀，即 `Mbit/s = 10^6 bit/s`，不使用二进制的 `Mibit/s`。

## SCIP 线性模型的数值缩放

### 缩放定义

模型构造边界统一定义：

\[
\widetilde b_{ul}=b_{ul}/10^6\quad[\mathrm{MHz}],
\]

\[
\widetilde S_u=S_u/10^6,
\ \widetilde d_u=d_u/10^6,
\ \widetilde q_u=q_u/10^6,
\ \widetilde C_l^{\mathrm{bh}}=C_l^{\mathrm{bh}}/10^6,
\ \widetilde C_G=C_G/10^6
\quad[\mathrm{Mbit/s}],
\]

\[
\widetilde E=E/10^3\quad[\mathrm{kJ}].
\]

频谱效率 \(\eta\) 的数值不变，因为

\[
\eta\ [\mathrm{bit/s/Hz}]\times
\widetilde b\ [\mathrm{MHz}]
=\widetilde r\ [\mathrm{Mbit/s}].
\]

所以缩放后的服务等式仍可写成

\[
\widetilde S_u=\sum_l\eta_{ul}\widetilde b_{ul}.
\]

逐边带宽上界也先在 SI 层计算并验证，再转换为

\[
\widetilde M_{ul}=M_{ul}/10^6\quad[\mathrm{MHz}]
\]

进入约束 \(\widetilde b_{ul}\le\widetilde M_{ul}x_{ul}\)。

### 缩放后的通信能耗系数

当带宽变量以 MHz 建模、能量约束以 kJ 建模时，通信能耗项必须写成

\[
\frac{T(p_A/\xi_{\mathrm{PA}})(10^6\widetilde b)}{10^3}
=1000T\frac{p_A}{\xi_{\mathrm{PA}}}\widetilde b\quad[\mathrm{kJ}].
\]

不得把 SI 公式中的 \(T(p_A/\xi_{\mathrm{PA}})b\) 原样作用于 MHz 数值，否则会产生 \(10^6\) 倍错误。

### 边界转换规则

1. 场景生成器只输出 SI 字段；
2. `model_scaling` 层一次性生成 SCIP 所需缩放字段；
3. SCIP solution 先转换回 SI，再由独立 evaluator 重算物理约束和目标；
4. 原始日志同时保存 SI 值和缩放值的 schema 版本，不依赖显示格式反推；
5. 论文表格从 SI 结果生成，不能直接读取 SCIP 内部缩放列后省略单位。

## 对数量与线性量换算

### 功率与 dBm

\[
P_{\mathrm W}=10^{(P_{\mathrm{dBm}}-30)/10},
\qquad
P_{\mathrm{dBm}}=10\log_{10}(P_{\mathrm W})+30.
\]

其中 \(P_{\mathrm W}\) 是以瓦为单位的线性功率，\(P_{\mathrm{dBm}}\) 是以 1 mW 为参考的 dBm 功率，\(\log_{10}\) 是以 10 为底的对数。

### 增益、损耗、噪声因子和 SINR

\[
g_{\mathrm{lin}}=10^{G_{\mathrm{dB}}/10},
\qquad
G_{\mathrm{dB}}=10\log_{10}(g_{\mathrm{lin}}),
\]

\[
F_{\mathrm{lin}}=10^{NF_{\mathrm{dB}}/10},
\qquad
\gamma_{\mathrm{lin}}=10^{\gamma_{\mathrm{dB}}/10}.
\]

这里 \(g_{\mathrm{lin}}\) 是线性功率增益，\(G_{\mathrm{dB}}\) 是对应的 dB 增益或损耗；\(NF_{\mathrm{dB}}\) 是接收机噪声系数，\(F_{\mathrm{lin}}\) 是线性噪声因子；\(\gamma_{\mathrm{dB}}\) 和 \(\gamma_{\mathrm{lin}}\) 分别是同一 SINR 的 dB 与线性表示。

路径损耗、天线增益、设备损耗和可靠性裕量可以在 dB 域按正负号相加减，得到的净 dB 增益必须再转换成线性增益后才能进入功率或 SINR 公式。

## PSD、带宽、速率与能量

\[
P=p_{\mathrm{PSD}}B,
\qquad
r=\eta B,
\qquad
E=Pt.
\]

其中 \(p_{\mathrm{PSD}}\) 是功率谱密度，单位为 W/Hz；\(B\) 是实际使用带宽，单位为 Hz；\(P\) 是线性功率，单位为 W；\(\eta\) 是频谱效率，单位为 bit/s/Hz；\(r\) 是速率，单位为 bit/s；\(t\) 是持续时间，单位为 s；\(E\) 是能量，单位为 J。

量纲必须分别满足：

- \(\mathrm{W/Hz}\times\mathrm{Hz}=\mathrm W\)；
- \(\mathrm{bit/s/Hz}\times\mathrm{Hz}=\mathrm{bit/s}\)；
- \(\mathrm W\times\mathrm s=\mathrm J\)。

本项目冻结的是天线端口传导 PSD，因此天线增益没有包含在 \(p_{\mathrm{PSD}}\) 中，链路预算仍需单独加入发射天线增益；不得把该 PSD 误写成 EIRP PSD 后再次加入天线增益。

## Shannon 型频谱效率规则

\[
\eta_{\mathrm{eff}}
=\zeta\min\left(\eta_{\max},\log_2\left(1+\frac{\gamma_{\mathrm{lin}}}{\Gamma}\right)\right).
\]

其中 \(\eta_{\mathrm{eff}}\) 是有效净荷频谱效率，单位为 bit/s/Hz；\(\zeta\) 是无量纲净荷比例；\(\eta_{\max}\) 是原始频谱效率上限；\(\gamma_{\mathrm{lin}}\) 是线性 SINR；\(\Gamma\) 是无量纲实现差距因子；\(\log_2\) 是以 2 为底的对数。

禁止把 dB SINR 直接代入该公式；必须先使用 \(\gamma_{\mathrm{lin}}=10^{\gamma_{\mathrm{dB}}/10}\) 转成线性值。

## 角度规则

程序中的二维几何先计算

\[
\theta_{\mathrm{deg}}=\frac{180}{\pi}
\operatorname{atan2}(\Delta h,\rho).
\]

其中 \(\theta_{\mathrm{deg}}\) 是以度为单位的仰角，\(\Delta h\) 是 UAV 与链路另一端的高度差，单位为 m；\(\rho\) 是水平距离，单位为 m；\(\operatorname{atan2}\) 返回弧度；\(\pi\) 是圆周率。得到度数后才能代入当前 Al-Hourani 参数化的 LoS 概率公式。

## 冻结数值的单位自检样例

| 检查 | 结果 |
|---|---:|
| 接入满带宽传导功率：\(5.0\times10^{-8}\ \mathrm{W/Hz}\times20\times10^6\ \mathrm{Hz}\) | \(1\ \mathrm W\) |
| 两块 263.2 Wh 电池：\(2\times263.2\times3600\) | \(1{,}895{,}040\ \mathrm J\) |
| 保留 20% 后可用能量：\(0.8\times1{,}895{,}040\) | \(1{,}516{,}032\ \mathrm J\) |
| 9 dB 噪声系数转线性：\(10^{9/10}\) | \(7.943282347\) |
| 线性 SINR 0.352835 转 dB：\(10\log_{10}(0.352835)\) | 约 \(-4.5243\ \mathrm{dB}\) |
| 固定悬停、基础设备和起降能量：\(30{,}000+1800(600+40)\) | \(1{,}182{,}000\ \mathrm J=1182\ \mathrm{kJ}\) |
| 满 20 MHz 接入通信能量：\(1800(5\times10^{-8}/0.30)(20\times10^6)\) | \(6000\ \mathrm J=6\ \mathrm{kJ}\) |
| 往返巡航距离系数：\(2(550/10)\) | \(110\ \mathrm{J/m}\) |
| 满带宽能量开始可能约束的飞行距离：\((1{,}516{,}032-1{,}182{,}000-6000)/110\) | 约 \(2982\ \mathrm m\) |

## 实现和审计规则

1. YAML 中带单位后缀的数值已经是内部单位，读取后不得再次乘前缀。
2. 场景生成器输出必须在字段名或 schema 中保留单位后缀，禁止使用含义不明的 `distance`、`rate` 或 `power`。
3. 链路与能量预计算只接收线性功率、线性增益、线性 SINR、Hz、bit/s、W 和 J；SCIP 模型只接收经过集中转换的 MHz、Mbit/s 和 kJ 缩放量。dB/dBi/dBm 只在链路预计算和报告边界出现。
4. `null` 表示未设置可选上限；字符串 `none`、数值 0 和 YAML 空值不是同一含义。
5. 浮点比较使用显式容差，不能用字符串格式化后的展示值进行可行性判断。
6. 每次生成数据必须执行量纲断言，至少检查非负距离、概率范围、正带宽、PSD×带宽功率、频谱效率×带宽速率及能量预算。
7. 论文表格可以展示 km、MHz、Mbit/s、Wh 和 dB，但表头必须写明单位，并由内部 SI 值统一转换生成。
8. 每次构造模型必须对至少一个随机边同时用 SI 公式与缩放公式计算服务速率和通信能耗，并断言还原后在容差内一致。
9. 求解完成后必须在 SI 层独立检查全部约束；SCIP 缩放模型可行但 SI 复算失败属于 P0 错误。
10. normalized gap 和 nPDI 是无量纲统计量；墙钟积分在除以统一时限后才称为本项目的无量纲 nPDI。
11. 逐边上界的删边判断统一在 SI 的 Hz 层执行：仅当 `M_ul < b_min - 1 Hz` 时删除；相等或差值不超过 1 Hz 时保留，再把保留边的上界转换成 MHz。
