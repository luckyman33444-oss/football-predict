import io
import sys
import contextlib
import pandas as pd

from engine import (
    backtest_one,
    fetch_predictions_range,
    fetch_events_range,
)

# 从命令行读日期，不传就用默认 7-9 月
START = sys.argv[1] if len(sys.argv) > 1 else "2026-07-03"
END   = sys.argv[2] if len(sys.argv) > 2 else "2026-09-30"

print(f"① 拉取 {START} ～ {END} 的预测...")
preds, err = fetch_predictions_range(START, END)
if err:
    print("预测拉取失败：", err)
    raise SystemExit(1)
print(f"   拿到 {len(preds)} 条预测")

print("② 拉取实际比分...")
actual_map = fetch_events_range(START, END)
print(f"   拿到 {len(actual_map)} 场比分")

print("③ 开始回测...")
rows = []
for i, p in enumerate(preds):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            r = backtest_one(p, actual_map)
    except Exception:
        continue
    if r:
        # 从原始预测里取日期
        ev = p.get("event", {}) if isinstance(p.get("event"), dict) else {}
        ev_date = ev.get("date") or ev.get("start_time") or ev.get("commence_time") or ""
        r["日期"] = str(ev_date)[:10]
        rows.append(r)
    if (i + 1) % 200 == 0:
        print(f"   已处理 {i+1}/{len(preds)}")

if not rows:
    print("没有任何可回测的比赛。")
    raise SystemExit(1)

df = pd.DataFrame(rows)
df.to_csv("detail.csv", index=False, encoding="utf-8-sig")
print(f"saved {len(df)} rows to detail.csv")
print(f"列名: {list(df.columns)}")