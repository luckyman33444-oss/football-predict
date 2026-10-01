import pandas as pd
from collections import Counter

df = pd.read_csv('detail.csv')
df = df[df['前3候选'].notna()].copy()

def parse(s):
    out = []
    for x in str(s).split(','):
        if '-' in x:
            a, b = x.strip().split('-')
            try: out.append((int(a), int(b)))
            except: pass
    return out

def total_goals(s):
    if '-' in str(s):
        a, b = str(s).split('-')
        try: return int(a) + int(b)
        except: return None

cand = Counter()
for s in df['前3候选']:
    for a, b in parse(s):
        cand[a + b] += 1

df['g'] = df['实际比分'].apply(total_goals)
actual = df['g'].value_counts(normalize=True)

tot = sum(cand.values())
print("总进球 | 模型候选权重 | 实际占比")
print("-" * 35)
for g in range(0, 8):
    c = cand.get(g, 0) / tot * 100
    a = actual.get(g, 0) * 100
    print(f"  {g}球  |    {c:5.1f}%    |  {a:5.1f}%")