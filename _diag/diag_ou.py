import pandas as pd
df = pd.read_csv('detail.csv')

print("=== 大小球整体 ===")
s = df['大小球命中'].dropna()
print(f"  {s.sum()}/{len(s)} = {s.mean():.4f}")

print("\n=== 按等级 ===")
for g, sub in df.groupby('等级'):
    s = sub['大小球命中'].dropna()
    if len(s) >= 30: print(f"  {g}: {s.sum()}/{len(s)} = {s.mean():.4f}")

print("\n=== 按推荐方向 ===")
for d, sub in df.groupby('大小球推荐'):
    s = sub['大小球命中'].dropna()
    if len(s) >= 30: print(f"  {d}: {s.sum()}/{len(s)} = {s.mean():.4f}")

print("\n=== 按联赛(样本>80) ===")
for lg, sub in df.groupby('联赛'):
    s = sub['大小球命中'].dropna()
    if len(s) >= 80: print(f"  {lg}: {s.sum()}/{len(s)} = {s.mean():.4f}")