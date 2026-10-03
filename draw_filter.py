import pandas as pd

df = pd.read_csv('detail.csv')
df = df[df['实际胜平负'].notna()].copy()
act = df['实际胜平负'].astype(str).str.strip()
pred = df['胜平负推荐'].astype(str).str.strip()

for c in ['模型主胜','模型和局','模型客胜']:
    df[c] = pd.to_numeric(df[c], errors='coerce')

print("=== 模型判客胜方向 ===")
sub = df[pred == '客胜'].copy()
sub['和局档'] = pd.cut(sub['模型和局'], bins=[0,15,20,25,30,100], labels=['<15%','15-20%','20-25%','25-30%','30%+'])
print(f"总客胜场次: {len(sub)}")
for b in ['<15%','15-20%','20-25%','25-30%','30%+']:
    s = sub[sub['和局档'] == b]
    if len(s) == 0: continue
    a = s['实际胜平负'].astype(str).str.strip()
    k = (a == '客胜').sum()
    print(f"  {b:8s} n={len(s):4d}  实际客胜 {k:3d} ({k/len(s)*100:5.1f}%)")

print()
print("=== 组合筛选（只看主胜方向） ===")
sub_h = df[pred == '主胜'].copy()
for t in [15, 18, 20, 22, 25, 28, 30]:
    s = sub_h[sub_h['模型和局'] < t]
    if len(s) < 30: continue
    a = s['实际胜平负'].astype(str).str.strip()
    h = (a == '主胜').sum()
    print(f"  和局<{t}%: n={len(s):4d}  主胜命中 {h/len(s)*100:5.1f}%")

print()
print("=== 组合筛选（只看客胜方向） ===")
sub_k = df[pred == '客胜'].copy()
for t in [15, 18, 20, 22, 25, 28, 30]:
    s = sub_k[sub_k['模型和局'] < t]
    if len(s) < 30: continue
    a = s['实际胜平负'].astype(str).str.strip()
    k = (a == '客胜').sum()
    print(f"  和局<{t}%: n={len(s):4d}  客胜命中 {k/len(s)*100:5.1f}%")

print()
print("=== 终极：主客胜合并，只筛'和局<25%' ===")
s = df[(df['模型和局'] < 25) & (df['胜平负推荐'].isin(['主胜','客胜']))]
a = s['实际胜平负'].astype(str).str.strip()
p = s['胜平负推荐'].astype(str).str.strip()
hit = (a == p)
print(f"  总场次: {len(s)}")
print(f"  命中率: {hit.mean()*100:.1f}%")
print(f"  vs 全量方向 49.1%: {hit.mean()*100 - 49.1:+.1f} 点")