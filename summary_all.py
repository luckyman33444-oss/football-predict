import pandas as pd
import re

df = pd.read_csv('detail.csv')

def rate(s):
    s = s.dropna()
    if len(s) == 0: return "—"
    return f"{s.sum()}/{len(s)} = {s.mean()*100:.1f}%"

print("=" * 60)
print(f"总场次: {len(df)}  ｜ 日期: 2026-07-03 ~ 2026-10-02")
print("=" * 60)

print("\n【1. 胜平负方向】")
print(f"  模型: {rate(df['胜平负命中'])}")
print(f"  市场: {rate(df['市场命中'])}")
print(f"  融合: {rate(df['融合命中'])}")

print("\n【2. 亚盘方向】")
print(f"  模型: {rate(df['亚盘命中'])}")
print(f"  市场: {rate(df['市场亚盘命中'])}")

print("\n【3. 大小球方向】")
print(f"  模型: {rate(df['大小球命中'])}")
print(f"  市场: {rate(df['市场大小球命中'])}")

print("\n【4. 比分】")
for col in ['主力比分命中', '备选比分命中']:
    v = df[col].dropna()
    full = (v == '✅完全对').sum()
    dir_ok = v.isin(['✅完全对', '⚠️方向对']).sum()
    print(f"  {col}: 完全对 {full}/{len(v)} = {full/len(v)*100:.1f}% ｜ 方向对 {dir_ok}/{len(v)} = {dir_ok/len(v)*100:.1f}%")
s = df['前3命中'].dropna()
_ok = s.isin(['✅','是','True',True]).sum()
print(f"  前3候选命中: {_ok}/{len(s)} = {_ok/len(s)*100:.1f}%")

print("\n" + "=" * 60)
print("【V5.8 强信号筛选器验证】")
print("=" * 60)

df['市场差'] = (df['市场主胜'] - df['市场客胜']).abs()
df['大小球强度'] = df['市场大小球概率'].apply(lambda x: max(x, 100 - x) if pd.notna(x) else None)

print("\n--- 主客和：按市场差分档 ---")
for lo, hi, lb in [(0,10,"差<10"),(10,20,"差10-20"),(20,35,"差20-35"),(35,101,"差≥35 ★")]:
    sub = df[(df['市场差']>=lo)&(df['市场差']<hi)]
    print(f"  {lb}: {rate(sub['市场命中'])}")

print("\n--- 大小球：按市场强度分档 ---")
for lo, hi, lb in [(0,55,"<55"),(55,60,"55-60"),(60,65,"60-65 ★"),(65,101,"≥65 ★★")]:
    sub = df[(df['大小球强度']>=lo)&(df['大小球强度']<hi)]
    print(f"  {lb}: {rate(sub['市场大小球命中'])}")

print("\n--- 亚盘：按市场差分档 ---")
for lo, hi, lb in [(0,10,"差<10"),(10,20,"差10-20"),(20,35,"差20-35"),(35,101,"差≥35 ★")]:
    sub = df[(df['市场差']>=lo)&(df['市场差']<hi)]
    print(f"  {lb}: {rate(sub['市场亚盘命中'])}")

print("\n--- 高置信（市场和局<22）---")
sub = df[df['市场和局'] < 22]
print(f"  主客和: {rate(sub['市场命中'])}  场次占比 {len(sub)/len(df)*100:.1f}%")

print("\n" + "=" * 60)
print("【按等级】")
print("=" * 60)
for g, sub in df.groupby('等级'):
    print(f"  {g} (n={len(sub)}): 胜平负 {rate(sub['市场命中'])} ｜ 大小球 {rate(sub['市场大小球命中'])} ｜ 亚盘 {rate(sub['市场亚盘命中'])}")