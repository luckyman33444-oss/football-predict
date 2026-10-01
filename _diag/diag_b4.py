import pandas as pd
df = pd.read_csv('detail.csv')
df = df[df['前3候选'].notna() & df['实际比分'].notna()].copy()
actual = df['实际比分'].astype(str).str.strip()

# 全局常见比分，按频率降序
GLOBAL = ['1-1','1-0','2-1','0-1','0-0','2-0','1-2','2-2','0-2','3-1']

def score(fixed):
    n_hit = actual.isin(fixed).sum()
    return n_hit / len(actual) * 100, len(fixed)

print("方案                           候选数  命中率")
print("-" * 50)

# 方案1: 固定输出 GLOBAL 的前 N 个
for n in [3,4,5,6,7,8,9,10]:
    hr, nc = score(GLOBAL[:n])
    print(f"固定 top{n:<2d} 全局比分                   {nc}      {hr:5.1f}%")

print()
# 方案2: 当前 A 方案（从 detail.csv 里的前3候选读）
cur = df['前3候选'].astype(str).str.split(',')
cur_hit = [a in c for a, c in zip(actual, cur)]
cur_n = sum(len(c) for c in cur) / len(cur)
print(f"当前 A 方案（动态4-7个）         {cur_n:.1f}    {sum(cur_hit)/len(cur_hit)*100:5.1f}%")

print()
# 方案3: 模型前3 ∪ 全局 top5（去掉大小球判断）
def merge5(row):
    m = [x.strip() for x in str(row['前3候选']).split(',')[:3]]
    for g in ['1-1','1-0','2-1','0-1','0-0']:
        if g not in m: m.append(g)
    return m
m3 = df.apply(merge5, axis=1)
h3 = [a in c for a, c in zip(actual, m3)]
n3 = sum(len(c) for c in m3) / len(m3)
print(f"模型前3 ∪ 全局top5               {n3:.1f}    {sum(h3)/len(h3)*100:5.1f}%")

print()
# 方案4: 模型前3 ∪ 全局 top8
def merge8(row):
    m = [x.strip() for x in str(row['前3候选']).split(',')[:3]]
    for g in GLOBAL[:8]:
        if g not in m: m.append(g)
    return m
m4 = df.apply(merge8, axis=1)
h4 = [a in c for a, c in zip(actual, m4)]
n4 = sum(len(c) for c in m4) / len(m4)
print(f"模型前3 ∪ 全局top8               {n4:.1f}    {sum(h4)/len(h4)*100:5.1f}%")