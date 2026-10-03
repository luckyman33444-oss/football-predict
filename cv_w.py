import pandas as pd
import numpy as np

df = pd.read_csv('detail.csv')
df = df[df['实际胜平负'].notna()].copy()
act_all = df['实际胜平负'].astype(str).str.strip()
df['actual'] = act_all

for c in ['模型主胜','模型和局','模型客胜','市场主胜','市场和局','市场客胜']:
    df[c] = pd.to_numeric(df[c], errors='coerce')

def predict(df, w):
    bhw = w*df['模型主胜']/100 + (1-w)*df['市场主胜']/100
    baw = w*df['模型客胜']/100 + (1-w)*df['市场客胜']/100
    return bhw.ge(baw).map({True:'主胜', False:'客胜'})

def hit(df, w):
    return (predict(df, w) == df['actual']).mean() * 100

def cv_best_w(sub):
    """2折CV：train找最优w，test验证"""
    sub = sub.reset_index(drop=True)
    np.random.seed(42)
    sub['fold'] = np.random.randint(0, 2, len(sub))
    gains = []
    for f in [0, 1]:
        train = sub[sub['fold'] != f]
        test  = sub[sub['fold'] == f]
        if len(train) < 30 or len(test) < 30: continue
        best_w, best_hr = 0, -1
        for w in [0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8]:
            hr = hit(train, w)
            if hr > best_hr: best_hr = hr; best_w = w
        test_h = hit(test, best_w)
        test_base = hit(test, 0.0)
        gains.append(test_h - test_base)
    return np.mean(gains) if gains else 0

print("=== 按等级（CV 后真实增益） ===")
for lvl in ['S','A','B','F']:
    sub = df[df['等级'] == lvl].copy()
    if len(sub) < 100: continue
    g = cv_best_w(sub)
    print(f"  等级 {lvl}: n={len(sub):4d}  CV 真实增益 {g:+.2f}%")

print()
print("=== 按联赛（n>=100，CV 后真实增益） ===")
for lg in df['联赛'].value_counts().index:
    sub = df[df['联赛'] == lg].copy()
    if len(sub) < 100: continue
    g = cv_best_w(sub)
    print(f"  {lg:25s} n={len(sub):4d}  CV 真实增益 {g:+.2f}%")