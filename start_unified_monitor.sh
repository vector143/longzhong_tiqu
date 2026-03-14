#!/bin/bash
# 统一监控系统快捷启动脚本
# 等价于运行三个独立的监控命令

cd "$(dirname "$0")"

echo "=========================================="
echo "🚀 启动统一监控系统"
echo "=========================================="
echo ""
echo "等价于运行以下三个命令："
echo "1. python -m monitor.runner --keywords \"原油,甲醇,PTA,乙二醇,铜,白银,橡胶,天然橡胶\" --no-history"
echo "2. python -m crawl.multi_commodity_monitor --interval 30"
echo "3. python crawl/investing_monitor.py --monitor --interval 30 --proxy http://127.0.0.1:7897"
echo ""
echo "=========================================="
echo ""

# 运行统一监控
python unified_monitor.py
