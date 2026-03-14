# 华尔街见闻财经日历爬虫

自动爬取华尔街见闻财经日历数据，支持按地区、重要性、类型筛选。

## 功能特点

- 支持按地区筛选：中国、日本、欧元区、美国等
- 支持按重要性筛选：1-5星
- 支持按类型筛选：宏观、财报、假期等
- 支持单次抓取和持续监控两种模式
- 自动保存为JSON格式

## 快速开始

### 单次抓取（默认配置）

```bash
# 抓取中国、美国、日本、欧元区的2星及以上宏观数据
python crawl/calendar_monitor.py --fetch
```

### 自定义筛选条件

```bash
# 只抓取中国和美国的3星及以上事件
python crawl/calendar_monitor.py --fetch --countries 中国 美国 --importance 3

# 指定日期范围
python crawl/calendar_monitor.py --fetch --start 2026-02-10 --end 2026-02-20

# 抓取所有类型（不限类型）
python crawl/calendar_monitor.py --fetch --types 全部
```

### 持续监控模式

```bash
# 每小时检查一次新事件
python crawl/calendar_monitor.py --monitor --interval 3600

# 每30分钟检查一次，只监控3星事件
python crawl/calendar_monitor.py --monitor --interval 1800 --importance 3
```

## 参数说明

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| --fetch | -f | 单次抓取模式 | 是（默认） |
| --monitor | -m | 持续监控模式 | 否 |
| --interval | -i | 监控轮询间隔（秒） | 3600 |
| --countries | -c | 监控的国家/地区 | 中国 美国 日本 欧元区 |
| --importance | | 最低重要性（1-5星） | 2 |
| --types | -t | 日历类型 | 宏观 |
| --start | | 开始日期 (YYYY-MM-DD) | 今天 |
| --end | | 结束日期 (YYYY-MM-DD) | 7天后 |

## 输出格式

数据保存在 `output/calendar/` 目录，文件命名格式：

```
Calendar_{国家代码}_{日期}_{事件ID}.json
```

示例：`Calendar_CN_20260211_12979.json`

### JSON字段说明

```json
{
  "id": 12979,                    // 事件ID
  "title": "事件标题",             // 事件标题
  "country": "中国",               // 国家/地区
  "country_id": "CN",             // 国家代码
  "importance": 4,                // 重要性（1-5星）
  "calendar_type": "FE",          // 类型（FE=财经事件, MD=宏观数据）
  "actual": "",                   // 实际值
  "forecast": "",                 // 预测值
  "previous": "",                 // 前值
  "unit": "",                     // 单位
  "foresight": "前瞻信息...",      // 前瞻分析
  "source": "华尔街见闻财经日历"   // 数据来源
}
```

## 代码使用示例

```python
from crawl.wallstreetcn_calendar import WallStreetCNCalendarCrawler

# 创建爬虫实例
crawler = WallStreetCNCalendarCrawler()

# 获取数据
items = crawler.fetch_and_parse(
    countries=["中国", "美国"],
    min_importance=2,
    calendar_types=["宏观"]
)

# 处理数据
for item in items:
    print(f"{item['country']} - {item['title']}")
```

## 注意事项

1. 默认日期范围为今天到7天后
2. "宏观"类型包含FE和MD两种calendar_type
3. 重要性星级越高，事件越重要
4. 监控模式会自动去重，只处理新事件

## 文件说明

- `wallstreetcn_calendar.py` - 爬虫核心类
- `calendar_monitor.py` - 监控脚本（可执行）
- `output/calendar/` - 数据输出目录
