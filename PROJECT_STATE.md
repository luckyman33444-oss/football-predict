# Football Predict V5.4 — 项目状态

## 仓库
https://github.com/luckyman33444-oss/football-predict

## 文件清单
- data.py — 固定配置（ESPN_LEAGUES、TEAM_CN、LEAGUE_CN、DIXON_COLES_RHO）
- engine.py — 所有函数（backtest_one、predict_full_dc、pick_best_result 等）
- app.py — Streamlit 界面，Tab1~6
- run_bt.py — 回测脚本，支持命令行参数
- summarize.py — 读 detail.csv，生成 summary.md
- parlay_sim.py — 三串一模拟器（分析用）
- run_all.sh — 一键回测脚本
- PROJECT_STATE.md — 本文件

## V5.4 关键参数
- pick_best_result：已禁用和局，只返回主胜/客胜
- compute_model_asian_handicap 平手门槛 = 0.25
- 比分前5候选：scores[:5]
- summarize.py：联赛标签（精选/普通/避雷）

## 联赛标签
- 精选：意甲、日职联、Pro League、Parva Liga、Superliga、尼日利亚超
- 避雷：阿甲、英冠、哥伦比亚甲、Liga Portugal 2、Copa Libertadores、摩洛哥甲

## 最新回测（2026-07-03 ～ 2026-09-30，3911 场）
- 胜平负 49.3% / 亚盘 50.0% / 大小球 57.2%
- 比分前5命中 31.6%
- 精选 378 场：胜平负 59.8% / 亚盘 62.1% / 比分前5 34.4%
- 避雷 401 场：胜平负 40.1% / 亚盘 41.3%

## 候选数量实验
- 前3: 26.2% / 前5: 31.7% / 前6: 31.8%（前5最佳）

## 已验证无效（勿重试）
- 和局条件 0.32/0.05：和局命中率反降
- 平手门槛 0.30：无增益
- 黑名单反向买：29.5%，平局吃掉30%，不可行
- 比分候选按主胜/客胜方向锁死：降到 21%，方向错时必错

## 三串一投注结论
- 比分三串一：前2候选命中0.43%，前3候选27注2.49%，成本高
- 胜平负三串一：全量命中约12.7%
- 比分/胜平负三串一按固定赔率都亏，需真实赔率验证
- 保本单可考虑但收益薄

## 下一步（待办）
1. 决定 Tab7 是否做实
2. 观察 1-2 周新数据验证模型
3. 研究比分前5候选能否进一步扩大覆盖

## 回测流程
python run_bt.py
python summarize.py
cat summary.md

明细 detail.csv 留在 Codespaces，不要贴对话。