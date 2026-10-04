import pandas as pd

df = pd.read_csv('detail.csv')

def cv(df, mask_col, hit_col, label):
    d = df.dropna(subset=[hit_col]).sort_values('日期').reset_index(drop=True)
    n = len(d); k = 5; fold = n // k
    print(f"=== {label} （总 {n}）===")
    rates = []
    for i in range(k):
        seg = d.iloc[i*fold:(i+1)*fold] if i < k-1 else d.iloc[i*fold:]
        s = seg[seg[mask_col]][hit_col].dropna()
        if len(s):
            rates.append(s.mean())
            print(f"  折{i+1}: {s.sum()}/{len(s)} = {s.mean():.4f}")
    if rates:
        import statistics
        print(f"  → 均值 {statistics.mean(rates):.4f} ｜ 最低 {min(rates):.4f} ｜ 最高 {max(rates):.4f}")
    print()

# 大小球：市场概率 >= 60 / >= 65
df['ou_ge60'] = df['市场大小球概率'] >= 60
df['ou_ge65'] = df['市场大小球概率'] >= 65
cv(df, 'ou_ge60', '市场大小球命中', '大小球 市场概率>=60')
cv(df, 'ou_ge65', '市场大小球命中', '大小球 市场概率>=65')

# 主客和：市场差 >= 35
df['gap_ge35'] = df['市场差'] >= 35
cv(df, 'gap_ge35', '市场命中', '主客和 市场差>=35')

# 主客和：市场差>=20（扩量）
df['gap_ge20'] = df['市场差'] >= 20
cv(df, 'gap_ge20', '市场命中', '主客和 市场差>=20')

# 每天场次
print("=== 覆盖率 ===")
n = len(df)
for col, name in [('ou_ge60','大小球>=60'),('ou_ge65','大小球>=65'),('gap_ge35','主客和差>=35'),('gap_ge20','主客和差>=20')]:
    c = df[col].sum()
    print(f"  {name}: {c}/{n} = {c/n*100:.1f}%")