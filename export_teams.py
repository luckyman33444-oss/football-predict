import pandas as pd
from collections import Counter

df = pd.read_csv('detail.csv')
all_teams = list(df['主队'].dropna().astype(str)) + list(df['客队'].dropna().astype(str))

def is_cn(s):
    return any('\u4e00' <= c <= '\u9fff' for c in str(s))

cnt = Counter(t for t in all_teams if not is_cn(t))

# 按频次降序导出
with open('untranslated_teams.txt', 'w', encoding='utf-8') as f:
    for name, c in cnt.most_common():
        f.write(f"{name}\n")

print(f"已导出 {len(cnt)} 个未翻译队名到 untranslated_teams.txt")
print(f"出现 >=5 次的: {sum(1 for _, c in cnt.items() if c >= 5)} 个")
print(f"出现 2-4 次的: {sum(1 for _, c in cnt.items() if 2 <= c < 5)} 个")
print(f"出现 1 次的: {sum(1 for _, c in cnt.items() if c == 1)} 个")