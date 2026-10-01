import pandas as pd
df = pd.read_csv('detail.csv')
df = df[df['前3候选'].notna() & df['实际比分'].notna()].copy()
actual = df['实际比分'].astype(str).str.strip()

POOL = ['1-1','1-0','2-1','0-1','0-0','2-0','1-2','2-2']

def hr(pool):
    return actual.isin(pool).mean() * 100

print(f"完整 8 池命中: {hr(POOL):.1f}%\n")

print("=== 逐个移除，看掉多少（掉得多=贡献大） ===")
base = hr(POOL)
for s in POOL:
    sub = [x for x in POOL if x != s]
    print(f"  移除 {s}: 剩{len(sub)}个  命中 {hr(sub):.1f}%   ↓{base - hr(sub):.2f}")

print()
print("=== 只留 3 个和局比分，看命中 ===")
draw3 = ['1-1','0-0','2-2']
print(f"  和局池 {draw3}: {hr(draw3):.1f}%")

print()
print("=== 只留 5 个非和局比分 ===")
non_draw = ['1-0','2-1','0-1','2-0','1-2']
print(f"  非和局池 {non_draw}: {hr(non_draw):.1f}%")

print()
print("=== 各方向的实际占比 ===")
print(f"  和局(1-1,0-0,2-2): {(actual.isin(draw3)).mean()*100:.1f}%")
print(f"  非和局: {actual.isin(non_draw).mean()*100:.1f}%")

print()
print("=== 每个比分单独占比（频率） ===")
for s in POOL:
    print(f"  {s}: {(actual == s).mean()*100:.1f}%")