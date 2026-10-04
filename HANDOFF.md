# Football Predict 交接（V5.9）

> 本文件是唯一交接入口。接手时先读本文件。
> 每个文件、每个改动、每个坑，都必须记在这里。

## 一、快速上手

1. 读「文档地图」→ 知道每个文件干什么
2. 读「当前能力」→ 知道系统能做什么
3. 读「关键结论」+「避雷」→ 知道哪些坑踩过
4. 改代码前：先诊断（读代码 / grep / 拉数据），再动手
5. 每步只改一处 → git --no-pager diff 确认 → python -c "import ast; ast.parse(...)" 验语法 → push
6. push 后 1-2 分钟 Streamlit Cloud 自动部署

## 二、文档地图

### 核心代码

| 文件 | 作用 |
|---|---|
| app.py | Streamlit UI，7 Tab（Tab1 显示、Tab2 选场/比分串/稳健串、Tab6 回测、Tab7 筛选）|
| engine.py | 模型核心（predict_full_dc、parse_prediction、backtest_one、fetch_all_predictions、compute_model_asian_handicap）|
| data.py | 常量（DIXON_COLES_RHO、MATCH_TIER_MULTIPLIER、BLEND_WEIGHT_MODEL、TEAM_CN 1520队、LEAGUE_CN、LEAGUE_GRADE）|

### 运行脚本

| 文件 | 作用 | 命令 |
|---|---|---|
| run_bt.py | 回测 → detail.csv | python run_bt.py 2026-07-01 2026-10-03 |
| make_report.py | detail.csv → report_v58.csv | python make_report.py |
| summary_all.py | 详细统计（打印）| python summary_all.py |
| run_all.sh | 一键回测+报告+归档 | bash run_all.sh [起] [止] |
| check_health.py | 静态检查 | python check_health.py |

### 产物

| 文件 | 内容 | 备注 |
|---|---|---|
| detail.csv | 回测明细 | gitignore，不提交，不贴对话 |
| report_v58.csv | 汇总报告 | 追踪，每次重跑更新 |

### 文档

| 文件 | 作用 |
|---|---|
| HANDOFF.md | 本文件，唯一交接入口 |
| README.md | GitHub 首页简介 |

### 归档

| 目录 | 内容 |
|---|---|
| _diag/ | 49 个诊断脚本（一次性）|
| _history/ | 17 个历史 summary 快照 |

## 三、系统架构
