# Platform 模块开发手册

## 模块定位

`VitalAI/platform/` 是系统级平台层，负责跨领域共享的运行时协议与核心机制。

它不属于任何单一业务域，也不直接承担外部接口适配。它解决的是：

- 系统内部怎么通信
- 系统怎么反馈
- 多目标冲突怎么仲裁
- 紧急情况怎么中断
- 运行时怎么聚合、监控、降级、切换

## 当前结构

```text
VitalAI/platform/
├─ messaging/
├─ feedback/
├─ arbitration/
├─ interrupt/
├─ runtime/
├─ observability/
└─ security/
```

## 当前已完成内容

### 1. 协议层

- `messaging/message_envelope.py`
- `feedback/events.py`
- `arbitration/intents.py`
- `interrupt/signals.py`

### 2. runtime 层

- `runtime/event_aggregator.py`
- `runtime/decision_core.py`
- `runtime/health_monitor.py`
- `runtime/shadow_decision_core.py`
- `runtime/snapshots.py`
- `runtime/degradation.py`
- `runtime/failover.py`

当前 snapshot store 状态：

- 默认 `SnapshotStore` 仍是进程内实现，适合单元测试和轻量运行
- `FileSnapshotStore` 是本地开发持久化实现，可跨实例读取历史 snapshot version
- 应通过 application assembly 的环境配置启用文件 store，不要让业务代码直接决定持久化路径

## 子模块要求

### `messaging/`

要求：

- 定义系统内部统一消息表达
- 保持字段稳定、typed、轻量
- 允许 runtime/application/domain 都能复用

不要做：

- 混入具体业务字段
- 直接绑定外部消息中间件实现

交付标准：

- 至少有统一 envelope
- 支持 trace / ttl / ack / priority 这类核心语义

### `feedback/`

要求：

- 统一反馈事件结构
- 为 reporting、observability、学习信号预留标准输入

不要做：

- 把 reporting 逻辑写进 feedback
- 让不同领域各自定义一套反馈格式

交付标准：

- 能清晰表示 event_type / layer / summary / failure / score

### `arbitration/`

要求：

- 提供跨领域可复用的意图表达
- 能让资源需求、目标权重、灵活度进入统一仲裁入口

不要做：

- 在这里直接写某个领域的业务规则

交付标准：

- intent 结构可被 health / daily_life / 未来新领域共同消费

### `interrupt/`

要求：

- 提供中断等级、动作、快照引用的统一表达
- 让 failover / degradation / snapshot 能共享语义

不要做：

- 把具体切换逻辑写进 signal 对象

交付标准：

- 能表达优先级、动作、原因、快照引用

### `runtime/`

要求：

- 保持组件拆分
- 保持 decision core 轻量
- 让 event aggregator / health monitor / shadow / failover / degradation 各司其职
- snapshot store 的持久化实现必须保持 typed snapshot contract 稳定

不要做：

- 回退成单体 `supervisor.py`
- 把大量领域逻辑塞进 runtime
- 在 runtime 里反向依赖 HTTP、scheduler 或具体业务接口

交付标准：

- 关键 runtime 组件之间通过 typed contract 交互
- 至少有最小串联验证
- snapshot history 能在启用持久化 store 时跨实例延续

## 代码风格

- 优先 dataclass、枚举、清晰字段名
- 用小方法表达语义
- 注释只解释设计意图，不重复字面行为
- 优先描述“运行时语义”，不是“工程技巧”

## 开发边界

### 可以依赖谁

- `Base/Config`
- `Base/Models`
- `Base/RicUtils`
- `VitalAI/shared`

### 不应该依赖谁

- 不应该深度依赖 `interfaces`
- 不应该引入具体领域判断作为 platform 基础行为

## 推进步骤建议

1. 先确认是“平台协议”还是“平台运行时组件”
2. 检查 `Base` 是否已有通用基础积木
3. 先定义 typed 输入输出
4. 再补运行行为
5. 最后补导出、测试、文档

## 测试建议

优先写：

- contract 对象行为测试
- runtime 串联测试
- failover / degradation / health-monitor 这类状态变化测试

避免：

- 依赖 `VitalAI.main`
- 把 platform 测试写成业务流测试

## 常见错误

- 把业务语义塞进 contract
- 让 runtime 重新长成一个超大对象
- 直接用 `dict[str, Any]` 绕过 typed contract
- 过早绑定外部中间件或持久化细节

## 当前最适合继续做的点

- 继续稳住 runtime 边界
- 补 observability / security 的 typed 接口壳
- 在 `FileSnapshotStore` 基础上补异常文件、清理策略、并发写入边界
- 如果要继续扩展，优先让新能力走现有 contract，而不是另起一套格式
