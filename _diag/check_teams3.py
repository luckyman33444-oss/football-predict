import pandas as pd
from data import TEAM_CN

df = pd.read_csv('detail.csv')
all_teams = set(df['主队'].dropna().astype(str)) | set(df['客队'].dropna().astype(str))

# 只挑"未在 TEAM_CN 里"的
missing = [t for t in all_teams if t not in TEAM_CN and not any('\u4e00' <= c <= '\u9fff' for c in t)]

print(f"detail.csv 独立队名: {len(all_teams)}")
print(f"TEAM_CN 条目: {len(TEAM_CN)}")
print(f"仍未被覆盖的英文名: {len(missing)}")
print()
print("=== 未覆盖 top30（若有）===")
from collections import Counter
cnt = Counter(t for t in list(df['主队']) + list(df['客队']) if t in missing)
for name, c in cnt.most_common(30):
    print(f"  {c:4d}  {name}")