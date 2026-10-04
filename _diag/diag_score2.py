import pandas as pd, re

df = pd.read_csv('detail.csv')

def actual(s):
    m = re.match(r'(\d+)\s*[-:]\s*(\d+)', str(s))
    return f"{int(m.group(1))}-{int(m.group(2))}" if m else None
df['实际'] = df['实际比分'].apply(actual)

print("=== 实际比分 top20 ===")
print(df['实际'].value_counts().head(20).to_dict())

print("\n=== 模型主力比分 top10 ===")
print(df['主力比分'].value_counts().head(10).to_dict())

df['主力中'] = df['主力比分'] == df['实际']
df['备选中'] = df['备选比分'] == df['实际']
df['任一中'] = df['主力中'] | df['备选中']

def in_top3(r):
    if pd.isna(r['前3候选']) or pd.isna(r['实际']): return None
    return r['实际'] in str(r['前3候选']).split(',')
df['前3中'] = df.apply(in_top3, axis=1)

for col, name in [('主力中','主力'),('备选中','备选'),('任一中','主力或备选'),('前3中','前3候选')]:
    s = df[col].dropna()
    print(f"{name}: {s.sum()}/{len(s)} = {s.mean()*100:.1f}%")

print("\n=== 主力命中 vs 大小球方向对错 ===")
for flag, g in df.groupby('大小球命中'):
    s = g['主力中'].dropna()
    print(f"  大小球{'对' if flag else '错'}: 主力命中 {s.mean()*100:.1f}% (n={len(s)})")

print("\n=== 主力命中 vs 胜平负方向对错 ===")
for flag, g in df.groupby('胜平负命中'):
    s = g['主力中'].dropna()
    print(f"  胜平负{'对' if flag else '错'}: 主力命中 {s.mean()*100:.1f}% (n={len(s)})")

print("\n=== 前3候选 命中 vs 大小球方向 ===")
for flag, g in df.groupby('大小球命中'):
    s = g['前3中'].dropna()
    print(f"  大小球{'对' if flag else '错'}: 前3命中 {s.mean()*100:.1f}% (n={len(s)})")