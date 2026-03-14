#!/bin/bash
# 测试并发优化版本的监控脚本

echo "=================================="
echo "测试并发优化版 Investing Monitor"
echo "=================================="
echo ""

echo "【测试配置】"
echo "- 频道: commodities (单频道测试)"
echo "- 并发数: 5"
echo "- 限速: 1秒/请求"
echo "- 代理: http://127.0.0.1:7897"
echo ""

echo "开始测试..."
echo ""

time python crawl/investing_monitor.py \
  --channels commodities \
  --proxy http://127.0.0.1:7897 \
  --delay 1.0 \
  --workers 5

echo ""
echo "=================================="
echo "测试完成"
echo "=================================="
