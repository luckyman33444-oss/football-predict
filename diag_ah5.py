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
    return '主' if a > b else ('客' if b > a else None)
df['市场pick'] = df.apply(market_pick, axis=1)
df['市场差'] = (df['市场主胜'] - df['市场客胜']).abs()
df['市场AH命中'] = df.apply(lambda r: ah_cover(r['盘方向'], r['盘口'], r['净胜'], r['市场pick']), axis=1)
df['分歧'] = (df['模型pick'].notna()) & (df['市场pick'].notna()) & (df['模型pick'] != df['市场pick'])

d = df.dropna(subset=['市场AH命中']).sort_values('日期').reset_index(drop=True)
n = len(d)
k = 5  # 5折
fold = n // k

print(f"总样本 {n}，{k}折\n")

print("=== 市场差>35 各折命中 ===")
for i in range(k):
    seg = d.iloc[i*fold:(i+1)*fold] if i < k-1 else d.iloc[i*fold:]
    s = seg[seg['市场差'] > 35]['市场AH命中']
    print(f"  折{i+1}: {s.sum()}/{len(s)} = {s.mean():.4f}" if len(s) else f"  折{i+1}: 0场")

print("\n=== 分歧 各折命中 ===")
for i in range(k):
    seg = d.iloc[i*fold:(i+1)*fold] if i < k-1 else d.iloc[i*fold:]
    s = seg[seg['分歧']]['市场AH命中']
    print(f"  折{i+1}: {s.sum()}/{len(s)} = {s.mean():.4f}" if len(s) else f"  折{i+1}: 0场")

print("\n=== 分歧 且 市场差>35 各折 ===")
for i in range(k):
    seg = d.iloc[i*fold:(i+1)*fold] if i < k-1 else d.iloc[i*fold:]
    s = seg[seg['分歧'] & (seg['市场差']>35)]['市场AH命中']
    print(f"  折{i+1}: {s.sum()}/{len(s)} = {s.mean():.4f}" if len(s) else f"  折{i+1}: 0场")

print("\n=== 每日场次数 ===")
print(f"  市场差>35 占 {len(d[d['市场差']>35])}/{n} = {len(d[d['市场差']>35])/n*100:.1f}%")
print(f"  分歧 占 {len(d[d['分歧']])}/{n} = {len(d[d['分歧']])/n*100:.1f}%")
print(f"  分歧&差>35 占 {len(d[d['分歧']&(d['市场差']>35)])}/{n} = {len(d[d['分歧']&(d['市场差']>35)])/n*100:.1f}%")
print(f"  日期跨度 {d['日期'].min()} ~ {d['日期'].max()}，{(pd.to_datetime(d['日期'].max())-pd.to_datetime(d['日期'].min())).days}天")