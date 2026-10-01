# Football Predict V5.0 — 项目状态

## 仓库
https://github.com/luckyman33444-oss/football-predict

## 文件职责
- `data.py` — 固定配置（ESPN_LEAGUES、TEAM_CN、LEAGUE_CN、DIXON_COLES_RHO 等）
- `engine.py` — 所有函数（backtest_one、fetch_predictions_range、fetch_events_range、pick_best_result、compute_model_asian_handicap 等）
- `app.py` — Streamlit 界面，Tab1~6
- `run_bt.py` — 批量回测脚本，支持命令行参数 `python run_bt.py 起始日期 结束日期`
- `summarize.py` — 读取 detail.csv，生成 summary.md（30 行汇总）
- `run_all.sh` — 一键跑回测 + 汇总 + 存档

## 回测流程（每次就这三条）
python run_bt.py 2026-07-03 2026-09-30
python summarize.py
cat summary.md

明细 detail.csv 留在 Codespaces，不要贴对话。

## V5.0 关键参数
- DIXON_COLES_RHO = {"top": -0.10, "mid": -0.13, "low": -0.15, "friendly": -0.13}
- compute_model_asian_handicap 平手门槛 = 0.15
- pick_best_result 和局条件 = d >= 0.28 and (max_prob - d) < 0.10

## 最新一次回测结果（2026-07-03 ～ 2026-09-30，3911 场）
- 胜平负命中率 48.2%
- 亚盘有效 3235，命中率 48.7%
- 大小球命中率 57.3%
- 主胜 2383场 52.7%
- 和局 770场 30.0% ← 最大问题
- 客胜 758场 52.4%
- 主让 2603场 48.1%
- 客让 632场 51.4%
- 平手观望 676场
- 置信度 <55%: 43.8% / 55-70%: 49.4% / 70-85%: 57.9% / 85%+: 100%

## 下一步计划
1. 【进行中】把 pick_best_result 和局条件改成 d >= 0.32 and (max_prob - d) < 0.05，重跑回测对比
2. 调 compute_model_asian_handicap 平手门槛（0.15 → 试 0.12 或 0.10）
3. 过滤差联赛：阿甲、英冠、哥伦比亚甲、Liga Portugal 2、Copa Libertadores、摩洛哥甲

## 已修复的 bug
- backtest_one 签名是 (p, actual_map)，不是 (日期, 联赛)
- Tab6 简繁体识别（主讓/主让、客讓/客让）
- run_bt.py 内部用 contextlib.redirect_stdout 吞掉 backtest_one 的 print