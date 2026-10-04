import pandas as pd
df = pd.read_csv('detail.csv')

print("=" * 50)
print("【大小球】按市场概率强度分档（市场大小球概率）")
print("=" * 50)
d = df.dropna(subset=['市场大小球命中','市场大小球概率'])
for lo, hi, label in [(50,55,"50-55 弱"),(55,60,"55-60 中"),(60,65,"60-65 强"),(65,101,"65+ 很强")]:
    sub = d[(d['市场大小球概率']>=lo)&(d['市场大小球概率']<hi)]
    s = sub['市场大小球命中'].dropna()
    if len(s): print(f"  {label}: {s.sum()}/{len(s)} = {s.mean():.4f}")
# 对比：同样分档下模型大小球命中
print("  -- 同档模型大小球命中 --")
for lo, hi, label in [(50,55,"50-55"),(55,60,"55-60"),(60,65,"60-65"),(65,101,"65+")]:
    sub = d[(d['市场大小球概率']>=lo)&(d['市场大小球概率']<hi)]
    s = sub['大小球命中'].dropna()
    if len(s): print(f"  {label}: {s.sum()}/{len(s)} = {s.mean():.4f}")

print()
print("=" * 50)
print("【大小球】模型 vs 市场 一致/分歧")
print("=" * 50)
d2 = df.dropna(subset=['市场大小球','大小球推荐'])
d2 = d2.copy()
d2['一致'] = d2['市场大小球'] == d2['大小球推荐']
for flag, g in d2.groupby('一致'):
    s_mk = g['市场大小球命中'].dropna()
    s_md = g['大小球命中'].dropna()
    tag = "一致" if flag else "分歧"
    print(f"  {tag} (n={len(g)}):")
    print(f"     市场: {s_mk.sum()}/{len(s_mk)} = {s_mk.mean():.4f}")
    print(f"     模型: {s_md.sum()}/{len(s_md)} = {s_md.mean():.4f}")

print()
print("=" * 50)
print("【主客和】按市场差(|市场主胜-市场客胜|)分档")
print("=" * 50)
df['市场差'] = (df['市场主胜'] - df['市场客胜']).abs()
for lo, hi, label in [(0,5,"0-5 极弱"),(5,10,"5-10 弱"),(10,20,"10-20 中"),(20,35,"20-35 强"),(35,101,"35+ 很强")]:
    sub = df[(df['市场差']>=lo)&(df['市场差']<hi)]
    s = sub['市场命中'].dropna()
    if len(s): print(f"  {label}: {s.sum()}/{len(s)} = {s.mean():.4f}")

print()
print("=" * 50)
print("【主客和】按市场和局概率分档（已有高置信，再细看）")
print("=" * 50)
for lo, hi, label in [(0,20,"<20"),(20,22,"20-22"),(22,25,"22-25"),(25,30,"25-30"),(30,101,"30+")]:
    sub = df[(df['市场和局']>=lo)&(df['市场和局']<hi)]
    s = sub['市场命中'].dropna()
    if len(s): print(f"  和局{label}: {s.sum()}/{len(s)} = {s.mean():.4f}")