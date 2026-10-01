import pandas as pd
df = pd.read_csv('detail.csv')
df = df[df['实际比分'].notna()].copy()
df['实际比分'] = df['实际比分'].astype(str).str.strip()

GLOBAL8 = ['1-1','1-0','2-1','0-1','0-0','2-0','1-2','2-2']

def top8(sub):
    return list(sub['实际比分'].value_counts().head(8).index)

def hit_rate(sub, pool):
    return sub['实际比分'].isin(pool).mean() * 100

print("=== 按等级分池 vs 全局池 ===")
for lvl in ['S','A','B','F']:
    sub = df[df['等级'] == lvl]
    own = top8(sub)
    h_own = hit_rate(sub, own)
    h_glo = hit_rate(sub, GLOBAL8)
    print(f"  {lvl} (n={len(sub)}): 自己池 {h_own:.1f}%  全局池 {h_glo:.1f}%  差 {h_own-h_glo:+.1f}")
    if h_own - h_glo > 0.5:
        extra = [s for s in own if s not in GLOBAL8]
        miss  = [s for s in GLOBAL8 if s not in own]
        print(f"      + 加入: {extra}")
        print(f"      - 移除: {miss}")

print()
print("=== 按精选/普通/避雷 vs 全局池 ===")
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
    own = top8(sub)
    h_own = hit_rate(sub, own)
    h_glo = hit_rate(sub, GLOBAL8)
    print(f"  {t} (n={len(sub)}): 自己池 {h_own:.1f}%  全局池 {h_glo:.1f}%  差 {h_own-h_glo:+.1f}")
    if h_own - h_glo > 0.5:
        extra = [s for s in own if s not in GLOBAL8]
        miss  = [s for s in GLOBAL8 if s not in own]
        print(f"      + 加入: {extra}")
        print(f"      - 移除: {miss}")