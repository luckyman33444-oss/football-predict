import pandas as pd, re, numpy as np

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
    if a > b: return '主'
    if b > a: return '客'
    return None
df['市场pick'] = df.apply(market_pick, axis=1)

df['市场AH命中'] = df.apply(lambda r: ah_cover(r['盘方向'], r['盘口'], r['净胜'], r['市场pick']), axis=1)
df['模型AH命中'] = df.apply(lambda r: ah_cover(r['盘方向'], r['盘口'], r['净胜'], r['模型pick']), axis=1)

# 市场方向与模型方向是否一致
df['一致'] = (df['市场pick'] == df['模型pick']).astype(object)
df.loc[df['模型pick'].isna() | df['市场pick'].isna(), '一致'] = None

# 分组统计
print("=== 市场AH命中：按一致性分组 ===")
for flag, g in df.groupby('一致'):
    s = g['市场AH命中'].dropna()
    if len(s): print(f"  {'一致' if flag else '分歧'}: {s.sum()}/{len(s)} = {s.mean():.4f}")

print("\n=== 市场AH命中：按市场概率差 (|主-客|) ===")
df['市场差'] = (df['市场主胜'] - df['市场客胜']).abs()
bins = [0, 5, 10, 20, 35, 100]
for lo, hi in zip(bins[:-1], bins[1:]):
    sub = df[(df['市场差'] >= lo) & (df['市场差'] < hi)]
    s = sub['市场AH命中'].dropna()
    if len(s): print(f"  差{lo}-{hi}: {s.sum()}/{len(s)} = {s.mean():.4f}")

print("\n=== 市场AH命中：一致 且 按市场差 ===")
sub = df[df['一致'] == True]
for lo, hi in zip(bins[:-1], bins[1:]):
    s2 = sub[(sub['市场差'] >= lo) & (sub['市场差'] < hi)]['市场AH命中'].dropna()
    if len(s2): print(f"  差{lo}-{hi}: {s2.sum()}/{len(s2)} = {s2.mean():.4f}")

print("\n=== 分歧时 谁更准 ===")
sub = df[df['一致'] == False]
s_mkt = sub['市场AH命中'].dropna()
s_mdl = sub['模型AH命中'].dropna()
print(f"  市场AH: {s_mkt.sum()}/{len(s_mkt)} = {s_mkt.mean():.4f}")
print(f"  模型AH: {s_mdl.sum()}/{len(s_mdl)} = {s_mdl.mean():.4f}")