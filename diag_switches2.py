import pandas as pd, re
from engine import predict_full_dc
from data import MATCH_TIER_MULTIPLIER

df = pd.read_csv('detail.csv')

def pxg(s):
    m = re.match(r'([0-9.]+)\s*-\s*([0-9.]+)', str(s))
    return (float(m.group(1)), float(m.group(2))) if m else (None, None)
def actual_res(s):
    m = re.match(r'(\d+)\s*[-:]\s*(\d+)', str(s))
    if not m: return None
    h, a = int(m.group(1)), int(m.group(2))
    return "主胜" if h > a else ("和局" if h == a else "客胜")

df[['xg_h','xg_a']] = df['模型xG'].apply(lambda s: pd.Series(pxg(s)))
df['实际'] = df['实际比分'].apply(actual_res)
d = df.dropna(subset=['xg_h','xg_a','实际']).copy()
n = len(d)
print(f"样本 {n}")
print("MATCH_TIER_MULTIPLIER 全部键:", list(MATCH_TIER_MULTIPLIER.keys()))
print()

# 先看 tier 是怎么定的
from engine import get_match_tier
d['tier'] = d['联赛'].apply(lambda x: get_match_tier(str(x), ""))
print("tier 分布:", d['tier'].value_counts().to_dict())
print()

hit_base = hit_tier = 0
for _, r in d.iterrows():
    xh, xa = r['xg_h'], r['xg_a']
    p0 = predict_full_dc(xh, xa, rho=-0.13)
    pick0 = "主胜" if p0['hw'] >= max(p0['d'], p0['aw']) else ("和局" if p0['d'] >= p0['aw'] else "客胜")
    if pick0 == r['实际']: hit_base += 1

    tm = MATCH_TIER_MULTIPLIER.get(r['tier'], 1.0)
    p1 = predict_full_dc(xh*tm, xa*tm, rho=-0.13)
    pick1 = "主胜" if p1['hw'] >= max(p1['d'], p1['aw']) else ("和局" if p1['d'] >= p1['aw'] else "客胜")
    if pick1 == r['实际']: hit_tier += 1

print(f"纯DC:        {hit_base}/{n} = {hit_base/n*100:.1f}%")
print(f"DC+分层(真实): {hit_tier}/{n} = {hit_tier/n*100:.1f}%")
print()
print("分层乘数表:", MATCH_TIER_MULTIPLIER)