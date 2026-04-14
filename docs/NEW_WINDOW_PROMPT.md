# 新窗口续接提示词

请在新窗口中使用下面这段提示词：

```text
先阅读：
1. docs/PROJECT_CONTEXT.md
2. docs/CURRENT_STATUS.md
3. docs/NEXT_TASK.md
4. README.md

然后检查本次模块相关的 Base 目录，再继续开发。

当前状态：
1. runtime_signals 结果边界已经稳定
2. runtime_signals_enabled 已经进入 assembly policy，并且 scheduler 默认关闭
3. 现在不要继续打磨结果边界，要转向相邻的 runtime/observability/security 小切片

当前优先方向：
1. 先查看 VitalAI/platform/runtime/
2. 再查看 VitalAI/platform/observability/ 与 VitalAI/platform/security/
3. 优先选择一个最小真实切片继续推进，推荐先看 snapshots / failover signals 如何进入真实 flow 或 assembly 路径
4. 完成后同步更新步骤文档、docs/CURRENT_STATUS.md、docs/NEXT_TASK.md
```

## 补充说明

- 当前不建议继续扩业务 flow
- 当前不建议继续反复打磨 `runtime_signals` 的结果形状
- 当前更适合让更多 runtime signal 真正进入 real flow / assembly / observability 路径
- 验证时优先避开 `VitalAI.main`，因为 `Base` 仍有较重导入副作用
