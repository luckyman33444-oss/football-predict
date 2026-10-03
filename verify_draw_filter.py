import pandas as pd
import numpy as np

df = pd.read_csv('detail.csv')
df = df[df['实际胜平负'].notna()].copy()
act = df['实际胜平负'].astype(str).str.strip()
pred = df['胜平负推荐'].astype(str).str.strip()
df['actual'] = act

for c in ['模型主胜','模型和局','模型客胜','胜平负概率']:
    df[c] = pd.to_numeric(df[c], errors='coerce')

print("=== CV：和局<25% 筛选是否稳定 ===")
sub = df[df['胜平负推荐'].isin(['主胜','客胜'])].copy().reset_index(drop=True)
np.random.seed(42)
sub['fold'] = np.random.randint(0, 2, len(sub))

for f in [0, 1]:
    test = sub[sub['fold'] == f]
    filt = test[test['模型和局'] < 25]
    hit = (filt['胜平负推荐'].astype(str).str.strip() == filt['actual']).mean() * 100
    print(f"  折{f}: n={len(filt)}  命中 {hit:.1f}%")

print()
print("=== '和局概率低' 和 '胜平负概率高' 是不是同一个信号 ===")
sub2 = df[df['胜平负推荐'].isin(['主胜','客胜'])].copy()
sub2['和局档'] = pd.cut(sub2['模型和局'], bins=[0,20,25,30,100], labels=['<20','20-25','25-30','30+'])
sub2['胜率档'] = pd.cut(sub2['胜平负概率'], bins=[0,55,60,65,70,100], labels=['<55','55-60','60-65','65-70','70+'])

cols = ['<55','55-60','60-65','65-70','70+']
print("和局vs胜率".ljust(10) + "".join(c.rjust(9) for c in cols))
for d in ['<20','20-25','25-30','30+']:
    row = d.ljust(10)
    for s in cols:
        x = sub2[(sub2['和局档']==d) & (sub2['胜率档']==s)]
        if len(x) < 5:
            row += "—".rjust(9)
        else:
            h = (x['胜平负推荐'].astype(str).str.strip() == x['actual']).mean() * 100
            row += f"{h:.1f}%".rjust(9)
    print(row)

print()
print("=== 叠加筛选 ===")
conds = [
    ((sub2['模型和局']<25), "和局<25%"),
    ((sub2['胜平负概率']>=65), "胜率>=65%"),
    ((sub2['模型和局']<25) & (sub2['胜平负概率']>=65), "和局<25% AND 胜率>=65%"),
    ((sub2['模型和局']<25) | (sub2['胜平负概率']>=65), "和局<25% OR 胜率>=65%"),
]
for cond, name in conds:
    x = sub2[cond]
    if len(x) < 30:
        print(f"  {name:40s} n={len(x):4d}  (样本太小)")
        continue
    h = (x['胜平负推荐'].astype(str).str.strip() == x['actual']).mean() * 100
    print(f"  {name:40s} n={len(x):4d}  命中 {h:.1f}%")