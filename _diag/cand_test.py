import pandas as pd
df = pd.read_csv('detail.csv')
df = df[df['前3候选'].notna() & df['实际比分'].notna()].copy()

def parse(s):
    out = []
    for x in str(s).split(','):
        if '-' in x:
            out.append(x.strip())
    return out

cands = df['前3候选'].apply(parse)
actual = df['实际比分'].astype(str).str.strip()

def hit(scores):
    return [a in s for a, s in zip(actual, scores)]

# 各种候选方案
schemes = {
    "当前前3（first 3）":        cands.apply(lambda x: x[:3]),
    "当前前4（全部4个）":         cands.apply(lambda x: x[:4]),
    "前3 + 1-1":               cands.apply(lambda x: x[:3] + (['1-1'] if '1-1' not in x[:3] else [])),
    "前3 + 1-1, 1-0":          cands.apply(lambda x: x[:3] + [s for s in ['1-1','1-0'] if s not in x[:3]]),
    "前3 + 1-1, 1-0, 0-1":     cands.apply(lambda x: x[:3] + [s for s in ['1-1','1-0','0-1'] if s not in x[:3]]),
    "前3 + 1-1, 1-0, 0-1, 0-0":cands.apply(lambda x: x[:3] + [s for s in ['1-1','1-0','0-1','0-0'] if s not in x[:3]]),
    "固定输出 top5 {1-1,1-0,2-1,0-1,0-0}": actual.apply(lambda _: ['1-1','1-0','2-1','0-1','0-0']),
}

print(f"总场次: {len(df)}\n")
print(f"{'方案':40s}  候选数  命中率")
print("-" * 60)
for name, s in schemes.items():
    hits = hit(s)
    n_cand = sum(len(x) for x in s) / len(s)
    print(f"{name:40s}  {n_cand:.1f}    {sum(hits)/len(hits)*100:5.1f}%")