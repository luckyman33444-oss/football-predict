import pandas as pd
df = pd.read_csv('detail.csv')
df = df[df['实际胜平负'].notna()].copy()
act = df['实际胜平负'].astype(str).str.strip()

for col, name in [('胜平负推荐','模型'), ('市场推荐','市场'), ('融合推荐','融合')]:
    if col not in df.columns:
        print(f"{name}: 字段不存在")
        continue
    pred = df[col].astype(str).str.strip()
    hit = (pred == act)
    print(f"{name:6s}: {hit.mean()*100:5.1f}%  (n={len(df)})")

print()
print("=== 交叉：模型 vs 市场 谁更好 ===")
if '市场推荐' in df.columns:
    m_hit = (df['胜平负推荐'].astype(str).str.strip() == act)
    k_hit = (df['市场推荐'].astype(str).str.strip() == act)
    print(f"  模型对 & 市场错: {((m_hit)&(~k_hit)).sum()}")
    print(f"  模型错 & 市场对: {((~m_hit)&(k_hit)).sum()}")
    print(f"  都对: {(m_hit&k_hit).sum()}")
    print(f"  都错: {((~m_hit)&(~k_hit)).sum()}")
    print(f"  模型和市场一致场次: {(df['胜平负推荐'].astype(str).str.strip()==df['市场推荐'].astype(str).str.strip()).sum()}")