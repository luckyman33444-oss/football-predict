# Football Predict V5.0 — 项目状态

## 仓库
https://github.com/luckyman33444-oss/football-predict

## 文件职责
- data.py — 固定配置
- engine.py — 所有函数（backtest_one、fetch_predictions_range、fetch_events_range、pick_best_result、compute_model_asian_handicap）
- app.py — Streamlit 界面，Tab1~6
- run_bt.py — 批量回测，支持 python run_bt.py 起始日期 结束日期
- summarize.py — 读 detail.csv，生成 summary.md
- run_all.sh — 一键跑回测 + 汇总
- PROJECT_STATE.md — 本文件

## 回测流程（每次三条）

python run_bt.py
python summarize.py
cat summary.md

明细 detail.csv 留在 Codespaces，不要贴对话。

## 当前 engine.py 状态（V5.3 基线）

- pick_best_result 已禁用和局推荐，只返回主胜/客胜：

def pick_best_result(hw, d, aw):
    if hw >= aw:
        return ("主胜", hw)
    return ("客胜", aw)

- compute_model_asian_handicap 平手门槛 = 0.25（不是 0.15）：

if abs_diff < 0.25:

- DIXON_COLES_RHO 未改，仍为 {"top": -0.10, "mid": -0.13, "low": -0.15, "friendly": -0.13}

## 最新回测结果（2026-07-03 ～ 2026-09-30，3911 场）

- 胜平负 49.2%
- 亚盘有效 2591，命中 50.5%
- 大小球 57.2%
- 主力比分完全对 11.2%
- 备选比分方向/完全对 39.7%
- 主胜 2867场 50.0% / 客胜 1044场 46.9%
- 主让 2175场 49.7% / 客让 416场 54.8% / 观望 1320场
- 置信度 <55%: 43.7% / 55-70%: 51.0% / 70-85%: 59.2% / 85%+: 100%

## 已试过但放弃的改动

- 和局条件 0.28/0.10 改 0.32/0.05：和局命中率从 30% 掉到 26%，禁用和局更好
- 平手门槛 0.30：亚盘只升 0.3%，观望多 200 场，不值

## 下一步计划（进行中）

1. 联赛过滤（黑名单 vs 白名单）：
   - 黑名单候选：阿甲、英冠、哥伦比亚甲、Liga Portugal 2、Copa Libertadores、摩洛哥甲
   - 白名单候选：意甲、日职联、Pro League、Parva Liga、Superliga、尼日利亚超
   - 建议在 summarize.py 里加 MODE 开关，不改 engine.py

2. 后续：调 DIXON_COLES_RHO、大小球权重

## 已知 bug / 注意

- backtest_one 签名是 (p, actual_map)，不是 (日期, 联赛)
- git diff 输出长时会被分页卡住，按 q 退出
- engine.py 每次改完不提交也能跑，本地生效