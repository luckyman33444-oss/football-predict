import pandas as pd
df = pd.read_csv('detail.csv')
df = df[df['实际比分'].notna() & df['模型xG'].notna()].copy()
df['实际比分'] = df['实际比分'].astype(str).str.strip()

# 解析 "1.50-1.20"
def parse_xg(s):
    try:
        a, b = str(s).split('-')
        return float(a), float(b)
    except:
        return None, None

df[['xg_h','xg_a']] = df['模型xG'].apply(lambda s: pd.Series(parse_xg(s)))
df = df.dropna(subset=['xg_h','xg_a'])
df['diff'] = (df['xg_h'] - df['xg_a']).abs()

# 分 3 档
def bucket(d):
    if d >= 0.8: return '悬殊(差>=0.8)'
    if d >= 0.4: return '中等(0.4-0.8)'
    return '均衡(差<0.4)'
df['档'] = df['diff'].apply(bucket)

GLOBAL8 = ['1-1','1-0','2-1','0-1','0-0','2-0','1-2','2-2']

print("=== 各强弱档：实际比分 top8 + 与全局池对比 ===")
for b in ['悬殊(差>=0.8)','中等(0.4-0.8)','均衡(差<0.4)']:
    sub = df[df['档'] == b]
    if len(sub) == 0: continue
    print(f"\n【{b}】 n={len(sub)}")
    top = sub['实际比分'].value_counts().head(8)
    for score, cnt in top.items():
        print(f"  {score:6s} {cnt:4d}  {cnt/len(sub)*100:5.1f}%")

    own = list(top.index)
    h_own = sub['实际比分'].isin(own).mean() * 100
    h_glo = sub['实际比分'].isin(GLOBAL8).mean() * 100
    print(f"  --> 自己池 {h_own:.1f}%  全局池 {h_glo:.1f}%  差 {h_own-h_glo:+.1f}")
    extra = [s for s in own if s not in GLOBAL8]
    miss  = [s for s in GLOBAL8 if s not in own]
    print(f"      + 加入: {extra}")
    print(f"      - 移除: {miss}")

# 主胜方 xG 高低 也看下（不只是差值）
print()
print("=" * 60)
print("=== 按主队 xG 绝对高低分档 ===")
def xg_bucket(x):
    if x >= 2.0: return '主强(>=2.0)'
    if x >= 1.5: return '中(1.5-2.0)'
    return '弱(<1.5)'
df['xgb'] = df['xg_h'].apply(xg_bucket)
for b in ['主强(>=2.0)','中(1.5-2.0)','弱(<1.5)']:
    sub = df[df['xgb'] == b]
    print(f"\n【{b}】 n={len(sub)}")
    top = sub['实际比分'].value_counts().head(8)
    for score, cnt in top.items():
        print(f"  {score:6s} {cnt:4d}  {cnt/len(sub)*100:5.1f}%")