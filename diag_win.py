import pandas as pd

df = pd.read_csv('detail.csv')
df = df[df['实际胜平负'].notna()].copy()

# 提取三列概率
df['p_h'] = pd.to_numeric(df['主胜'].astype(str).str.extract(r'(\d+\.?\d*)')[0])
df['p_d'] = pd.to_numeric(df['和局'].astype(str).str.extract(r'(\d+\.?\d*)')[0])
df['p_a'] = pd.to_numeric(df['客胜'].astype(str).str.extract(r'(\d+\.?\d*)')[0])

# "预测结果"从推荐里取
df['pred'] = df['胜平负推荐'].astype(str).str.strip()

# A: 当前推荐的命中
a_hit = (df['pred'] == df['实际胜平负'].astype(str).str.strip())
print(f"A. 当前'胜平负推荐'命中率: {a_hit.mean()*100:.1f}%  (n={len(df)})")

# B: 三列概率里取最大者（禁和局，只看主胜/客胜）
def max_hw_aw(row):
    return '主胜' if row['p_h'] >= row['p_a'] else '客胜'
df['pred_max'] = df.apply(max_hw_aw, axis=1)
b_hit = (df['pred_max'] == df['实际胜平负'].astype(str).str.strip())
print(f"B. '三列概率里主/客最大者'命中率: {b_hit.mean()*100:.1f}%")

# C: 三列概率里取最大者（含和局）
def max_all(row):
    m = max([('主胜',row['p_h']), ('和局',row['p_d']), ('客胜',row['p_a'])], key=lambda x: x[1])
    return m[0]
df['pred_max3'] = df.apply(max_all, axis=1)
c_hit = (df['pred_max3'] == df['实际胜平负'].astype(str).str.strip())
print(f"C. '三列概率全取最大者'命中率: {c_hit.mean()*100:.1f}%")

# 对比
print()
print("=== 结论 ===")
print(f"若 A ≈ B → 回测已经在用融合后的概率（无提升空间）")
print(f"若 A < B → 回测用的是裸模型，融合市场能提升 {b_hit.mean()*100 - a_hit.mean()*100:+.1f} 点")