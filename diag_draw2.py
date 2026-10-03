import pandas as pd

df = pd.read_csv('detail.csv')
df = df[df['实际胜平负'].notna()].copy()
act = df['实际胜平负'].astype(str).str.strip()

for c in ['模型主胜','模型和局','模型客胜']:
    df[c] = pd.to_numeric(df[c], errors='coerce')

# 模型判主胜的场次
sub = df[(df['模型主胜'] >= df['模型客胜'])].copy()
print(f"模型判主胜场次: {len(sub)}")
print(f"其中实际和局: {(sub['实际胜平负'].astype(str).str.strip() == '和局').sum()} ({(sub['实际胜平负'].astype(str).str.strip() == '和局').mean()*100:.1f}%)")
print()

# 按和局概率分 5 档
sub['和局档'] = pd.cut(sub['模型和局'], bins=[0,15,20,25,30,100], labels=['<15%','15-20%','20-25%','25-30%','30%+'])

print("=== 模型判主胜时，按'和局概率'分档 ===")
print(f"{'和局档':10s} {'场次':6s} {'实际和局':10s} {'实际主胜':10s} {'实际客胜':10s}")
for b in ['<15%','15-20%','20-25%','25-30%','30%+']:
    s = sub[sub['和局档'] == b]
    if len(s) == 0: continue
    a = s['实际胜平负'].astype(str).str.strip()
    d = (a == '和局').sum(); h = (a == '主胜').sum(); k = (a == '客胜').sum()
    print(f"{b:10s} {len(s):6d} {d:6d} ({d/len(s)*100:4.1f}%) {h:6d} ({h/len(s)*100:4.1f}%) {k:6d} ({k/len(s)*100:4.1f}%)")

print()
print("=== 同理，看'客胜'方向的 ===")
sub2 = df[(df['模型客胜'] > df['模型主胜'])].copy()
print(f"模型判客胜: {len(sub2)} 场，实际和局 {(sub2['实际胜平负'].astype(str).str.strip() == '和局').sum()} ({(sub2['实际胜平负'].astype(str).str.strip() == '和局').mean()*100:.1f}%)")