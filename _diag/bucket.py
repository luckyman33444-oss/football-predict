import pandas as pd
df = pd.read_csv('detail.csv')
for c in ['胜平负概率','大小球概率']:
    df[c] = pd.to_numeric(df[c].astype(str).str.extract(r'(\d+\.?\d*)')[0], errors='coerce')
def to_bool(s): return s.astype(str).str.strip().str.lower().map({'true':True,'false':False})
for c in ['胜平负命中','大小球命中','亚盘命中']:
    df[c] = to_bool(df[c])
B=[0,45,50,55,60,65,70,75,80,101]
L=['<45','45-50','50-55','55-60','60-65','65-70','70-75','75-80','80+']
for pc,hc,name in [('胜平负概率','胜平负命中','胜平负'),('大小球概率','大小球命中','大小球')]:
    d=df[[pc,hc]].dropna().copy()
    d['桶']=pd.cut(d[pc],bins=B,labels=L,right=False)
    g=d.groupby('桶',observed=False).agg(场次=(hc,'size'),概率均值=(pc,'mean'),实际命中=(hc,'mean'))
    g['概率均值']=g['概率均值'].round(1)
    g['实际命中']=(g['实际命中']*100).round(1)
    g['偏差']=(g['实际命中']-g['概率均值']).round(1)
    print(f"\n===== {name} (n={len(d)}) =====")
    print(g.to_string())
print(f"\n亚盘命中: {df['亚盘命中'].mean()*100:.1f}% (n={df['亚盘命中'].notna().sum()})")
print(f"胜平负概率 NaN={df['胜平负概率'].isna().sum()}, 范围 {df['胜平负概率'].min()}~{df['胜平负概率'].max()}")
print(f"大小球概率 NaN={df['大小球概率'].isna().sum()}, 范围 {df['大小球概率'].min()}~{df['大小球概率'].max()}")
