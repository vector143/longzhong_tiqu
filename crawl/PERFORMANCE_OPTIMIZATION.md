# Investing Monitor 性能优化报告

## 优化概述

针对 `investing_monitor.py` 运行效率低的问题，实施了**方案3：混合并发优化方案**。

## 问题分析

### 原版性能瓶颈
1. **串行处理**：3个频道顺序处理，无法并发
2. **固定延迟累积**：每个请求固定 sleep 3秒，线性放大等待时间
3. **文章详情串行获取**：每篇文章逐个获取，无法并发
4. **无并发控制**：单线程同步方式

### 性能估算（原版）
- 3个频道串行
- 每频道：列表 3秒 + 10篇文章×3秒 = 33秒
- 总耗时：3 × 33 = **99秒**
- 30秒间隔无法满足

## 优化方案

### 核心改进

#### 1. 智能限速器（RateLimiter）
```python
class RateLimiter:
    """替代固定sleep，支持并发环境下的限速"""
    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self.last_request_time = 0
        self.lock = threading.Lock()
```

**优势**：
- 线程安全
- 只在必要时等待
- 支持并发环境

#### 2. 频道级并发
```python
# 使用 ThreadPoolExecutor 并发处理多个频道
with ThreadPoolExecutor(max_workers=len(channels)) as executor:
    futures = {
        executor.submit(self._crawl_channel_incremental, channel, max_pages): channel
        for channel in channels
    }
```

**效果**：3个频道同时处理

#### 3. 文章级并发
```python
# 每个频道内，文章详情并发获取
with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
    futures = [executor.submit(fetch_one, item) for item in news_items]
```

**效果**：每个频道内最多5篇文章同时获取

#### 4. 并发控制
- **Semaphore**：限制最大并发数（默认5）
- **Lock**：保护共享资源（去重数据库、文件写入）
- **线程安全**：所有共享操作都加锁保护

## 性能提升

### 优化后性能估算
- 3个频道并发
- 每频道：列表 1秒 + ceil(10/5)×1秒 = 3秒
- 总耗时：**≈3秒**（频道并发）

### 提速比
- 理论提速：99 / 3 ≈ **33倍**
- 实际提速：考虑网络延迟，预计 **10-20倍**

## 新增参数

### --delay（原有参数，含义变更）
- **原含义**：固定请求延迟
- **新含义**：请求最小间隔（用于限速器）
- **默认值**：1.0秒（原3.0秒）
- **说明**：不再是固定等待，而是智能限速

### --workers（新增参数）
- **含义**：最大并发数
- **默认值**：5
- **说明**：控制同时进行的请求数量
- **建议**：
  - 代理稳定：可设置 8-10
  - 代理不稳定：保持 5
  - 无代理：建议 3

## 使用方法

### 推荐配置（30秒间隔监控）
```bash
python crawl/investing_monitor.py --monitor --interval 30 \
  --proxy http://127.0.0.1:7897 \
  --delay 1.0 --workers 5
```

### 激进配置（更快速度）
```bash
python crawl/investing_monitor.py --monitor --interval 30 \
  --proxy http://127.0.0.1:7897 \
  --delay 0.5 --workers 8
```

### 保守配置（避免被封）
```bash
python crawl/investing_monitor.py --monitor --interval 30 \
  --proxy http://127.0.0.1:7897 \
  --delay 2.0 --workers 3
```

## 兼容性

### 向后兼容
- 所有原有参数保持兼容
- 不指定新参数时使用默认值
- 原有命令仍可正常运行

### 代码改动
- **新增**：RateLimiter 类
- **修改**：crawl_incremental() 方法
- **新增**：_crawl_channel_incremental() 方法
- **新增**：_fetch_articles_concurrent() 方法
- **修改**：__init__() 添加并发参数

## 注意事项

1. **代理稳定性**：并发数过高可能导致代理不稳定
2. **目标站限制**：如遇到频繁429错误，降低并发数或增加延迟
3. **内存占用**：并发会增加内存占用，但影响不大
4. **线程安全**：所有共享资源访问都已加锁保护

## 监控建议

运行时观察：
- 是否有大量请求失败
- 是否触发目标站限流
- 实际完成时间是否满足间隔要求

根据实际情况调整 `--delay` 和 `--workers` 参数。

---

**优化完成时间**：2026-02-11
**优化方案**：方案3 - 混合并发优化
**预期提速**：10-20倍
