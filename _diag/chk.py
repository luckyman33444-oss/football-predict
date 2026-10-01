import pandas as pd
df = pd.read_csv('detail.csv')
for c in ['前3候选','前3命中','主力比分命中','备选比分命中','主力比分','备选比分','实际比分']:
    print(f"--- {c} ---")
    print(df[c].astype(str).value_counts(dropna=False).head(5))
    print()
