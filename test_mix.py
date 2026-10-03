import pandas as pd

df = pd.read_csv('detail.csv')
df = df[df['实际胜平负'].notna()].copy()
act = df['实际胜平负'].astype(str).str.strip()
df['actual'] = act

for c in ['模型主胜','模型和局','模型客胜','市场主胜','市场和局','市场客胜']:
    df[c] = pd.to_numeric(df[c], errors='coerce')

def hit_rate(sub, pred_col):
    p = sub[pred_col].astype(str).str.strip()
    return (p == sub['actual']).mean() * 100

# 只看主客胜方向（模型判和局的不计）
df2 = df[df['胜平负推荐'].isin(['主胜','客胜'])].copy()
df2['市场方向'] = df2.apply(lambda r: '主胜' if r['市场主胜'] >= r['市场客胜'] else '客胜', axis=1)

print("=== 全量方向对比 ===")
print(f"  模型方向: {hit_rate(df2, '胜平负推荐'):.1f}%  (n={len(df2)})")
print(f"  市场方向: {hit_rate(df2, '市场方向'):.1f}%  (n={len(df2)})")

print()
print("=== 筛选：模型和局<25% ===")
f = df2[df2['模型和局'] < 25]
print(f"  场次: {len(f)}")
print(f"  模型方向命中: {hit_rate(f, '胜平负推荐'):.1f}%")
print(f"  市场方向命中: {hit_rate(f, '市场方向'):.1f}%")

print()
print("=== 筛选：市场和局<25%（用市场概率筛） ===")
f2 = df2[df2['市场和局'] < 25]
print(f"  场次: {len(f2)}")
print(f"  模型方向命中: {hit_rate(f2, '胜平负推荐'):.1f}%")
print(f"  市场方向命中: {hit_rate(f2, '市场方向'):.1f}%")

print()
print("=== 筛选：模型和局<25% AND 市场和局<25% ===")
f3 = df2[(df2['模型和局'] < 25) & (df2['市场和局'] < 25)]
print(f"  场次: {len(f3)}")
print(f"  模型方向命中: {hit_rate(f3, '胜平负推荐'):.1f}%")
print(f"  市场方向命中: {hit_rate(f3, '市场方向'):.1f}%")

print()
print("=== 试几个不同市场阈值 ===")
for t in [20, 22, 25, 28, 30]:
    f4 = df2[df2['市场和局'] < t]
    print(f"  市场和局<{t}%: n={len(f4):4d}  市场方向 {hit_rate(f4, '市场方向'):.1f}%  模型方向 {hit_rate(f4, '胜平负推荐'):.1f}%")