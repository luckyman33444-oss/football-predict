#!/bin/bash
# 一键跑回测 + 生成报告 + 归档

START=${1:-2026-07-01}
END=${2:-2026-10-03}
STAMP=$(date +%Y%m%d_%H%M)

mkdir -p _history

echo "=== 跑 $START ~ $END ==="
python run_bt.py "$START" "$END"

if [ -f detail.csv ]; then
    cp detail.csv "_history/detail_${STAMP}.csv"
fi

echo ""
echo "=== 生成报告 ==="
python make_report.py
if [ -f report_v58.csv ]; then
    cp report_v58.csv "_history/report_${STAMP}.csv"
fi

echo ""
echo "=== 详细统计 ==="
python summary_all.py | tee "_history/summary_${STAMP}.txt"

echo ""
echo "=== 结果已保存到 _history/ ==="
ls -la "_history/" | tail -5
