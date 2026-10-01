import pandas as pd

df = pd.read_csv('detail.csv')
df = df[df['前3候选'].notna() & df['实际比分'].notna()].copy()
actual = df['实际比分'].astype(str).str.strip()

def goals(s):
    if '-' in s:
        a, b = s.split('-')
        try: return int(a) + int(b)
        except: return None
    return None

df['ag'] = actual.apply(goals)
LOW  = ['1-1','1-0','0-1','0-0','2-0']
HIGH = ['2-1','1-2','2-2','3-1','3-0']
FIX5 = ['1-1','1-0','2-1','0-1','0-0']

def parse(s):
    return [x.strip() for x in str(s).split(',') if '-' in x]

cand_model = df['前3候选'].apply(lambda s: parse(s)[:4])
cand_cond  = df.apply(lambda r: HIGH if '大球' in str(r['大小球推荐']) else LOW, axis=1)
cand_orcl  = df.apply(lambda r: HIGH if r['ag']>=3 else LOW, axis=1)
cand_fix   = actual.apply(lambda _: FIX5)

def score(c):
    h = [a in cc for a, cc in zip(actual, c)]
    n = sum(len(x) for x in c)/len(c)
    return sum(h)/len(h)*100, n

print(f"{'方案':26s}  候选数  命中率")
print("-"*48)
for name, c in [('模型前4', cand_model),
                ('条件候选(模型大小球)', cand_cond),
                ('条件候选(完美大小球)', cand_orcl),
                ('固定top5', cand_fix)]:
    hr, nc = score(c)
    print(f"{name:26s}  {nc:.1f}   {hr:5.1f}%")