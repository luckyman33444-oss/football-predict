import pandas as pd
df = pd.read_csv('detail.csv')
df = df[df['前3候选'].notna()].copy()
df['hit'] = (df['前3命中'].astype(str).str.strip() == '✅')
df['O'] = pd.to_numeric(df['大小球概率'].astype(str).str.extract(r'(\d+)')[0])

B = [50,55,60,65,70,75,100]
L = ['50-55','55-60','60-65','65-70','70-75','75+']
df['桶'] = pd.cut(df['O'], bins=B, labels=L, right=False)

g = df.groupby('桶', observed=False).agg(
    场次=('hit','size'),
    大小球实际命中=('大小球命中', lambda x:(x.astype(str).str.strip()=='True').mean()*100),
    前3命中=('hit','mean')
)
g['大小球实际命中'] = g['大小球实际命中'].round(1)
g['前3命中'] = (g['前3命中']*100).round(1)
print(g.to_string())