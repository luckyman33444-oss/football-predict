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

def model_pick(j):
    if pd.isna(j): return None
    j = str(j)
    if '看好主勝' in j: return '主'
    if '看好客勝' in j: return '客'
    return None
df['模型pick'] = df['亚盘判断'].apply(model_pick)

def market_pick(r):
    a, b = r['市场主胜'], r['市场客胜']
    if pd.isna(a) or pd.isna(b): return None
    return '主' if a > b else ('客' if b > a else None)
df['市场pick'] = df.apply(market_pick, axis=1)
df['市场差'] = (df['市场主胜'] - df['市场客胜']).abs()
df['市场AH命中'] = df.apply(lambda r: ah_cover(r['盘方向'], r['盘口'], r['净胜'], r['市场pick']), axis=1)
df['分歧'] = (df['模型pick'].notna()) & (df['市场pick'].notna()) & (df['模型pick'] != df['市场pick'])

sub = df[df['分歧']].copy()
print("分歧总场次:", len(sub), " 命中:", sub['市场AH命中'].mean())

print("\n=== 分歧 按市场差 ===")
for lo, hi in [(0,10),(10,20),(20,35),(35,100)]:
    s = sub[(sub['市场差']>=lo)&(sub['市场差']<hi)]['市场AH命中'].dropna()
    if len(s): print(f"  差{lo}-{hi}: {s.sum()}/{len(s)} = {s.mean():.4f}")

print("\n=== 分歧 按日期分段(每50场) ===")
d = sub.dropna(subset=['市场AH命中']).sort_values('日期').reset_index(drop=True)
for i in range(0, len(d), 50):
    s = d['市场AH命中'].iloc[i:i+50]
    if len(s): print(f"  {i}-{i+len(s)}: {s.sum()}/{len(s)} = {s.mean():.4f}")

print("\n=== 分歧 按盘口 ===")
for line, g in sub.groupby('盘口'):
    s = g['市场AH命中'].dropna()
    if len(s)>=10: print(f"  盘口{line}: {s.sum()}/{len(s)} = {s.mean():.4f}")

print("\n=== 分歧 top联赛 ===")
for lg, g in sub.groupby('联赛'):
    s = g['市场AH命中'].dropna()
    if len(s)>=10: print(f"  {lg}: {s.sum()}/{len(s)} = {s.mean():.4f}")