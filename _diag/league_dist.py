import pandas as pd
df = pd.read_csv('detail.csv')
df = df[df['实际比分'].notna()].copy()
df['实际比分'] = df['实际比分'].astype(str).str.strip()

# 1) 按标签看
print("=" * 60)
print("按联赛标签分组，实际比分 top8")
print("=" * 60)
for lvl in ['S', 'A', 'B', 'F']:
    sub = df[df['等级'] == lvl]
    if len(sub) == 0: continue
    print(f"\n【等级 {lvl}】 n={len(sub)}")
    top = sub['实际比分'].value_counts().head(8)
    for score, cnt in top.items():
        print(f"  {score:6s} {cnt:4d}  {cnt/len(sub)*100:5.1f}%")

# 2) 按精选/避雷看（用联赛名匹配）
print()
print("=" * 60)
print("精选 vs 避雷 联赛，实际比分 top8")
print("=" * 60)
SELECTED = ['意甲','日职联','Pro League','Parva Liga','Superliga','尼日利亚超']
BLACK = ['阿甲','英冠','哥伦比亚甲','Liga Portugal 2','Copa Libertadores','摩洛哥甲']
def tag(name):
    n = str(name)
    if any(x in n for x in SELECTED): return '精选'
    if any(x in n for x in BLACK): return '避雷'
    return '普通'
df['tag'] = df['联赛'].apply(tag)

for t in ['精选','普通','避雷']:
    sub = df[df['tag'] == t]
    print(f"\n【{t}】 n={len(sub)}")
    top = sub['实际比分'].value_counts().head(8)
    for score, cnt in top.items():
        print(f"  {score:6s} {cnt:4d}  {cnt/len(sub)*100:5.1f}%")

# 3) 每个具体联赛的样本量（过滤样本 < 30 的）
print()
print("=" * 60)
print("各联赛样本量（只列 n>=30）")
print("=" * 60)
vc = df['联赛'].value_counts()
for lg, cnt in vc.items():
    if cnt >= 30:
        print(f"  {lg:30s} {cnt}")