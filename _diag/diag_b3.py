import pandas as pd
df = pd.read_csv('detail.csv')
df = df[df['前3候选'].notna()].copy()
df['hit'] = (df['前3命中'].astype(str).str.strip() == '✅')
df['rec'] = df['大小球推荐'].astype(str)

print("=== 按大小球推荐方向拆 ===")
for r in ['大球','小球']:
    sub = df[df['rec'].str.contains(r)]
    print(f"  {r}: {len(sub)}场  前3命中 {sub['hit'].mean()*100:.1f}%")

# 大球场次：实际比分 top10
print()
print("=== 判'大球'场次，实际比分 top10 ===")
d = df[df['rec'].str.contains('大球')]
print(d['实际比分'].value_counts().head(10).to_string())

print()
print("=== 判'小球'场次，实际比分 top10 ===")
d = df[df['rec'].str.contains('小球')]
print(d['实际比分'].value_counts().head(10).to_string())