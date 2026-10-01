import time
import pandas as pd

df = pd.read_csv("detail.csv")

def rate(series):
    s = series.astype(str).str.lower()
    return s.isin(["true", "1", "是", "命中"]).mean()

lines = []
lines.append(f"总场次: {len(df)}")

if "胜平负命中" in df.columns:
    lines.append(f"胜平负命中率: {rate(df['胜平负命中']):.1%}")
if "亚盘命中" in df.columns:
    ah = df["亚盘命中"].dropna()
    ah = ah[ah.astype(str).str.lower() != "none"]
    lines.append(f"亚盘有效: {len(ah)}，命中率: {rate(ah):.1%}")
if "大小球命中" in df.columns:
    lines.append(f"大小球命中率: {rate(df['大小球命中']):.1%}")

if "胜平负推荐" in df.columns and "胜平负命中" in df.columns:
    lines.append("\n按胜平负推荐:")
    for k, g in df.groupby("胜平负推荐"):
        lines.append(f"  {k}: {len(g)}场，{rate(g['胜平负命中']):.1%}")

if "亚盘方向" in df.columns and "亚盘命中" in df.columns:
    lines.append("\n按亚盘方向:")
    def ah_key(x):
        s = str(x)
        if "主让" in s or "主讓" in s: return "主让"
        if "客让" in s or "客讓" in s: return "客让"
        return "平手/观望"
    df["_ah"] = df["亚盘方向"].map(ah_key)
    for k, g in df.groupby("_ah"):
        if k == "平手/观望":
            lines.append(f"  {k}: {len(g)}场，不计命中")
        else:
            lines.append(f"  {k}: {len(g)}场，{rate(g['亚盘命中']):.1%}")

if "置信度" in df.columns and "胜平负命中" in df.columns:
    lines.append("\n按置信度:")
    bins = [0, 55, 70, 85, 100]
    labels = ["<55%", "55-70%", "70-85%", "85%+"]
    df["_conf"] = pd.cut(df["置信度"], bins=bins, labels=labels, right=False)
    for k, g in df.groupby("_conf", observed=True):
        lines.append(f"  {k}: {len(g)}场，胜平负 {rate(g['胜平负命中']):.1%}")

# 保存带时间戳的历史汇总
text = "\n".join(lines)
with open("summary.md", "w", encoding="utf-8") as f:
    f.write(text)

stamp = time.strftime("%Y%m%d_%H%M")
with open(f"summary_{stamp}.md", "w", encoding="utf-8") as f:
    f.write(text)

print(f"summary saved to summary.md (and summary_{stamp}.md)")