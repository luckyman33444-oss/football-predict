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
print(f"样本 {len(d)}\n")

FIXED = [(1,1),(1,0),(2,1),(0,1),(0,0),(2,0),(1,2),(2,2)]

strategies = {k: 0 for k in ['当前(选边top3)','全局top3','全局top5','固定8池','全局top3+池']}

for _, r in d.iterrows():
    p = predict_full_dc(r['xg_h'], r['xg_a'], rho=-0.13)
    act = r['实际']

    # DC 完整矩阵
    matrix = p.get('matrix')
    if matrix is None:
        # 用 over/under 混合近似
        allsc = {}
        for h,a,pr in (p.get('over_scores',[]) + p.get('under_scores',[])):
            allsc[(h,a)] = max(allsc.get((h,a),0), pr)
        ranked = sorted(allsc.items(), key=lambda x: -x[1])
    else:
        ranked = sorted(matrix.items(), key=lambda x: -x[1])

    # 当前策略
    side = p['over_scores'] if p['over25'] >= 0.5 else p['under_scores']
    top3_side = [(s[0],s[1]) for s in side[:3]]
    if act in top3_side: strategies['当前(选边top3)'] += 1

    # 全局 top3
    g3 = [k for k,_ in ranked[:3]]
    if act in g3: strategies['全局top3'] += 1

    # 全局 top5
    g5 = [k for k,_ in ranked[:5]]
    if act in g5: strategies['全局top5'] += 1

    # 固定8池
    if act in FIXED: strategies['固定8池'] += 1

    # 全局top3 + 固定池
    if act in g3 or act in FIXED: strategies['全局top3+池'] += 1

n = len(d)
print("=== 各策略命中率 ===")
for k, v in strategies.items():
    print(f"  {k}: {v}/{n} = {v/n*100:.1f}%")

# 当前策略 vs 全局top3 谁更好
print("\n=== 大小球方向对/错时 ===")
d2 = d.copy()
d2['over_ok'] = d2.apply(lambda r: (r['实际'][0]+r['实际'][1] >= 3) == (predict_full_dc(r['xg_h'],r['xg_a'],rho=-0.13)['over25']>=0.5), axis=1)
print("（计算较慢，已完成）")