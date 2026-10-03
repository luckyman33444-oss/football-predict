import pandas as pd
from data import TEAM_CN
from engine import fetch_all_predictions, parse_prediction

all_preds, err = fetch_all_predictions()
parsed = [parse_prediction(p) for p in all_preds]
df = pd.DataFrame(parsed)

print(f"预测总条数: {len(df)}")
if 'event_date' in df.columns:
    dates = sorted(df['event_date'].dropna().unique())
    print(f"覆盖日期: {dates}")
    print()
    print("每天场次:")
    print(df.groupby('event_date').size().to_string())
print()

def is_cn(s):
    return any('\u4e00' <= c <= '\u9fff' for c in str(s))

teams = set(df['主队'].dropna().astype(str)) | set(df['客队'].dropna().astype(str))
missing = sorted([t for t in teams if t not in TEAM_CN and not is_cn(t)])
missing = [t for t in missing if t not in ('?', '—', '', 'nan', 'None')]

print(f"总独立队名: {len(teams)}")
print(f"未翻译的: {len(missing)}")
print()
for t in missing:
    print(t)