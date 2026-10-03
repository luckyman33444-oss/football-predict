import pandas as pd, re

df = pd.read_csv('detail.csv')

def actual_total(s):
    m = re.match(r'(\d+)\s*[-:]\s*(\d+)', str(s))
    return int(m.group(1)) + int(m.group(2)) if m else None
df['总进球'] = df['实际比分'].apply(actual_total)
df['实际大球'] = df['总进球'].apply(lambda t: (t >= 3) if pd.notna(t) else None)

# 模型大小球命中
s = df['大小球命中'].dropna()
print(f"模型大小球: {s.sum()}/{len(s)} = {s.mean():.4f}")

# 模型大小球方向分布
print("\n模型推荐方向:")
print(df['大小球推荐'].value_counts().to_dict())

# 用模型 over 概率（大小球概率列）作方向
def model_over_dir(r):
    rec = r['大小球推荐']; p = r['大小球概率']
    if pd.isna(p): return None
    return rec  # 已是推荐方向

# 市场大小球：detail.csv 里没有直接市场OU列，看列名
print("\n列名含 over/大小球/ou:")
print([c for c in df.columns if 'over' in c.lower() or '大小球' in c or 'ou' in c.lower()])