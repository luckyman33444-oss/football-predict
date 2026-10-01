import pandas as pd
df = pd.read_csv('detail.csv')
df = df[df['前3候选'].notna()].copy()
df['hit'] = (df['前3命中'].astype(str).str.strip() == '✅')
df['ou_hit'] = (df['大小球命中'].astype(str).str.strip() == 'True')

print("=== 前3命中，按大小球判对/错拆 ===")
for k, name in [(True, '大小球判对'), (False, '大小球判错')]:
    sub = df[df['ou_hit'] == k]
    print(f"  {name}: {len(sub)}场  前3命中 {sub['hit'].mean()*100:.1f}%")

print()
print(f"全量: {len(df)}场  前3命中 {df['hit'].mean()*100:.1f}%")