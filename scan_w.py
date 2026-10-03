import pandas as pd

df = pd.read_csv('detail.csv')
df = df[df['实际胜平负'].notna()].copy()
act = df['实际胜平负'].astype(str).str.strip()

# 6 列概率 → 小数
for c in ['模型主胜','模型和局','模型客胜','市场主胜','市场和局','市场客胜']:
    df[c] = pd.to_numeric(df[c], errors='coerce')

def hit_rate(w):
    # w = 模型权重，(1-w) = 市场权重
    mhw = df['模型主胜']/100; md = df['模型和局']/100; maw = df['模型客胜']/100
    khw = df['市场主胜']/100; kd = df['市场和局']/100; kaw = df['市场客胜']/100
    bhw = w*mhw + (1-w)*khw
    bd  = w*md  + (1-w)*kd
    baw = w*maw + (1-w)*kaw
    pred = bhw.ge(baw).map({True:'主胜', False:'客胜'})
    return (pred == act).mean() * 100

print("w=模型权重, 1-w=市场权重")
print("=" * 40)
best_w, best_hr = 0, 0
for w in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
    hr = hit_rate(w)
    mark = ""
    if hr > best_hr: best_hr = hr; best_w = w
    print(f"  w={w:.1f}  →  {hr:.2f}%")
print()
print(f"全局最优: w={best_w:.1f}, 命中 {best_hr:.2f}%")
print()
print("参照: 模型w=1.0 vs 市场w=0.0")
print(f"  纯模型: {hit_rate(1.0):.2f}%")
print(f"  纯市场: {hit_rate(0.0):.2f}%")