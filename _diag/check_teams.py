import pandas as pd
from data import TEAM_CN

df = pd.read_csv('detail.csv')

teams = set(df['主队'].dropna().astype(str)) | set(df['客队'].dropna().astype(str))

# 判断规则：含中文 = 已翻译；纯英文/数字 = 未翻译
def is_cn(s):
    return any('\u4e00' <= c <= '\u9fff' for c in str(s))

untranslated = [t for t in teams if not is_cn(t)]

print(f"detail.csv 出现的独立队名: {len(teams)}")
print(f"已是中文的: {len(teams) - len(untranslated)}")
print(f"未翻译的: {len(untranslated)}")
print()
print("=== 未翻译队名 top 50（按出现场次排） ===")
all_teams = list(df['主队'].dropna().astype(str)) + list(df['客队'].dropna().astype(str))
from collections import Counter
cnt = Counter(t for t in all_teams if not is_cn(t))
for name, c in cnt.most_common(50):
    print(f"  {c:4d}  {name}")