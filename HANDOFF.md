cd /workspaces/football-predict

cat > HANDOFF.md << 'HEOF'
# Football Predict 交接（V5.8）

> 本文件是**唯一交接入口**。接手时先读本文件，再按「文档地图」定位需要的文件。

## 一、快速上手（AI / 人类通用）

1. 读本文件的「文档地图」→ 知道每个文件干什么
2. 读「当前能力」→ 知道系统现在能做什么
3. 读「关键结论」→ 知道哪些坑踩过
4. 改代码前：先诊断（读代码/跑命令），再改，改完 `python -c "import ast; ast.parse(open('X.py').read())"` 验语法
5. 每步只改一个地方，`git --no-pager diff` 确认，再 push
6. push 后 1-2 分钟 Streamlit Cloud 自动部署

## 二、文档地图

### 核心代码（改动风险高，改前必读）
| 文件 | 作用 | 何时改 |
|---|---|---|
| `app.py` | Streamlit UI，7 个 Tab | 改界面/交互/筛选器 |
| `engine.py` | 模型 + 回测 + Excel 导出 | 改算法/回测逻辑 |
| `data.py` | 常量：DIXON_COLES_RHO、MATCH_TIER_MULTIPLIER、BLEND_WEIGHT_MODEL、TEAM_CN(1520队)、LEAGUE_CN、LEAGUE_GRADE | 加联赛/队名/调参数 |

### 运行脚本（工具，按需跑）
| 文件 | 作用 | 命令 |
|---|---|---|
| `run_bt.py` | 回测 → 生成 `detail.csv` | `python run_bt.py 2026-07-01 2026-10-03` |
| `make_report.py` | `detail.csv` → `report_v58.csv` 汇总 | `python make_report.py` |
| `summary_all.py` | 详细统计（打印屏幕，不写文件）| `python summary_all.py` |
| `run_all.sh` | 一键：回测 + 报告 + 归档到 `_history/` | `bash run_all.sh [起] [止]` |
| `check_health.py` | 语法 + 导入 + 关键函数 + detail.csv 字段检查 | `python check_health.py` |

### 产物（自动生成，勿手改）
| 文件 | 内容 |
|---|---|
| `detail.csv` | 回测明细（每场一行，40+ 列），gitignore |
| `report_v58.csv` | 汇总报告（各板块命中率 + 筛选器分桶）|

### 文档
| 文件 | 作用 |
|---|---|
| `HANDOFF.md` | **本文件**，交接入口 |
| `README.md` | GitHub 首页简介（文件清单 + 部署说明）|

### 归档（保留历史，不参与运行）
| 目录 | 内容 |
|---|---|
| `_diag/` | 49 个诊断脚本（一次性分析用）|
| `_history/` | 17 个历史 summary 快照 |

## 三、系统架构（三条数据流）
