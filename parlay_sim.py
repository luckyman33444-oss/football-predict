import pandas as pd
import numpy as np

df = pd.read_csv("detail.csv")
df = df[df["前3命中"].notna()].reset_index(drop=True)

exc = {"阿甲", "英冠", "哥伦比亚甲", "Liga Portugal 2", "Copa Libertadores", "摩洛哥甲"}
df = df[~df["联赛"].isin(exc)].reset_index(drop=True)

PER_DAY = 43
n_days = len(df) // PER_DAY
BET = 25
N_SIM = 100

def parse_top3(s):
    if pd.isna(s): return []
    return [x.strip() for x in str(s).split(",")]

df["_top3"] = df["前3候选"].map(parse_top3)

def which_candidate(row):
    actual = str(row["实际比分"]).strip()
    for i, c in enumerate(row["_top3"]):
        if c == actual:
            return i
    return -1

df["_which"] = df.apply(which_candidate, axis=1)

print("=== 每场实际命中第几候选 ===")
vc = df["_which"].value_counts().sort_index()
for k, v in vc.items():
    label = {0: "第1候选", 1: "第2候选", 2: "第3候选", -1: "全错"}.get(k, str(k))
    print(f"  {label}: {v}场 ({v/len(df):.1%})")

np.random.seed(42)
hitsA = hitsB = hitsC = 0
costA = costB = costC = 0

for sim in range(N_SIM):
    for d in range(n_days):
        pool = np.arange(d*PER_DAY, (d+1)*PER_DAY)
        picks = np.random.choice(pool, size=3, replace=False)

        # A：前3候选，27注全买
        costA += 27 * BET
        if all(df.iloc[i]["_which"] >= 0 for i in picks):
            hitsA += 1

        # B：前2候选，8注
        costB += 8 * BET
        if all(0 <= df.iloc[i]["_which"] <= 1 for i in picks):
            hitsB += 1

        # C：前3候选，27注里随机挑8注
        costC += 8 * BET
        if all(df.iloc[i]["_which"] >= 0 for i in picks):
            if np.random.random() < 8/27:
                hitsC += 1

total_periods = n_days * N_SIM

print()
print("=== 三方案对比（100 次模拟，每期随机选 3 场）===")
print(f"总期数: {total_periods}")
print()
print(f"A. 前3候选 27注全买:")
print(f"   中奖: {hitsA} 期 ({hitsA/total_periods:.2%})")
print(f"   单期成本: {27*BET} 元, 平均 {total_periods/hitsA:.1f} 期中一次" if hitsA else "   0中")
print()
print(f"B. 前2候选 8注:")
print(f"   中奖: {hitsB} 期 ({hitsB/total_periods:.2%})")
print(f"   单期成本: {8*BET} 元, 平均 {total_periods/hitsB:.1f} 期中一次" if hitsB else "   0中")
print()
print(f"C. 前3候选 随机挑8注:")
print(f"   中奖: {hitsC} 期 ({hitsC/total_periods:.2%})")
print(f"   单期成本: {8*BET} 元, 平均 {total_periods/hitsC:.1f} 期中一次" if hitsC else "   0中")