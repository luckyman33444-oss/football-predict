import pandas as pd, re
from engine import predict_full_dc

df = pd.read_csv('detail.csv')

def parse_xg(s):
    if pd.isna(s): return None, None
    m = re.match(r'([0-9.]+)\s*-\s*([0-9.]+)', str(s))
    if not m: return None, None
    return float(m.group(1)), float(m.group(2))

df[['xg_h','xg_a']] = df['模型xG'].apply(lambda s: pd.Series(parse_xg(s)))

def actual_over(s):
    m = re.match(r'(\d+)\s*[-:]\s*(\d+)', str(s))
    if not m: return None
    return (int(m.group(1)) + int(m.group(2))) >= 3

df['实际大球'] = df['实际比分'].apply(actual_over)
d = df.dropna(subset=['xg_h','xg_a','实际大球']).copy()
print(f"可算样本 {len(d)}\n")

rhos = [-0.05, -0.08, -0.10, -0.13, -0.15, -0.18, -0.20, -0.22, -0.25]

print("=== 全体 ===")
for r in rhos:
    hits = 0
    for _, row in d.iterrows():
        p = predict_full_dc(row['xg_h'], row['xg_a'], rho=r)
        pred_over = p['over25'] >= 0.5
        if pred_over == row['实际大球']: hits += 1
    print(f"  rho {r:+.2f}: {hits}/{len(d)} = {hits/len(d):.4f}")

print("\n=== 按等级 ===")
for g, sub in d.groupby('等级'):
    if len(sub) < 100: continue
    print(f"-- {g} (n={len(sub)}) --")
    best = (None, 0)
    for r in rhos:
        hits = 0
        for _, row in sub.iterrows():
            p = predict_full_dc(row['xg_h'], row['xg_a'], rho=r)
            pred_over = p['over25'] >= 0.5
            if pred_over == row['实际大球']: hits += 1
        rate = hits/len(sub)
        if rate > best[1]: best = (r, rate)
        print(f"  rho {r:+.2f}: {rate:.4f}")
    print(f"  → 最优 rho {best[0]:+.2f} = {best[1]:.4f}")