# Football Predict 交接（V5.9）

> 本文件是唯一交接入口。接手时先读本文件。
> 每个文件、每个改动、每个坑，都必须记在这里，否则下次接手会重复踩坑。

## 一、快速上手（AI / 人类通用）

1. 读本文件的「文档地图」→ 知道每个文件干什么
2. 读「当前能力」→ 知道系统现在能做什么
3. 读「关键结论」+「避雷」→ 知道哪些坑踩过
4. 改代码前：先诊断（读代码 / 跑 grep / 拉数据），再动手
5. 每步只改一处 → `git --no-pager diff` 确认 → `python -c "import ast; ast.parse(...)"` 验语法 → push
6. push 后 1-2 分钟 Streamlit Cloud 自动部署

## 二、文档地图（每个文件干什么、何时改）

### 核心代码（改动风险高，改前必读）

| 文件 | 作用 | 改什么时动它 |
|---|---|---|
| `app.py` | Streamlit UI，7 个 Tab。含 Tab1 显示、Tab2 选场/比分串/稳健串、Tab6 回测展示、Tab7 筛选 | 改界面 / 交互 / 筛选逻辑 |
| `engine.py` | 模型核心 + 回测 + Excel 导出。含 `predict_full_dc`（DC 模型）、`parse_prediction`（Tab1 数据源）、`backtest_one`（回测）、`fetch_all_predictions`（拉 Bzzoiro）、`compute_model_asian_handicap` | 改算法 / 回测逻辑 / 数据源 |
| `data.py` | 常量。含 `DIXON_COLES_RHO`（rho 参数）、`MATCH_TIER_MULTIPLIER`（分层系数，基本=1.0）、`BLEND_WEIGHT_MODEL`（融合权重）、`TEAM_CN`（1520 队中文映射）、`LEAGUE_CN`、`LEAGUE_GRADE`、`FOOTBALL_API_LEAGUE_IDS` | 加联赛 / 队名 / 调参数 |

### 运行脚本（工具，按需跑）

| 文件 | 作用 | 命令 |
|---|---|---|
| `run_bt.py` | 回测 → 生成 `detail.csv`（每场一行，40+ 列）| `python run_bt.py 2026-07-01 2026-10-03` |
| `make_report.py` | `detail.csv` → `report_v58.csv`（汇总报告）| `python make_report.py` |
| `summary_all.py` | 详细统计（打印到屏幕，不写文件）| `python summary_all.py` |
| `run_all.sh` | 一键：回测 + 报告 + 归档到 `_history/` | `bash run_all.sh [起] [止]` |
| `check_health.py` | 静态检查：语法 + 导入 + 关键函数 + detail.csv 字段 | `python check_health.py` |

### 产物（自动生成，勿手改）

| 文件 | 内容 | 备注 |
|---|---|---|
| `detail.csv` | 回测明细（每场一行）| gitignore，不提交，不贴对话 |
| `report_v58.csv` | 汇总报告（各板块命中率 + 筛选器分桶）| 追踪，每次重跑更新 |

### 文档

| 文件 | 作用 |
|---|---|
| `HANDOFF.md` | **本文件**，唯一交接入口 |
| `README.md` | GitHub 首页简介（文件清单 + 部署说明）|

### 归档（保留历史，不参与运行）

| 目录 | 内容 | 备注 |
|---|---|---|
| `_diag/` | 49 个诊断脚本 | 一次性分析用，可删 |
| `_history/` | 17 个历史 summary 快照 | run_all.sh 自动生成 |

## 三、系统架构（三条数据流）
