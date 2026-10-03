import pandas as pd
import numpy as np

df = pd.read_csv('detail.csv')
df = df[df['实际胜平负'].notna()].copy()
df = df[df['胜平负推荐'].isin(['主胜','客胜'])].copy()

for c in ['市场主胜','市场和局','市场客胜']:
    df[c] = pd.to_numeric(df[c], errors='coerce')

df['market_dir'] = df.apply(lambda r: '主胜' if r['市场主胜'] >= r['市场客胜'] else '客胜', axis=1)
df['hit'] = (df['market_dir'] == df['实际胜平负'].astype(str).str.strip())

np.random.seed(42)
df['fold'] = np.random.randint(0, 2, len(df))

print("=== CV：市场和局筛选 是否稳定 ===")
for t in [20, 22, 25]:
    print(f"\n--- 阈值 <{t}% ---")
    for f in [0, 1]:
        test = df[df['fold'] == f]
        sub = test[test['市场和局'] < t]
        if len(sub) < 30:
            print(f"  折{f}: n={len(sub)} (样本小)")
            continue
        print(f"  折{f}: n={len(sub):4d}  命中 {sub['hit'].mean()*100:.1f}%")

print()
print("=== 和局<22% 各联赛是否稳定 ===")
for lg in df['联赛'].value_counts().index[:10]:
    sub_all = df[df['联赛'] == lg]
    if len(sub_all) < 100: continue
    sub = sub_all[sub_all['市场和局'] < 22]
    if len(sub) < 20: continue
    print(f"  {lg:25s} 筛选后 n={len(sub):4d}  命中 {sub['hit'].mean()*100:.1f}%")