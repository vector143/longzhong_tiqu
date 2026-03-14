#!/bin/bash
# Investing.com 监控脚本 - 快速启动脚本

# 配置
PROXY="http://127.0.0.1:7897"
OUTPUT_DIR="./output"
DELAY=3
INTERVAL=300

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Investing.com 新闻监控脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查代理是否可用
echo -e "${YELLOW}检查代理连接...${NC}"
if nc -zv 127.0.0.1 7897 2>&1 | grep -q succeeded; then
    echo -e "${GREEN}✅ 代理连接正常${NC}"
else
    echo -e "${RED}❌ 代理连接失败，请检查代理是否运行${NC}"
    echo -e "${YELLOW}提示: 确保代理服务器运行在 127.0.0.1:7897${NC}"
    exit 1
fi

echo ""
echo "请选择运行模式："
echo "1) 首次运行 - 爬取历史文章（每个频道100篇）"
echo "2) 增量爬取 - 单次检查新文章"
echo "3) 持续监控 - 每5分钟自动检查（推荐）"
echo "4) 自定义配置"
echo ""
read -p "请输入选项 (1-4): " choice

case $choice in
    1)
        echo -e "${GREEN}开始爬取历史文章...${NC}"
        python crawl/investing_monitor.py \
            --history 100 \
            --proxy "$PROXY" \
            --output "$OUTPUT_DIR" \
            --delay "$DELAY"
        ;;
    2)
        echo -e "${GREEN}开始增量爬取...${NC}"
        python crawl/investing_monitor.py \
            --proxy "$PROXY" \
            --output "$OUTPUT_DIR" \
            --delay "$DELAY"
        ;;
    3)
        echo -e "${GREEN}启动持续监控模式...${NC}"
        echo -e "${YELLOW}按 Ctrl+C 停止监控${NC}"
        python crawl/investing_monitor.py \
            --monitor \
            --interval "$INTERVAL" \
            --proxy "$PROXY" \
            --output "$OUTPUT_DIR" \
            --delay "$DELAY"
        ;;
    4)
        echo ""
        read -p "历史爬取数量 (0=跳过): " history_count
        read -p "是否持续监控? (y/n): " is_monitor
        read -p "检查间隔(秒，默认300): " custom_interval
        read -p "请求延迟(秒，默认3): " custom_delay
        read -p "频道 (all/commodities/economy/economic-indicators): " channels

        custom_interval=${custom_interval:-300}
        custom_delay=${custom_delay:-3}

        cmd="python crawl/investing_monitor.py --proxy $PROXY --output $OUTPUT_DIR --delay $custom_delay"

        if [ "$history_count" != "0" ] && [ -n "$history_count" ]; then
            cmd="$cmd --history $history_count"
        fi

        if [ "$is_monitor" = "y" ]; then
            cmd="$cmd --monitor --interval $custom_interval"
        fi

        if [ "$channels" != "all" ] && [ -n "$channels" ]; then
            cmd="$cmd --channels $channels"
        fi

        echo -e "${GREEN}执行命令: $cmd${NC}"
        eval $cmd
        ;;
    *)
        echo -e "${RED}无效选项${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}完成！${NC}"
echo -e "${GREEN}========================================${NC}"
