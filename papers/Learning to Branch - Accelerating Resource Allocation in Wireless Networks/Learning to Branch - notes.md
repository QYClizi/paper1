# Learning to Branch: Accelerating Resource Allocation in Wireless Networks
Lee, Yu, Li — IEEE TVT, Vol.69 No.1, Jan. 2020

---

## Q1. "B&B ... converges slowly and has forbidding complexity for real-time implementation" 是什么意思

- **converges slowly**：B&B 要展开大量节点、迭代很多次，上下界才收敛。时间主要不是花在"找到"最优解，而是花在"**证明**它最优"（搜完/剪掉其余所有解）。
- **forbidding complexity**：`forbidding` = 令人望而却步的（不是"禁止"）。本文中 B&B 最坏复杂度为**指数级 O(2^(KL))**，K=蜂窝用户数，L=D2D 对数。
- **for real-time implementation**：无线资源分配要跟着 CSI 实时重算，信道相干时间在毫秒级；B&B 算完时信道已变，结果作废。
- 合起来：**B&B 能给全局最优，但收敛慢 + 指数复杂度，实际无线系统里用不了** —— 这是全文动机起点。

---

## Q2. "we use imitation learning method to accelerate the B&B algorithm" 中 imitation learning 是什么

- **定义**：让学习器模仿一个专家（**oracle**）的动作，以**监督学习**的方式达到最优表现。
- **oracle 从哪来**：把 B&B 离线完整跑一遍，回头看就知道每个节点该 branch（在最优路径上，标 1）还是 prune（标 0）⇒ 标签自动可得。
- **本质**：把离线算出的最优决策**蒸馏进一个轻量分类器**；在线只做一次前向，所以快。动作空间只有 {prune, branch} ⇒ 直接变成**二分类**（本文用 SVM）。
- **为何不用 RL**：模仿学习的最优策略**已知**（oracle 给得出），RL 的最优策略未知、要试错探索。原文：*"Imitation learning better fits accelerating the B&B algorithm than reinforcement learning."*

---

## Q3. SVM 是什么

- **Support Vector Machine（支持向量机）**，经典的**监督式二分类器**。
- **核心思想**：在特征空间里找一个**超平面**把两类样本分开，并让**间隔（margin，到最近样本的距离）最大**。原文：*"find a mapping of training examples so that they can be divided by a clear gap that is as wide as possible."*
- **支持向量**：离超平面最近、真正决定超平面位置的那几个样本；其余样本移动不影响结果 ⇒ 模型只由少数样本确定，**小样本下也稳**。
- **核技巧（kernel trick）**：线性不可分时，用核函数把样本映射到高维空间再找超平面。
- **本文用它**：8 维特征向量 → 判 branch(1) / prune(0)。选它是因为特征维度低、样本量不大、要求推理极快；实现用 **LIBSVM**。

---

## Q4. 摘要句解读："With invariant problem-independent features and appropriate problem-dependent feature selection for D2D, a good auxiliary prune policy can be learned in a supervised manner to speed up the most time-consuming branch process."

这是全文方法的**一句话总纲**，拆成四块：

- **invariant problem-independent features（不变的问题无关特征）**：只看 B&B 二叉树本身的结构，对任何 MINLP 都通用、不随应用换、无需重新设计（沿用 [20]）。共 6 个 —— 节点特征（节点深度、plunge depth、局部上界 b_U^n）、分支特征（分支变量的值）、树特征（全局下界 b_L、已获得解的个数）。
- **problem-dependent feature selection for D2D（针对 D2D 挑的问题相关特征）**：从原问题里找关键参数 = **CSI** 和 **功率约束**，各设计 1 个 —— CSI 特征 f(CSI)、功率特征 g(p_kl)。**6 + 2 = 8 维输入向量**。
- **两类特征都做了归一化 ⇒ size-independent**：含 bound 的除以根节点上界，含 depth 的除以树最大深度，CSI 除以 R_min^C，功率除以平均值。目的是让特征**不依赖 CU 数 K 和 D2D 对数 L**，从而在一种规模上学到的策略能迁移到别的规模（**泛化能力**）。
- **learned in a supervised manner**：oracle 提供标签 → SVM 二分类 → 得到 auxiliary prune policy。
- **speed up the most time-consuming branch process**：B&B 最耗时的就是不断分支展开树；剪掉的节点越多，时间越短。注意加速的是**分支/搜索过程**，不是每个节点的求解。

> 一句话：**用一组"跟问题规模无关"的特征把节点状态编码成 8 维向量，监督训练出一个剪枝分类器，去砍掉 B&B 最费时的树搜索。**

---

## 待办 / 疑问

- [ ] plunge depth 的定义
- [ ] 加权：ω1（按深度指数衰减，A=5,B=2.68）× ω2（最优节点加权 1/2/4/8）—— 细节待看
- [ ] 混合训练策略（mixed training）具体怎么混
- [ ] DNN 新损失函数如何动态控制"最优性 vs 复杂度"
