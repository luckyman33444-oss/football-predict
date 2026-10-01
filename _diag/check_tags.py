import pandas as pd
df = pd.read_csv('detail.csv')
df = df[df['前3候选'].notna()].copy()
hit = (df['前3命中'].astype(str).str.strip() == '✅')
df['hit'] = hit

print("按等级:")
for lvl in sorted(df['等级'].dropna().unique()):
    sub = df[df['等级'] == lvl]
    print(f"  {lvl}: {len(sub)}场, 前3命中 {sub['hit'].mean()*100:.1f}%")

print()
print(f"全量: {len(df)}场, 前3命中 {hit.mean()*100:.1f}%")