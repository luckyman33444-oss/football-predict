import pandas as pd, re
from engine import predict_full_dc, blend_with_market, cap_home_win_prob, DIXON_COLES_RHO
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
def actual_ou(s):
    m = re.match(r'(\d+)\s*[-:]\s*(\d+)', str(s))
    return (int(m.group(1)) + int(m.group(2)) >= 3) if m else None

df[['xg_h','xg_a']] = df['模型xG'].apply(lambda s: pd.Series(pxg(s)))
df['实际'] = df['实际比分'].apply(actual_res)
df['实际大'] = df['实际比分'].apply(actual_ou)

# trust 映射
def trust_of(grade):
    return {"S":"top","A":"mid","B":"mid","F":"low"}.get(grade, "mid")

d = df.dropna(subset=['xg_h','xg_a','实际','实际大']).copy()
n = len(d)
print(f"样本 {n}\n")

configs = {
    "① 纯DC(rho=-0.13)":        dict(rho=-0.13, cap=False, blend=False),
    "② DC + 分层":              dict(rho=-0.13, cap=False, blend=False, tier=True),
    "③ DC + 主胜封顶":          dict(rho=-0.13, cap=True,  blend=False),
    "④ DC + 盘口融合(市场1X2)": dict(rho=-0.13, cap=False, blend=True),
    "⑤ 全开(分层+封顶+融合)":   dict(rho=-0.13, cap=True,  blend=True, tier=True),
}

results = []
for name, cfg in configs.items():
    hit_res = hit_ou = 0
    for _, r in d.iterrows():
        xh, xa = r['xg_h'], r['xg_a']
        if cfg.get('tier'):
            tm = MATCH_TIER_MULTIPLIER.get('normal', 1.0)
            xh *= tm; xa *= tm
        p = predict_full_dc(xh, xa, rho=cfg['rho'])
        if not p: continue
        hw, dd, aw = p['hw'], p['d'], p['aw']
        if cfg.get('blend'):
            ph = r['市场主胜']/100; pd_ = r['市场和局']/100; pa = r['市场客胜']/100
            if ph and pa:
                w = 0.7
                bhw = w*hw + (1-w)*ph; bd = w*dd + (1-w)*pd_; baw = w*aw + (1-w)*pa
                t = bhw+bd+baw
                if t>0: bhw/=t; bd/=t; baw/=t
                hw, dd, aw = bhw, bd, baw
        if cfg.get('cap'):
            hw, dd, aw = cap_home_win_prob(hw, dd, aw)
        pick = "主胜" if hw >= max(dd, aw) else ("和局" if dd >= aw else "客胜")
        if pick == r['实际']: hit_res += 1
        ou_pick = p['over25'] >= 0.5
        if ou_pick == r['实际大']: hit_ou += 1
    results.append({"配置": name, "胜平负": f"{hit_res/n*100:.1f}%", "大小球": f"{hit_ou/n*100:.1f}%"})

print(pd.DataFrame(results).to_string(index=False))