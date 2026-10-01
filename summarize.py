import time
import pandas as pd

# ============ 这里切换模式 ============
# "all"   = 全量（不过滤）
# "black" = 黑名单（踢掉差联赛）
# "white" = 白名单（只留好联赛）
MODE = "black"

EXCLUDE_LEAGUES = {"阿甲", "英冠", "哥伦比亚甲", "Liga Portugal 2", "Copa Libertadores", "摩洛哥甲"}
INCLUDE_LEAGUES = {"意甲", "日职联", "Pro League", "Parva Liga", "Superliga", "尼日利亚超"}
# =====================================

df = pd.read_csv("detail.csv")

# 联赛过滤
if "联赛" in df.columns:
    if MODE == "black":
        df = df[~df["联赛"].isin(EXCLUDE_LEAGUES)].copy()
    elif MODE == "white":
        df = df[df["联赛"].isin(INCLUDE_LEAGUES)].copy()

def rate(series):
    s = series.astype(str).str.lower()
    return s.isin(["true", "1", "是", "命中"]).mean()

lines = []
lines.append(f"模式: {MODE}")
lines.append(f"总场次: {len(df)}")

if "胜平负命中" in df.columns:
    lines.append(f"胜平负命中率: {rate(df['胜平负命中']):.1%}")
if "亚盘命中" in df.columns:
    ah = df["亚盘命中"].dropna()
    ah = ah[ah.astype(str).str.lower() != "none"]
    lines.append(f"亚盘有效: {len(ah)}，命中率: {rate(ah):.1%}")
if "大小球命中" in df.columns:
    lines.append(f"大小球命中率: {rate(df['大小球命中']):.1%}")

if "主力比分命中" in df.columns:
    m = df["主力比分命中"].astype(str)
    valid = m[~m.isin(["—", "-", "nan", "None", ""])]
    if len(valid):
        lines.append(f"主力比分完全对: {len(valid)}场，{valid.str.contains('完全对').mean():.1%}")

if "备选比分命中" in df.columns:
    m = df["备选比分命中"].astype(str)
    valid = m[~m.isin(["—", "-", "nan", "None", ""])]
    if len(valid):
        lines.append(f"备选比分方向/完全对: {len(valid)}场，{valid.str.contains('完全对|方向对').mean():.1%}")

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

text = "\n".join(lines)
with open("summary.md", "w", encoding="utf-8") as f:
    f.write(text)

stamp = time.strftime("%Y%m%d_%H%M")
with open(f"summary_{MODE}_{stamp}.md", "w", encoding="utf-8") as f:
    f.write(text)

print(f"summary saved (mode={MODE})")