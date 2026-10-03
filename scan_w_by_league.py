import pandas as pd

df = pd.read_csv('detail.csv')
df = df[df['实际胜平负'].notna()].copy()
act = df['实际胜平负'].astype(str).str.strip()

for c in ['模型主胜','模型和局','模型客胜','市场主胜','市场和局','市场客胜']:
    df[c] = pd.to_numeric(df[c], errors='coerce')

def hit_rate(sub, w):
    mhw = sub['模型主胜']/100; maw = sub['模型客胜']/100
    khw = sub['市场主胜']/100; kaw = sub['市场客胜']/100
    bhw = w*mhw + (1-w)*khw
    baw = w*maw + (1-w)*kaw
    pred = bhw.ge(baw).map({True:'主胜', False:'客胜'})
    a = sub['实际胜平负'].astype(str).str.strip()
    return (pred == a).mean() * 100

def scan(sub, name):
    if len(sub) < 50:
        return None
    best_w, best_hr = 0, 0
    for w in [0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]:
        hr = hit_rate(sub, w)
        if hr > best_hr: best_hr = hr; best_w = w
    base_hr = hit_rate(sub, 0.0)  # 纯市场基准
    gain = best_hr - base_hr
    print(f"  {name:30s} n={len(sub):4d}  最优w={best_w:.1f}  命中{best_hr:5.2f}%  vs纯市场{base_hr:5.2f}%  增益{gain:+.2f}")
    return best_w, gain

print("=== 按等级分档 ===")
for lvl in ['S','A','B','F']:
    sub = df[df['等级'] == lvl]
    scan(sub, f"等级 {lvl}")

print()
print("=== 按联赛分档（仅 n>=100） ===")
for lg in df['联赛'].value_counts().index:
    sub = df[df['联赛'] == lg]
    if len(sub) < 100: continue
    scan(sub, lg)

print()
print("=== 全量基准 ===")
scan(df, "全量")