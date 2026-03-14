# 统一监控系统 - 配置对比

## 命令等价性

运行 `python unified_monitor.py` 等价于同时运行以下三个命令：

### 1. 隆众资讯监控
```bash
python -m monitor.runner \
  --keywords "原油,甲醇,PTA,乙二醇,铜,白银,橡胶,天然橡胶" \
  --no-history
```

### 2. 华尔街见闻监控
```bash
python -m crawl.multi_commodity_monitor --interval 30
```

### 3. Investing.com 监控
```bash
python crawl/investing_monitor.py \
  --monitor \
  --interval 30 \
  --proxy http://127.0.0.1:7897
```

## 默认配置对比

| 监控源 | 原命令参数 | unified_monitor.py 默认值 | 说明 |
|--------|-----------|--------------------------|------|
| **隆众资讯** | | | |
| 关键词 | `--keywords "原油,甲醇,PTA,乙二醇,铜,白银,橡胶,天然橡胶"` | `--lz-keywords "原油,甲醇,PTA,乙二醇,铜,白银,橡胶,天然橡胶"` | ✅ 完全一致 |
| 轮询间隔 | 默认 30 分钟 | `--lz-interval 30` (分钟) | ✅ 完全一致 |
| 历史爬取 | `--no-history` | 默认 `no_history=True` | ✅ 跳过历史爬取 |
| **华尔街见闻** | | | |
| 频道列表 | 默认 5 个商品频道 | `--wsj-channels commodity-channel oil-channel gold-channel gold-forex-channel goldc-channel` | ✅ 完全一致 |
| 轮询间隔 | `--interval 30` (秒) | `--wsj-interval 30` (秒) | ✅ 完全一致 |
| **Investing.com** | | | |
| 频道列表 | 默认 3 个频道 | `--inv-channels commodities economic-indicators economy` | ✅ 完全一致 |
| 轮询间隔 | `--interval 30` (秒) | `--inv-interval 30` (秒) | ✅ 完全一致 |
| 代理地址 | `--proxy http://127.0.0.1:7897` | `--inv-proxy http://127.0.0.1:7897` | ✅ 完全一致 |

## 快速启动

### 方式 1: 直接运行 Python 脚本
```bash
python unified_monitor.py
```

### 方式 2: 使用启动脚本
```bash
./start_unified_monitor.sh
```

### 方式 3: 使用 Python 模块方式
```bash
python -m unified_monitor
```

## 自定义配置示例

如果需要修改某些参数，可以覆盖默认值：

```bash
# 修改隆众关键词
python unified_monitor.py --lz-keywords "原油,甲醇"

# 修改华尔街见闻频道
python unified_monitor.py --wsj-channels commodity-channel oil-channel

# 修改 Investing 代理
python unified_monitor.py --inv-proxy http://127.0.0.1:8888

# 修改轮询间隔
python unified_monitor.py --lz-interval 60 --wsj-interval 60 --inv-interval 60

# 禁用某个监控源
python unified_monitor.py --disable-lz  # 只运行华尔街见闻和 Investing
```

## 输出目录

所有监控的数据都保存在同一个目录：
```
output/report/cleaned/
```

文件命名格式：
- 隆众资讯: `YYYY-MM-DD_隆众资讯_标题_文章ID.json`
- 华尔街见闻: `WSJ_YYYYMMDD_文章ID.json`
- Investing.com: `YYYY-MM-DD_Investing.com_标题_文章ID.json`

## Rich 界面预览

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 🎯 统一监控系统 | 运行时间: 00:15:30 | 监控源: 3 | 运行中: 3 | 总采集: 45 │
├──────────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐         │
│ │ 隆众资讯         │ │ 华尔街见闻       │ │ Investing.com    │         │
│ │ 状态: 🟢 running │ │ 状态: 🟢 running │ │ 状态: 🟢 running │         │
│ │ 运行时间: 00:15:30│ │ 运行时间: 00:15:30│ │ 运行时间: 00:15:30│         │
│ │ 本轮采集: 5      │ │ 本轮采集: 8      │ │ 本轮采集: 3      │         │
│ │ 总计采集: 15     │ │ 总计采集: 20     │ │ 总计采集: 10     │         │
│ │ 关键词: 原油,... │ │ 频道数: 5        │ │ 频道数: 3        │         │
│ │ 轮询间隔: 30秒   │ │ 轮询间隔: 30秒   │ │ 轮询间隔: 30秒   │         │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘         │
├──────────────────────────────────────────────────────────────────────────┤
│ 💡 提示: 按 Ctrl+C 停止所有监控                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## 优势对比

### 原方式（三个独立命令）
- ❌ 需要开三个终端窗口
- ❌ 难以统一管理和监控
- ❌ 停止时需要分别 Ctrl+C
- ❌ 无法看到整体运行状态

### 新方式（unified_monitor.py）
- ✅ 单个命令启动所有监控
- ✅ 统一的 Rich 界面展示
- ✅ 一键停止所有监控（Ctrl+C）
- ✅ 实时查看所有监控状态
- ✅ 可选择性启用/禁用监控源
- ✅ 统一的配置管理

## 注意事项

1. **依赖检查**: 确保已安装 `rich` 库
   ```bash
   pip install rich
   ```

2. **代理配置**: Investing.com 监控需要代理，确保代理服务正在运行
   ```bash
   # 检查代理
   curl -x http://127.0.0.1:7897 https://www.investing.com
   ```

3. **Cookie 配置**: 隆众资讯监控需要有效的 Cookie 文件

4. **后台运行**: 建议在 tmux 或 screen 中运行
   ```bash
   # 使用 tmux
   tmux new -s monitor
   python unified_monitor.py
   # Ctrl+B, D 分离会话

   # 重新连接
   tmux attach -t monitor
   ```

## 故障排查

### 问题 1: 某个监控源无法启动
**解决方案**: 使用 `--disable-xxx` 参数禁用有问题的监控源，单独调试

### 问题 2: UI 刷新卡顿
**解决方案**: 降低刷新率
```bash
python unified_monitor.py --refresh-rate 0.5  # 降低到 2 FPS
```

### 问题 3: 代理连接失败
**解决方案**: 检查代理服务或修改代理地址
```bash
python unified_monitor.py --inv-proxy http://127.0.0.1:8888
```
