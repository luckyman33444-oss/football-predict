import pandas as pd
df = pd.read_csv('detail.csv')
df = df[df['前3候选'].notna() & df['实际胜平负'].notna()].copy()

# 从 "主胜 71.9% 🔒 高" 里抽 "主胜"
df['dir'] = df['比分方向'].astype(str).str.extract(r'^(主胜|客胜|和局)')
hit = (df['dir'] == df['实际胜平负'].astype(str).str.strip())
print(f"模型'比分方向'命中: {hit.mean()*100:.1f}%  (n={len(df)})")
print()
print("模型判的方向分布:")
print(df['dir'].value_counts(dropna=False).to_string())
print()
print("实际方向分布:")
print(df['实际胜平负'].value_counts().to_string())