import pandas as pd, re
from engine import predict_full_dc

df = pd.read_csv('detail.csv')

def parse_xg(s):
    m = re.match(r'([0-9.]+)\s*-\s*([0-9.]+)', str(s))
    return (float(m.group(1)), float(m.group(2))) if m else (None, None)
def actual(s):
    m = re.match(r'(\d+)\s*[-:]\s*(\d+)', str(s))
    return (int(m.group(1)), int(m.group(2))) if m else None

df[['xg_h','xg_a']] = df['模型xG'].apply(lambda s: pd.Series(parse_xg(s)))
df['实际'] = df['实际比分'].apply(actual)
d = df.dropna(subset=['xg_h','xg_a','实际']).copy()
n = len(d)
print(f"样本 {n}\n")

# 当前
cur_main = (df['主力比分'].apply(lambda s: actual(s)) == df['实际']).sum()
cur_alt = (df['备选比分'].apply(lambda s: actual(s)) == df['实际']).sum()
print(f"当前 主力命中: {cur_main}/{n} = {cur_main/n*100:.1f}%")
print(f"当前 备选命中: {cur_alt}/{n} = {cur_alt/n*100:.1f}%")

# 全局 top1/top2/top3
hit1 = hit2 = hit3 = 0
for _, r in d.iterrows():
    p = predict_full_dc(r['xg_h'], r['xg_a'], rho=-0.13)
    allsc = {}
    for h,a,pr in (p.get('over_scores',[]) + p.get('under_scores',[])):
        allsc[(h,a)] = max(allsc.get((h,a),0), pr)
    ranked = [k for k,_ in sorted(allsc.items(), key=lambda x: -x[1])]
    act = r['实际']
    if len(ranked)>=1 and act==ranked[0]: hit1 += 1
    if len(ranked)>=2 and act in ranked[:2]: hit2 += 1
    if len(ranked)>=3 and act in ranked[:3]: hit3 += 1

print(f"\n全局 top1 命中: {hit1}/{n} = {hit1/n*100:.1f}%")
print(f"全局 top2 命中: {hit2}/{n} = {hit2/n*100:.1f}%")
print(f"全局 top3 命中: {hit3}/{n} = {hit3/n*100:.1f}%")