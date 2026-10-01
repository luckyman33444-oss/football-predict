# Football Predict V5.4 — 项目状态

## 仓库
https://github.com/luckyman33444-oss/football-predict

## V5.4 关键参数（已确认）
- pick_best_result：已禁用和局
- 平手门槛 = 0.25
- 比分前5候选：scores[:5]
- summarize.py：联赛标签

## 联赛标签
- 精选：意甲、日职联、Pro League、Parva Liga、Superliga、尼日利亚超
- 避雷：阿甲、英冠、哥伦比亚甲、Liga Portugal 2、Copa Libertadores、摩洛哥甲

## 最新回测（3911 场）
- 胜平负 49.3% / 亚盘 50.0% / 大小球 57.2%
- 比分前5命中 31.6%
- 精选 378 场：59.8% / 62.1% / 34.4%
- 避雷 401 场：40.1% / 41.3%

## 已验证无效的方案（勿重试）
- 和局条件 0.32/0.05：和局命中率反降
- 平手门槛 0.30：无增益
- 黑名单反向买：29.5%，不可行
- **比分候选按主胜/客胜方向锁死：降到 21%，无效**

## 三串一投注结论
- 前2候选 8注：命中率 0.43%，230期中一次，不划算
- 前3候选 27注：2.49%，成本 675 元/期
- 比分三串一数学上打不过（热门比分赔率 5-7 倍，达不到保本线）

## 文件
- app.py / engine.py / data.py：主程序
- run_bt.py：回测
- summarize.py：汇总
- parlay_sim.py：三串一模拟器

## 下一步
1. 决定 Tab7 是否做实（建议按胜平负，不按比分）
2. 观察 1-2 周新数据

## 回测流程
python run_bt.py
python summarize.py
cat summary.md