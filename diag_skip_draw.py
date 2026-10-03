import pandas as pd

df = pd.read_csv('detail.csv')
df = df[df['实际胜平负'].notna()].copy()
act = df['实际胜平负'].astype(str).str.strip()
pred = df['胜平负推荐'].astype(str).str.strip()

# 三方向概率
for c in ['模型主胜','模型和局','模型客胜']:
    df[c] = pd.to_numeric(df[c], errors='coerce')

# 模型和局是不是三方向里最高的？
df['模型判和局'] = (df['模型和局'] >= df['模型主胜']) & (df['模型和局'] >= df['模型客胜'])

print("=== 模型和局概率是最高时，这些场次情况 ===")
sub_d = df[df['模型判和局']]
print(f"场次数: {len(sub_d)} ({len(sub_d)/len(df)*100:.1f}%)")
if len(sub_d) > 0:
    act_d = sub_d['实际胜平负'].astype(str).str.strip()
    print(f"  其中实际和局: {(act_d == '和局').sum()} 场 ({(act_d == '和局').mean()*100:.1f}%)")
    print(f"  实际主胜:     {(act_d == '主胜').sum()} 场 ({(act_d == '主胜').mean()*100:.1f}%)")
    print(f"  实际客胜:     {(act_d == '客胜').sum()} 场 ({(act_d == '客胜').mean()*100:.1f}%)")

print()
print("=== 模型判主胜时，实际和局的占比 ===")
sub_h = df[(~df['模型判和局']) & (pred == '主胜')]
if len(sub_h) > 0:
    a = sub_h['实际胜平负'].astype(str).str.strip()
    print(f"  场次 {len(sub_h)}，实际和局 {(a == '和局').sum()} ({(a == '和局').mean()*100:.1f}%)")

print()
print("=== 反例：模型判和局时，实际主/客胜占比 ===")
if len(sub_d) > 0:
    print(f"  也就是说，模型判和局的场次里有 {(1-(act_d == '和局').mean())*100:.1f}% 其实是主胜或客胜")
    print(f"  → 一律挂'观望'会错过这些场次")

print()
print("=== 模拟：剔除模型判和局的场次，剩余命中率 ===")
keep = df[~df['模型判和局']]
hit_keep = (keep['胜平负推荐'].astype(str).str.strip() == keep['实际胜平负'].astype(str).str.strip())
hit_all = (pred == act)
print(f"  全部场次 (n={len(df)}): {hit_all.mean()*100:.1f}%")
print(f"  剔除模型判和局 (n={len(keep)}): {hit_keep.mean()*100:.1f}%")
print(f"  提升: {(hit_keep.mean() - hit_all.mean())*100:+.2f} 个点")
