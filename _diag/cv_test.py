import pandas as pd
import numpy as np

df = pd.read_csv('detail.csv')
df = df[df['实际比分'].notna() & df['模型xG'].notna()].copy()
df['实际比分'] = df['实际比分'].astype(str).str.strip()

def parse_xg(s):
    try:
        a, b = str(s).split('-')
        return float(a), float(b)
    except:
        return None, None

df[['xg_h','xg_a']] = df['模型xG'].apply(lambda s: pd.Series(parse_xg(s)))
df = df.dropna(subset=['xg_h','xg_a'])
df['diff'] = (df['xg_h'] - df['xg_a']).abs()

GLOBAL8 = ['1-1','1-0','2-1','0-1','0-0','2-0','1-2','2-2']

# 只测悬殊档
big = df[df['diff'] >= 0.8].copy().reset_index(drop=True)

# 2 折：随机奇偶交替
np.random.seed(42)
big['fold'] = np.random.randint(0, 2, len(big))

def top8(sub):
    return list(sub['实际比分'].value_counts().head(8).index)

def hit(sub, pool):
    return sub['实际比分'].isin(pool).mean() * 100

print(f"悬殊档 n={len(big)}\n")
print("=== 2折交叉验证 ===")
own_avg = 0
glo_avg = 0
for f in [0, 1]:
    train = big[big['fold'] != f]   # 用另一半算池
    test  = big[big['fold'] == f]   # 在这一半上测
    own = top8(train)
    h_own = hit(test, own)
    h_glo = hit(test, GLOBAL8)
    own_avg += h_own / 2
    glo_avg += h_glo / 2
    print(f"  折{f}: train n={len(train)}  test n={len(test)}")
    print(f"     自己池(train算) {h_own:.1f}%   全局池 {h_glo:.1f}%   差 {h_own-h_glo:+.1f}")
    print(f"     用的池: {own}")

print(f"\n平均: 自己池 {own_avg:.1f}%  全局池 {glo_avg:.1f}%  差 {own_avg-glo_avg:+.1f}")

# 用"理论池"再测一次（不依赖 train 数据）
THEORY_BIG = ['2-1','2-0','1-0','3-0','3-1','1-1','0-0','0-1']
print(f"\n=== 理论池（不看数据）===")
h_theory = hit(big, THEORY_BIG)
h_glo = hit(big, GLOBAL8)
print(f"  理论悬殊池 {h_theory:.1f}%  全局池 {h_glo:.1f}%  差 {h_theory-h_glo:+.1f}")
print(f"  理论池: {THEORY_BIG}")