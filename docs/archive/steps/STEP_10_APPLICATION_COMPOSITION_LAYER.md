# 第十步：Application Composition Layer 技术拆解

## 文档目的

这份文档记录第十步开发工作的技术落点：把现有 typed flow 的 workflow 组装逻辑，从 `interfaces` 支持层上提到正式的 application composition / assembly 层。

前面几步已经证明：

- `command + use case + workflow` 形状是可行的
- API / scheduler / consumer 都能复用这套形状

这时最自然的下一步，不是继续扩更多入口，而是把“怎么组装应用对象”放到正确位置。

---

## 为什么要做这一步

在第九步结束时，`interfaces/typed_flow_support.py` 同时做了两件事：

1. interface 层共享结果序列化
2. workflow 的依赖组装

其中第 1 件事属于 interface 层。
但第 2 件事更像 application composition 责任。

如果继续把 workflow 组装逻辑留在 interface 层，后面接口一多，会出现一个问题：

`入口适配层慢慢知道太多应用内部组装细节。`

所以这一步把装配逻辑上提，让结构更干净：

- application 负责 assembly
- interfaces 负责 adapter

---

## 文件 1：`VitalAI/application/assembly.py`

### 改动点

新增：

- `build_health_workflow()`
- `build_daily_life_workflow()`

### 技术意义

这一步正式建立了一个轻量 application composition 层。

它当前做的事很简单：

- 组装 runtime 依赖
- 组装 domain service
- 组装 use case
- 组装 workflow

虽然还只是内存内构造，但职责位置已经正确了。

后面如果要做配置驱动、容器装配、依赖替换，这里也会比 interface 层更合适。

---

## 文件 2：`VitalAI/application/__init__.py`

### 改动点

把新的 assembly builder 导出了：

- `build_health_workflow`
- `build_daily_life_workflow`

### 技术意义

这样 application 层不仅有 command / use case / workflow，也开始有正式的装配入口。

---

## 文件 3：`VitalAI/interfaces/typed_flow_support.py`

### 改动点

这个文件不再自己组装 workflow，而是改为调用 application 层的 builder。

保留下来的职责只有：

- 入口层共享 support
- workflow result 序列化

### 技术意义

这一步让 interface support 继续保持小而薄，没有演化成隐藏的 application factory。

---

## 文件 4：`tests/application/test_application_assembly.py`

### 改动点

新增 2 个测试：

1. `build_health_workflow()` 能组装出可执行 workflow
2. `build_daily_life_workflow()` 能组装出可执行 workflow

### 技术意义

这说明 application composition 已经是可验证的正式结构，而不是只有实现没有验证的辅助文件。

---

## 本轮结果

到第十步结束时，系统的职责分布更清晰了：

- application：command / use case / workflow / assembly
- interfaces：API / scheduler / consumer adapter

这一步没有增加新业务能力，但让现有多入口 typed flow 的结构更稳，也为后续引入更真实的依赖装配留下了正确落点。
