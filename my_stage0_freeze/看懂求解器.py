# -*- coding: utf-8 -*-
"""
边跑边讲：把分支定界的主循环打印出来。
运行：python 看懂求解器.py
需要：pip install pyscipopt
"""
from pyscipopt import Model, Branchrule, Nodesel, SCIP_RESULT, SCIP_PARAMSETTING
import random

# ============================================================
# 一个自定义"分支规则"。SCIP 每次走到第 ④ 步就会来调用它。
# 我们在里面把当前节点的情况打印出来，然后把决定权还给 SCIP。
# ============================================================
class 讲解员(Branchrule):
    def __init__(self):
        self.第几次 = 0

    def branchexeclp(self, allowaddcons):
        self.第几次 += 1
        m = self.model

        # ---- 第 ① 步的结果：SCIP 已经替我们挑好了当前节点 ----
        节点 = m.getCurrentNode()
        编号 = 节点.getNumber()
        深度 = 节点.getDepth()

        # ---- 第 ② 步的结果：这个节点的松弛（LP）已经解完了 ----
        lp目标 = m.getLPObjVal()      # 本节点的界
        全局上界 = m.getDualbound()    # 整棵树目前的上界
        全局下界 = m.getPrimalbound()  # 目前找到的最好可行解

        # ---- 第 ④ 步的输入：哪些变量还是小数 ----
        候选, 取值, 小数部分, n全部, n优先, n隐含 = m.getLPBranchCands()

        print(f"\n{'='*64}")
        print(f"第 {self.第几次} 次被调用   |   节点编号 {编号}   深度 {深度}")
        print(f"{'-'*64}")
        叶, 子, 兄 = m.getOpenNodes()
        待办 = len(叶) + len(子) + len(兄)
        print(f"① 挑节点   : SCIP 挑了 {编号} 号节点（待办清单里还剩 {待办} 个）")
        print(f"② 解松弛   : 本节点 LP 目标值 = {lp目标:.4f}")
        print(f"             全局上界(还能多好) = {全局上界:.4f}")
        print(f"             全局下界(已经拿到) = {全局下界:.4f}")
        if abs(全局上界) < 1e18 and abs(全局下界) < 1e18:
            print(f"             gap = 上界 - 下界 = {abs(全局上界-全局下界):.4f}")
        print(f"③ 剪不剪   : 没剪。因为还有 {n优先} 个变量是小数，且界不比现有解差")
        print(f"④ 劈哪个   : 小数变量（= 合法的分支候选）:")
        for v, 值 in list(zip(候选, 取值))[:n优先][:6]:
            print(f"                {v.name:<10} = {值:.4f}   ← 卡在 0 和 1 中间")
        if n优先 > 6:
            print(f"                ...（共 {n优先} 个）")
        print(f"             → 交回给 SCIP，让它按默认规则挑一个")

        # 把决定权还给 SCIP 的默认规则（我们只是旁观，不干预）
        return {"result": SCIP_RESULT.DIDNOTRUN}


# ============================================================
# 造一个小 MILP：从 12 个物品里挑，装进两个背包
# ============================================================
random.seed(3)
m = Model()
n = 12
价值 = [random.randint(10, 40) for _ in range(n)]
重量 = [random.randint(5, 20) for _ in range(n)]
体积 = [random.randint(5, 20) for _ in range(n)]

x = [m.addVar(vtype="B", name=f"x{i}") for i in range(n)]
m.addCons(sum(重量[i]*x[i] for i in range(n)) <= sum(重量)//3)
m.addCons(sum(体积[i]*x[i] for i in range(n)) <= sum(体积)//3)
m.setObjective(sum(价值[i]*x[i] for i in range(n)), "maximize")

# 关掉 presolve / 割平面 / 启发式，让主循环干干净净地暴露出来
m.setPresolve(SCIP_PARAMSETTING.OFF)
m.setSeparating(SCIP_PARAMSETTING.OFF)
m.setHeuristics(SCIP_PARAMSETTING.OFF)
m.hideOutput()

m.includeBranchrule(讲解员(), "讲解员", "旁观并解说",
                    priority=536870911, maxdepth=-1, maxbounddist=1.0)

print("题目：12 个物品，两个容量限制，最大化总价值")
print("（presolve / 割平面 / 启发式 全部关掉，只留主循环）")
m.optimize()

print(f"\n{'='*64}")
print("跑完了")
print(f"{'='*64}")
print(f"最优值      : {m.getObjVal():.0f}")
print(f"选中的物品  : {[i for i in range(n) if m.getVal(x[i]) > 0.5]}")
print(f"一共开了    : {m.getNNodes()} 个节点")
print("\n要点：")
print("  · 每一次『第 ④ 步』就是一次分支决策 —— 这就是你要用 GNN 替换的地方")
print("  · 『劈哪个』不影响最终答案，只影响要劈多少次 → 所以不会丢最优性")
print("  · 『第 ③ 步剪不剪』才会丢最优性 → Lee 等 2020 学的是那一步")
