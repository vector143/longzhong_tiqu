# 统一三路监控到单一 Rich 界面的实施方案

## Objective

将 `python crawl/investing_monitor.py --monitor --interval 30 --proxy http://127.0.0.1:7897`、`python -m crawl.multi_commodity_monitor --interval 30`、`python -m monitor.runner --keywords "原油,甲醇,PTA,乙二醇,铜,白银,橡胶,天然橡胶" --no-history` 统一到一个单进程 Rich 控制台入口，同时保留三路现有的启动语义、预检、暂停恢复、立即运行、错误展示、轮询节奏和输出行为。成功标准不是做出一个更好看的面板，而是让统一入口能够正式替代人工同时盯三条命令的工作方式，并且不把现有 demo 级统一原型误当成正式架构，参考 `unified_monitor.py:25-204`、`monitor/unified_ui.py:22-227`、`monitor/runner.py:293-546`。

## Implementation Plan

- [ ] 1. 冻结统一入口的兼容矩阵、参数映射和运行语义基线。
  先把三条现有命令的用户可见行为做成兼容矩阵，包括参数命名、轮询单位、首轮行为、历史抓取、代理、重要快讯过滤、错误退出条件和停止语义。当前统一原型已经提供了按源分组的 CLI 和注册逻辑，但它本质上只做了参数解析、注册 adapter、`start_all()`、`stop_all()` 和 UI 运行，没有把各源的正式预检和运行语义收进来，参考 `unified_monitor.py:25-204`、`monitor/manager.py:11-47`。这一步的目的是先定清楚“统一后不能退化的行为”，避免后续只完成了外观统一。

- [ ] 2. 统一状态模型，停止继续扩散两套同名 `MonitorState`。
  以线程安全、带 `next_poll_time`、`recent_articles`、`poll_history`、`today_*` 统计的 `monitor/state.py:47-270` 作为统一控制台的状态底座，同时把简化版 `monitor/adapter.py:25-36` 明确为待迁移对象或重命名为 source snapshot，避免同名不同义继续扩散。当前 `UnifiedMonitorUI` 只能消费 `status`、`last_run`、`items_count`、`total_items` 和 `extra` 这类粗粒度状态，无法承载正式监控所需的轮询历史、最近文章、下次执行时间和暂停态语义，参考 `monitor/unified_ui.py:68-132`。这一步决定统一 Rich 方案最终是正式监控台还是展示层卡片。

- [ ] 3. 把 LongZhong 从临时 adapter 迁回正式 `runner/scheduler/state` 链路。
  `LongZhongAdapter` 当前重新手写了 Cookie 加载、历史抓取和轮询循环，只在 adapter 内部做简化计数与错误处理，甚至把 `items_count` 按关键词轮次累加，而不是按真实文章结果累加，参考 `monitor/adapters.py:202-317`。与之相比，正式入口 `monitor/runner.py:321-546` 已经包含 `--no-history` 提示、关键词重叠提示、PID 保护、启动前预检、上传器初始化、共享请求闸门、统一调度器和优雅清理；而 `monitor/scheduler.py:152-478` 已经包含立即执行、暂停恢复、等待当前轮询结束和下次执行时间同步。统一方案必须复用这套正式链路，只抽出可嵌入统一控制台的服务层或控制器，而不是继续复制主循环逻辑。

- [ ] 4. 为 WallStreetCN 和 Investing 补齐事件化运行接口与可观测性。
  当前 `WallStreetCNAdapter` 和 `InvestingAdapter` 仍然是“循环里顺手改状态”的实现风格，只能提供总数、最后频道、轮次等粗状态；同时 Investing 还把 `delay=3.0` 和 `max_pages=3` 硬编码在适配层，参考 `monitor/adapters.py:21-199`。要让三源在统一 Rich 中拥有可比语义，需要为它们补齐与隆众一致的 source controller 接口，至少统一暴露启动、停止、暂停、恢复、立即运行、下次运行时间、最近产出、最近错误和运行统计，并让每轮任务以结构化事件回写统一状态模型。

- [ ] 5. 扩展统一编排层，从 `start/stop` 容器升级为真正的控制平面。
  现有 `MonitorManager` 只有注册、启动、停止和取状态能力，无法支撑 Rich 控制台需要的 source 级 `pause`、`resume`、`run_now`、`restart`、source 选择和健康快照，也无法统一处理异步停止与等待当前轮询完成，参考 `monitor/manager.py:11-47`。需要把它升级为统一编排器，管理全局动作与单源动作，并约束每个 source controller 提供一致生命周期接口。这样 UI 才能对三源发出真正可执行的控制命令，而不是只能展示静态卡片。

- [ ] 6. 以 `monitor/ui.py` 为设计母版，重做统一 Rich 布局和交互。
  现有 `monitor/unified_ui.py:39-227` 只是头部加多张状态卡片，缺少成熟 UI 已有的快捷键、统计面板、最近文章、轮询历史和错误副标题等能力；同时它把所有 `interval` 一律显示成秒，与隆众的分钟语义不一致，参考 `monitor/unified_ui.py:120-121`。相比之下，`monitor/ui.py:32-342` 已经形成了完整的交互约定，包括 `Q` 退出、`R` 立即运行、`P` 暂停继续、今日统计、最近文章和轮询历史。统一 UI 应该沿用这套交互心智，做成“全局汇总 + 源列表 + 选中源详情”的单界面，而不是三个互不关联的卡片。

- [ ] 7. 设计统一入口和参数兼容策略，保证迁移成本可控。
  统一入口应保留当前 `unified_monitor.py:52-132` 的 namespaced 参数方向，但要把三源的正式参数、预检、冷启动提示和默认值兼容进去。例如隆众的 TTY 判定、`--no-history` 冷启动提示、关键词重叠提示和 PID 保护来自 `monitor/runner.py:314-390`；WallStreetCN 的频道与 `important_only`、Investing 的代理和分页节奏也要映射为统一入口的明确参数，而不是藏在 adapter 内部默认值里。目标是让用户通过统一入口得到与原命令等价的运行语义，而不是拿到一个更简化的外壳。

- [ ] 8. 规划分阶段迁移、灰度切换和可回滚发布路径。
  第一阶段只让统一入口并排调起三路正式 source controller，保留原三条命令继续可用；第二阶段补齐统一 UI 交互和 source 级控制；第三阶段再考虑把统一入口设为默认值守方式。每个阶段都要保留原命令作为回退路径，直到统一入口通过 parity smoke 和稳定性观察，避免一次性切换造成监控盲区。

- [ ] 9. 补齐测试与 smoke 验证，按行为等价而不是界面能显示来验收。
  验证重点不是 UI 能亮起来，而是统一入口在三源上的首轮行为、暂停恢复、立即运行、异常恢复、优雅退出和累计统计是否与原命令一致。隆众现有的调度与 UI 语义可直接参考 `monitor/scheduler.py:152-478`、`monitor/ui.py:88-342`，而统一原型的现状可参考 `unified_monitor.py:137-204`。需要为状态聚合、控制命令和退出清理补单元测试或集成 smoke，用行为等价来定义“统一成功”。

## Verification Criteria

- 统一入口启动后，三源都能在同一 Rich 界面中看到独立状态、下次轮询、最近错误、最近产出和累计统计，而不是只剩粗粒度 `items_count` 与 `total_items`。
- LongZhong 在统一入口下仍保留 PID 保护、启动前预检、`--no-history` 提示、共享请求闸门与优雅清理语义，与 `monitor.runner` 的行为等价。
- WallStreetCN 和 Investing 在统一入口下支持暂停、恢复、立即运行和停止，并能把每轮结果转成统一状态事件，而不是只更新裸计数。
- 统一入口的参数兼容层可以覆盖当前三条常用命令的核心参数，不要求用户手工改业务配置文件才能迁移。
- 统一入口异常退出或收到 `SIGINT`、`SIGTERM` 时，不会留下悬挂线程、未清理 PID 文件或未完成的上传资源。
- 原三条命令在迁移期内仍可独立运行，作为统一入口的回滚手段。

## Potential Risks and Mitigations

1. **LongZhong 迁移时把正式 runner 能力降级成 demo 适配器**
   Impact: 统一 UI 看起来更完整，但启动前预检、PID 保护、共享限流和清理链路丢失，监控稳定性反而下降。
   Likelihood: High
   Mitigation: 明确要求统一控制台复用 `monitor/runner.py:321-546` 和 `monitor/scheduler.py:152-478` 的正式能力，只抽服务层，不复制主循环。
   Contingency: 在统一入口切换前保留 `python -m monitor.runner` 作为同版本回退入口。

2. **状态模型合并不当，导致三源字段语义不一致**
   Impact: UI 可以渲染，但不同源的“本轮”“总计”“下次轮询”“错误态”不可比较，操作会误导值守人员。
   Likelihood: High
   Mitigation: 先定义统一 source snapshot 契约，再让各源映射进入；以 `monitor/state.py:47-270` 的 richer model 为核心，而不是继续堆 `extra`。
   Contingency: 如果完全统一字段成本过高，先采用“公共字段 + source 专属 detail 区”的两层模型，避免错误抽象。

3. **统一控制平面带来并发与停机语义复杂度**
   Impact: 暂停、恢复、立即运行和停止在不同源上行为不同，甚至留下未结束线程。
   Likelihood: Medium
   Mitigation: 要求每个 source controller 明确实现生命周期接口，并把“等待当前任务完成”的行为做成编排层契约，参照 `monitor/scheduler.py:188-235`、`monitor/runner.py:521-546`。
   Contingency: 若某源短期无法安全支持暂停和恢复，则在 UI 中显式降级为停止和启动，避免提供假按钮。

4. **参数兼容层过度追求一键统一，导致 CLI 变得不可维护**
   Impact: 入口参数爆炸，用户不清楚哪些参数对哪个源生效。
   Likelihood: Medium
   Mitigation: 继续采用 source namespace 设计，保持 `--lz-*`、`--wsj-*`、`--inv-*` 前缀，并在统一帮助文档中明确默认值和适用范围，参考 `unified_monitor.py:52-132`。
   Contingency: 如果统一 CLI 过重，可拆成“统一入口 + 源专属 profile 配置”，但仍保留单一 Rich 界面。

## Alternative Approaches

1. **继续沿用当前 `unified_monitor.py` 原型并逐步打补丁**
   Description: 在 `monitor/adapter.py`、`monitor/manager.py`、`monitor/unified_ui.py` 上持续叠功能。
   Pros: 初始改动小，能较快做出一个更好看的统一界面。
   Cons: 会把两套 `MonitorState` 和两套运行语义继续坐实，LongZhong 仍停留在临时 adapter 逻辑，后续维护成本更高。
   Recommendation: 不推荐作为正式路线，只适合做过渡验证。

2. **用 subprocess 直接包三条现有命令并抓取 stdout 和 stderr**
   Description: 统一界面只负责拉起三个子进程，再解析输出拼装卡片。
   Pros: 对现有业务代码侵入最小，短期能把三个程序放进一个屏幕。
   Cons: 输出解析脆弱、控制粒度差、无法稳定实现暂停和立即运行、难以拿到结构化状态，长期会非常脆。
   Recommendation: 不推荐，最多用于临时演示。

3. **以 `monitor.runner` 的成熟状态、调度和 UI 体系为底座，三源统一接入**
   Description: 把隆众现有的正式 `state + scheduler + ui` 思路提升为通用编排内核，再让 WallStreetCN 和 Investing 提供同构 source controller。
   Pros: 能复用现有成熟的生命周期、交互和状态语义，最有机会做成正式统一入口。
   Cons: 初期重构量比打补丁大，需要先做状态和控制接口统一。
   Recommendation: 推荐路线。

## Assumptions

- 统一 Rich 界面的目标是单进程单屏值守，而不是仅仅减少命令行数量。
- 迁移期允许原三条命令继续存在，统一入口不是一次性强制替换。
- LongZhong 的正式运行语义以 `monitor.runner` 为准，而不是以 `LongZhongAdapter` 当前实现为准。
- WallStreetCN 和 Investing 可以接受补充结构化状态事件与控制接口，不要求完全保留当前 adapter 内部实现。

## Dependencies

- 需要先定义三源共同的生命周期接口与状态快照契约，作为统一编排层的设计前提。
- 需要保持 Rich、APScheduler 和现有 crawler 依赖版本稳定，避免在统一过程中引入额外 UI 框架。
- 需要保留现有输出链路、代理配置、Cookie 管理和上传器配置，避免统一入口绕开现有运维依赖。
- 需要为统一入口补充 smoke 场景与回归验证脚本，否则无法判断是否真正达成三路 parity。

## Notes

- 结论不是“能不能做”，而是“能做，但当前仓库里的统一原型还不足以正式替代三条命令”。
- 最大结构性问题不是 UI，而是状态模型和 LongZhong 接入方式；这两个问题不解决，统一 Rich 只会停留在展示层 demo。
- 推荐顺序是先统一内核语义，再统一界面表现，最后再做默认入口切换。
