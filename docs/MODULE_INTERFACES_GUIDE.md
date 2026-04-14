# Interfaces 模块开发手册

## 模块定位

`VitalAI/interfaces/` 负责外部进入系统的方式。

它解决的是：

- HTTP 怎么进入
- scheduler 怎么进入
- consumer 怎么进入
- policy snapshot 怎么暴露

它不负责：

- 业务编排本体
- 领域判断
- 运行角色策略制定

## 当前结构

```text
VitalAI/interfaces/
├─ api/
├─ scheduler/
├─ consumers/
├─ web/
└─ typed_flow_support.py
```

## 当前已完成内容

### API

- `api/app.py`
- `api/routers/typed_flows.py`

### Scheduler

- `scheduler/typed_flow_jobs.py`

### Consumers

- `consumers/typed_flow_consumers.py`

### Shared support

- `typed_flow_support.py`

## 子模块要求

### `api/`

要求：

- 只做请求接收、调用 application、返回结果
- 可暴露策略可见性接口

不要做：

- 把业务编排写在 router 里
- 让 API 拥有 workflow 组装细节

### `scheduler/`

要求：

- 表达定时任务风格入口
- 尽量复用 command/workflow 形状

不要做：

- 直接绕过 application

### `consumers/`

要求：

- 表达事件消费风格入口
- 继续沿用 typed flow 形状

不要做：

- 把消息 broker 细节直接写死在 consumer 逻辑里

### `typed_flow_support.py`

要求：

- 统一复用 assembly 获取
- 统一结果序列化
- 统一策略快照与矩阵序列化

不要做：

- 越权拥有复杂业务逻辑

## 模块风格

- 薄
- 清楚
- 对齐
- 不制造第二套编排

具体来说：

- API / scheduler / consumer 尽量保持同构
- 复用 support 层，不重复组装
- 接口输出尽量稳定、可预测

## 交付标准

- 能驱动 application workflow
- 返回结构化结果
- 测试能覆盖入口行为
- 不需要深入 application 内部细节也能读懂接口职责

## 推进注意事项

### 1. 保持入口薄

一旦某个 router / job / consumer 开始出现越来越多的判断分支，优先检查是不是该下沉到 application。

### 2. introspection 可以有，但不要膨胀

当前策略快照和矩阵是合理的，因为它们帮助判断 stop point。

但不要把 interfaces 演化成运维平台本体。

### 3. 复用 support，而不是复制 shape

新的接口类型如果要接入 typed flow，优先复用：

- assembly 获取
- workflow result 序列化
- policy snapshot 序列化

### 4. role 由入口表达，不由入口发明

接口层可以说“我是 API / scheduler / consumer”，但不要在接口层自己定义新的角色策略。

## 测试建议

优先写：

- route adapter 测试
- scheduler / consumer 入口测试
- policy introspection / matrix 测试

## 常见错误

- 在接口层创建大量业务判断
- 让接口层直接 new 一堆依赖而绕开 assembly
- 同一类输出在不同入口返回不同 shape

## 当前最适合继续做的点

- 如果后续真的需要前端或管理台，可让 `web/` 复用当前 policy introspection 能力
- 如果新增入口类型，优先验证它是否能复用当前 typed flow support，而不是直接开新通道
