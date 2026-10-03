import pandas as pd
import re

df = pd.read_csv('detail.csv')
rows = []

def add(section, item, hit, n, rate):
    rows.append({"板块": section, "指标": item, "命中": hit, "样本": n, "命中率": rate})

def rate(s):
    s = s.dropna()
    if len(s) == 0: return (0, 0, "—")
    return (int(s.sum()), len(s), f"{s.mean()*100:.1f}%")

n_all = len(df)
rows.append({"板块": "概览", "指标": "总场次", "命中": "", "样本": n_all, "命中率": ""})
rows.append({"板块": "概览", "指标": "日期范围", "命中": "", "样本": "2026-07-03 ~ 2026-10-02", "命中率": ""})

# 1 胜平负
for col, name in [('胜平负命中','模型'),('市场命中','市场'),('融合命中','融合')]:
    h, n, r = rate(df[col]); add("胜平负", name, h, n, r)

# 2 亚盘
h, n, r = rate(df['亚盘命中']); add("亚盘", "模型", h, n, r)
h, n, r = rate(df['市场亚盘命中']); add("亚盘", "市场", h, n, r)

# 3 大小球
h, n, r = rate(df['大小球命中']); add("大小球", "模型", h, n, r)
h, n, r = rate(df['市场大小球命中']); add("大小球", "市场", h, n, r)

# 4 比分
for col, name in [('主力比分命中','主力'),('备选比分命中','备选')]:
    v = df[col].dropna()
    full = (v=='✅完全对').sum()
    add("比分", f"{name}·完全对", int(full), len(v), f"{full/len(v)*100:.1f}%")
    dirok = v.isin(['✅完全对','⚠️方向对']).sum()
    add("比分", f"{name}·方向对", int(dirok), len(v), f"{dirok/len(v)*100:.1f}%")
s = df['前3命中'].dropna()
ok = s.isin(['✅','是','True',True]).sum()
add("比分", "前3候选", int(ok), len(s), f"{ok/len(s)*100:.1f}%")

# 5 强信号筛选器
df['市场差'] = (df['市场主胜'] - df['市场客胜']).abs()
df['大小球强度'] = df['市场大小球概率'].apply(lambda x: max(x, 100-x) if pd.notna(x) else None)

for lo, hi, lb in [(0,10,"差<10"),(10,20,"差10-20"),(20,35,"差20-35"),(35,101,"差≥35★")]:
    sub = df[(df['市场差']>=lo)&(df['市场差']<hi)]
    h, n, r = rate(sub['市场命中']); add("筛选器·主客和", lb, h, n, r)

for lo, hi, lb in [(0,55,"<55"),(55,60,"55-60"),(60,65,"60-65★"),(65,101,"≥65★★")]:
    sub = df[(df['大小球强度']>=lo)&(df['大小球强度']<hi)]
    h, n, r = rate(sub['市场大小球命中']); add("筛选器·大小球", lb, h, n, r)

for lo, hi, lb in [(0,10,"差<10"),(10,20,"差10-20"),(20,35,"差20-35"),(35,101,"差≥35★")]:
    sub = df[(df['市场差']>=lo)&(df['市场差']<hi)]
    h, n, r = rate(sub['市场亚盘命中']); add("筛选器·亚盘", lb, h, n, r)

sub = df[df['市场和局'] < 22]
h, n, r = rate(sub['市场命中']); add("筛选器·高置信", "和局<22", h, n, r)

# 6 按等级
for g, sub in df.groupby('等级'):
    h, n, r = rate(sub['市场命中']); add(f"等级{g}", "胜平负", h, n, r)
    h, n, r = rate(sub['市场大小球命中']); add(f"等级{g}", "大小球", h, n, r)
    h, n, r = rate(sub['市场亚盘命中']); add(f"等级{g}", "亚盘", h, n, r)

rep = pd.DataFrame(rows)
rep.to_csv("report_v58.csv", index=False, encoding="utf-8-sig")
print("✅ 已生成 report_v58.csv")
print(rep.to_string(index=False))