# ⚽ Football Predict

足球比赛预测系统（Dixon-Coles 模型 + 市场盘口融合）。

## 核心文件
- `app.py` — Streamlit UI（7 个 Tab）
- `engine.py` — 模型 + 回测 + Excel
- `data.py` — 常量（rho、tier 乘数、队名中文映射）
- `run_bt.py` — 回测脚本：`python run_bt.py 2026-07-01 2026-10-03`

## 工具
- `make_report.py` — 生成 report_v58.csv
- `summary_all.py` — 详细统计（打印到屏幕）
- `check_health.py` — 静态健康检查
- `run_all.sh` — 一键跑回测 + 报告 + 归档

## 文档
- `HANDOFF.md` — 交接文档（含关键结论与待办）

## 部署
Push 到 main 后，Streamlit Cloud 自动部署（1-2 分钟）。
