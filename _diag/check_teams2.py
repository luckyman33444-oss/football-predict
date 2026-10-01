import pandas as pd
from data import TEAM_CN

df = pd.read_csv('detail.csv')
all_teams = list(df['主队'].dropna().astype(str)) + list(df['客队'].dropna().astype(str))

def is_cn(s):
    return any('\u4e00' <= c <= '\u9fff' for c in str(s))

from collections import Counter
cnt = Counter(t for t in all_teams if not is_cn(t))

print(f"未翻译队名: {len(cnt)} 个")
print(f"出现 >=5 次的: {sum(1 for _, c in cnt.items() if c >= 5)} 个")
print()
print("=== 剩余未翻译（top20）===")
for name, c in cnt.most_common(20):
    print(f"  {c:4d}  {name}")