import pandas as pd

df = pd.read_csv('detail.csv')
df = df[df['实际胜平负'].notna()].copy()
df = df[df['胜平负推荐'].isin(['主胜','客胜'])].copy()

for c in ['市场和局','市场主胜','市场客胜']:
    df[c] = pd.to_numeric(df[c], errors='coerce')

df['market_dir'] = df.apply(lambda r: '主胜' if r['市场主胜'] >= r['市场客胜'] else '客胜', axis=1)
df['hit'] = (df['market_dir'] == df['实际胜平负'].astype(str).str.strip())

# 每天大约多少场
df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
n_days = df['日期'].nunique() if df['日期'].notna().any() else 90  # 默认 3 个月
print(f"回测跨度: {n_days} 天\n")

print(f"{'阈值':8s} {'总场次':6s} {'每天':6s} {'命中':8s}")
print("-" * 35)
for t in [18, 20, 22, 25, 28]:
    sub = df[df['市场和局'] < t]
    if len(sub) == 0: continue
    per_day = len(sub) / n_days
    print(f"<{t}%     {len(sub):5d}   {per_day:.1f}   {sub['hit'].mean()*100:5.1f}%")