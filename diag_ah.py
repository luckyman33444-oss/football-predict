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
    if not m: return None
    return int(m.group(1)) - int(m.group(2))

df['净胜'] = df['实际比分'].apply(actual_margin)

def ah_cover(direction, line, margin, pick):
    """返回 pick 方在该盘口下是否赢盘。pick: '主' or '客'。None=push/无效"""
    if margin is None or direction is None: return None
    if direction == '平':
        h = margin
    elif direction == '主':
        h = margin - line
    else:  # 客讓
        h = margin + line
    if h == 0: return None  # 走盘
    home_covers = h > 0
    return home_covers if pick == '主' else (not home_covers)

# 模型方向
def model_pick(j):
    if pd.isna(j): return None
    j = str(j)
    if '看好主勝' in j: return '主'
    if '看好客勝' in j: return '客'
    return None

df['模型pick'] = df['亚盘判断'].apply(model_pick)

# 市场方向: 从市场主胜/客胜谁大
def market_pick(r):
    a, b = r['市场主胜'], r['市场客胜']
    if pd.isna(a) or pd.isna(b): return None
    if a > b: return '主'
    if b > a: return '客'
    return None

df['市场pick'] = df.apply(market_pick, axis=1)

# 计算命中
def hit(row, pick_col):
    return ah_cover(row['盘方向'], row['盘口'], row['净胜'], row[pick_col])

df['模型AH命中'] = df.apply(lambda r: hit(r, '模型pick'), axis=1)
df['市场AH命中'] = df.apply(lambda r: hit(r, '市场pick'), axis=1)

def rate(col):
    s = df[col].dropna()
    if len(s) == 0: return (0, 0, 0)
    return (s.sum(), len(s), s.mean())

for c in ['模型AH命中','市场AH命中']:
    w, n, r = rate(c)
    print(f"{c}: {w}/{n} = {r:.4f}" if n else f"{c}: 无数据")

# 只在模型非观望 且 市场有方向 的子集对比
sub = df[(df['模型pick'].notna()) & (df['市场pick'].notna())]
print("\n共同子集 n =", len(sub))
for c in ['模型AH命中','市场AH命中']:
    s = sub[c].dropna()
    print(f"  {c}: {s.sum()}/{len(s)} = {s.mean():.4f}" if len(s) else f"  {c}: 无")