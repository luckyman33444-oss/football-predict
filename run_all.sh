#!/bin/bash
# 一键跑回测 + 汇总 + 保存带时间戳的结果

# 默认日期，想换就改这两行
START=${1:-2026-07-03}
END=${2:-2026-09-30}

STAMP=$(date +%Y%m%d_%H%M)
mkdir -p history

echo "=== 跑 $START ~ $END ==="
python run_bt.py "$START" "$END"

if [ -f detail.csv ]; then
    cp detail.csv "history/detail_${STAMP}.csv"
fi

python summarize.py

if [ -f summary.md ]; then
    cp summary.md "history/summary_${STAMP}.md"
    echo ""
    echo "=== 结果已保存 ==="
    echo "明细: history/detail_${STAMP}.csv"
    echo "汇总: history/summary_${STAMP}.md"
    echo ""
    cat summary.md
fi