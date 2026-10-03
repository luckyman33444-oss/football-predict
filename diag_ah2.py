import pandas as pd, re
df = pd.read_csv('detail.csv')

def parse_line(s):
    if pd.isna(s): return None, None
    s = str(s).strip()
    if s == '平手': return '平', 0.0
    m = re.match(r'(主讓|客讓)\s*([0-9.]+)', s)
    if not m: return None, None
    side, v = m.group(1), float(m.group(2))
    return ('主' if side == '主讓' else '客'), v

df[['盘方向','盘口']] = df['亚盘方向'].apply(lambda s: pd.Series(parse_line(s)))

def actual_margin(s):
    if pd.isna(s): return None
    m = re.match(r'(\d+)\s*[-:]\s*(\d+)', str(s))
    return int(m.group(1)) - int(m.group(2)) if m else None
df['净胜'] = df['实际比分'].apply(actual_margin)

def ah_cover(direction, line, margin, pick):
    if margin is None or direction is None: return None
    if direction == '平': h = margin
    elif direction == '主': h = margin - line
    else: h = margin + line
    if h == 0: return None
    home_covers = h > 0
    return home_covers if pick == '主' else (not home_covers)

def market_pick(r):
    a, b = r['市场主胜'], r['市场客胜']
    if pd.isna(a) or pd.isna(b): return None
    if a > b: return '主'
    if b > a: return '客'
    return None
df['市场pick'] = df.apply(market_pick, axis=1)
df['市场AH命中'] = df.apply(lambda r: ah_cover(r['盘方向'], r['盘口'], r['净胜'], r['市场pick']), axis=1)

# 按盘口大小
print("=== 按盘口 ===")
for line, g in df.groupby('盘口'):
    s = g['市场AH命中'].dropna()
    if len(s): print(f"  盘口 {line}: {s.sum()}/{len(s)} = {s.mean():.4f}")

# 按日期分段（每300场一段）
d = df.dropna(subset=['市场AH命中']).copy()
if '日期' in d.columns:
    d = d.sort_values('日期').reset_index(drop=True)
seg = 300
print(f"\n=== 按时间分{seg}场一段 ===")
for i in range(0, len(d), seg):
    s = d['市场AH命中'].iloc[i:i+seg]
    if len(s): print(f"  {i}-{i+len(s)}: {s.sum()}/{len(s)} = {s.mean():.4f}")

# 按联赛 top10
print("\n=== 按联赛(样本>100) ===")
for lg, g in df.groupby('联赛'):
    s = g['市场AH命中'].dropna()
    if len(s) > 100: print(f"  {lg}: {s.sum()}/{len(s)} = {s.mean():.4f}")