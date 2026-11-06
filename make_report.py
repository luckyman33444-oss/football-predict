import pandas as pd
import os

if not os.path.exists('detail.csv'):
    print("❌ 没找到 detail.csv，请先跑 run_bt.py")
    exit()

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
if "日期" in df.columns:
    _ds = df["日期"].dropna().astype(str)
    _ds = _ds[_ds.str.len() >= 10].sort_values()
    _range = f"{_ds.iloc[0][:10]} ~ {_ds.iloc[-1][:10]}" if len(_ds) else "—"
else:
    _range = "—"
rows.append({"板块": "概览", "指标": "日期范围", "命中": "", "样本": _range, "命中率": ""})

# 1 胜平负 (V6.3 只认绝对臣服市场的胜负推荐)
h, n, r = rate(df['胜负命中']); add("胜负", "V6.3 最终方向", h, n, r)

# 2 大小球
h, n, r = rate(df['大小球命中']); add("大小球", "V6.3 最终方向", h, n, r)

# 3 比分
for col, name in [('主力比分命中','主力'),('备选比分命中','备选')]:
    v = df[col].dropna()
    if len(v) > 0:
        full = (v=='✅完全对').sum()
        add("比分", f"{name}·完全对", int(full), len(v), f"{full/len(v)*100:.1f}%")
        dirok = v.isin(['✅完全对','⚠️方向对']).sum()
        add("比分", f"{name}·方向对", int(dirok), len(v), f"{dirok/len(v)*100:.1f}%")

s = df['前3命中'].dropna()
if len(s) > 0:
    ok = s.isin(['✅','是','True',True]).sum()
    add("比分", "前3候选", int(ok), len(s), f"{ok/len(s)*100:.1f}%")

# 4 筛选器 (按市场差分档)
if "市场差" in df.columns:
    for lo, hi, lb in [(0,10,"差<10"),(10,20,"差10-20"),(20,35,"差20-35"),(35,101,"差≥35★")]:
        sub = df[(df['市场差']>=lo)&(df['市场差']<hi)]
        h, n, r = rate(sub['胜负命中']); add("筛选器·主客和", lb, h, n, r)

# 5 按等级
if "等级" in df.columns:
    for g, sub in df.groupby('等级'):
        h, n, r = rate(sub['胜负命中']); add(f"等级{g}", "胜平负", h, n, r)
        h, n, r = rate(sub['大小球命中']); add(f"等级{g}", "大小球", h, n, r)

rep = pd.DataFrame(rows)
rep.to_csv("report_v58.csv", index=False, encoding="utf-8-sig")
print("\n" + "="*50)
print("✅ V6.3 纯净版大样本回测报告已生成")
print("="*50)
print(rep.to_string(index=False))
