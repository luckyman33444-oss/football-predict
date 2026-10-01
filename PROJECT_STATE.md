# Football Predict V5.4 — 项目状态

## 仓库
https://github.com/luckyman33444-oss/football-predict

## V5.4 关键参数
- pick_best_result: 已禁用和局，只返回主胜/客胜
- compute_model_asian_handicap 平手门槛 = 0.25
- 比分前5候选：score_top3 = scores[:5]
- summarize.py: 联赛标签（精选/普通/避雷）+ MODE 开关

## 联赛标签
- 精选（INCLUDE）：意甲、日职联、Pro League、Parva Liga、Superliga、尼日利亚超
- 避雷（EXCLUDE）：阿甲、英冠、哥伦比亚甲、Liga Portugal 2、Copa Libertadores、摩洛哥甲

## 最新回测结果（2026-07-03 ～ 2026-09-30，3911 场）
- 胜平负 49.3%
- 亚盘 50.0%
- 大小球 57.2%
- 比分前5命中 31.7%
- 精选 378 场：胜平负 59.8% / 亚盘 62.1% / 比分前5 34.4%
- 避雷 401 场：胜平负 40.1% / 亚盘 41.3%

## 候选数量实验
- 前3: 26.2%
- 前5: 31.7%（最佳点）
- 前6: 31.8%（无增益）

## 放弃的方案
- 禁用和局：胜平负升 0.9%
- 平手 0.25：亚盘升 1.5%
- 平手 0.30：无增益
- 和局门槛 0.32：和局命中率反而降到 26%
- 黑名单反向买：反向命中 29.5%，平局吃掉 30%，不可行

## 下一步（待办）
1. 实装 Tab7 三串一模拟器（读 detail.csv，按天分组）
2. 赔率用真实值，不用假设 8 倍
3. 观察 1-2 周新数据，验证模型是否过拟合

## 回测流程
python run_bt.py
python summarize.py
cat summary.md

明细 detail.csv 留在 Codespaces，不要贴对话。