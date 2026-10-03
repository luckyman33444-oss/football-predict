import pandas as pd
from itertools import combinations

df = pd.read_csv('detail.csv')
df = df[df['实际比分'].notna()].copy()
actual = df['实际比分'].astype(str).str.strip()

candidates = ['1-1','1-0','2-1','0-1','0-0','2-0','1-2','2-2','3-1','0-2']

print("=== 所有 2 比分组合，按覆盖率排序 top10 ===")
results = []
for combo in combinations(candidates, 2):
    cover = actual.isin(combo).mean() * 100
    triple = (cover/100)**3 * 100
    results.append((combo, cover, triple))
results.sort(key=lambda x: -x[1])
for combo, cover, triple in results[:10]:
    mark = " ← 当前使用" if set(combo) == {'1-1','1-0'} else ""
    print(f"  {combo[0]} + {combo[1]}: 单场 {cover:5.1f}%  →  3串1约 {triple:.2f}%{mark}")

print()
print("=== 3 比分组合（27注）top5 ===")
results3 = []
for combo in combinations(candidates, 3):
    cover = actual.isin(combo).mean() * 100
    triple = (cover/100)**3 * 100
    results3.append((combo, cover, triple))
results3.sort(key=lambda x: -x[1])
for combo, cover, triple in results3[:5]:
    print(f"  {combo[0]}+{combo[1]}+{combo[2]}: 单场 {cover:5.1f}%  →  3串1约 {triple:.2f}%")