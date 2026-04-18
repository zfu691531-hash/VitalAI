# API Smoke Checklist

Date: 2026-04-17

## Update 2026-04-17

As of 2026-04-18, the agent smoke now checks one real internal tool execution too:

- `tool-agent` runs `user_overview_lookup` in read-only mode
- this replaces the older preview-only weather example in the smoke path

For focused `health` verification after the latest query improvements, these two manual reads are now useful:

- `GET /vitalai/flows/health-alerts/{user_id}?status_filter=acknowledged`
- `GET /vitalai/flows/health-alerts/{user_id}/{alert_id}`

For focused `daily_life` verification after the latest query improvements, these two manual reads are now useful:

- `GET /vitalai/flows/daily-life-checkins/{user_id}?urgency_filter=high`
- `GET /vitalai/flows/daily-life-checkins/{user_id}/{checkin_id}`

For focused `mental_care` verification after the latest query improvements, these two manual reads are now useful:

- `GET /vitalai/flows/mental-care-checkins/{user_id}?mood_filter=calm`
- `GET /vitalai/flows/mental-care-checkins/{user_id}/{checkin_id}`

For one lightweight cross-domain read after those domain writes, this aggregated endpoint is now useful too:

- `GET /vitalai/users/{user_id}/overview`

For one lightweight agent-feasibility check after the new agent framework wiring, these endpoints are now useful too:

- `GET /vitalai/agents`
- `GET /vitalai/agents/{agent_id}`
- `POST /vitalai/agents/{agent_id}/dry-run`

## Purpose

这页只回答一个问题：

“现在如果我要快速判断 VitalAI 后端是不是活着、核心接口是不是还能用，我该按什么顺序测？”

它不是完整接口文档，也不是架构说明。
它是最小联调清单，目标是让开发、测试、前端联调都能在 5 到 10 分钟内完成第一次验收。

## Recommended Order

1. 启动后端
2. 跑最小 HTTP smoke
3. 跑 typed flow HTTP smoke
4. 跑自然语言 interactions smoke
5. 跑 user overview smoke
6. 跑 agent registry smoke
7. 只在需要人工排查时，再手动发单条请求

## 1. Start The Server

```powershell
python -m uvicorn VitalAI.main:app --host 127.0.0.1 --port 8124
```

启动后，如果你想先用浏览器做一个最轻量的人工检查，也可以直接打开：

```text
http://127.0.0.1:8124/
```

如果只是想一键启动并顺手做最小体检，也可以：

```powershell
python scripts\dev_start_and_smoke.py --smoke
```

## 2. Minimal HTTP Smoke

用途：
- 确认服务启动成功
- 确认最小健康检查可用
- 确认 `profile_memory` 和 `interactions` 没断

```powershell
python scripts\manual_smoke_http_api.py --output text
```

预期至少看到：
- `VitalAI HTTP smoke: OK`
- `health: OK`
- `profile_memory_write: OK`
- `profile_memory_read: OK`
- `interaction: OK`

## 3. Typed Flow HTTP Smoke

用途：
- 一次性验收四条 typed flow 的写后读闭环
- 适合检查 history / snapshot / SQLite 落盘链路有没有断
- `health` 现在还会顺带验收最小状态流：`raised -> acknowledged -> resolved`

```powershell
python scripts\manual_smoke_typed_flow_http.py --output text
```

覆盖：
- `profile_memory`
- `health`
- `daily_life`
- `mental_care`

预期看到四行 `OK`。

## 4. Natural-Language Interactions Smoke

用途：
- 验收 `/vitalai/interactions` 的自然语言入口契约
- 看 intent recognition、clarification、decomposition guard 是否还正常

```powershell
python scripts\manual_smoke_interactions_http.py --output text
```

覆盖：
- 健康类自然语言输入 -> `HEALTH_ALERT`
- 记忆类自然语言输入 -> `PROFILE_MEMORY_UPDATE`
- 普通问候 -> `clarification_needed`
- 复合输入 -> `decomposition_needed`
- 缺失字段 -> `invalid_request`

这一步特别适合在改过 intent recognition、二层拆分、`/vitalai/interactions` 路由之后执行。

## 5. User Overview Smoke

用途：
- 验收轻量跨域读口是不是把 `profile_memory / health / daily_life / mental_care` 四条现有读模型收起来了
- 适合在改过 overview route、跨域 serializer、或前端联调读口之后执行

```powershell
python scripts\manual_smoke_user_overview_http.py --output text
```

预期至少看到：
- `VitalAI user overview HTTP smoke: OK`
- 四条 seed 行都是 `OK`
- `overview: OK profile_memory=1 health=1 daily_life=1 mental_care=1`

## 6. Agent Registry Smoke

用途：
- 验收 Agent 框架是否已经真正挂到平台和 HTTP 接口上
- 快速看 domain / reporting / platform 三类 agent 是否都能被列出和 dry-run
- 适合在改 `agent registry`、`Tool Agent`、`Privacy Guardian Agent`、`Intelligent Reporting Agent` 之后执行

```powershell
python scripts\manual_smoke_agents_http.py --output text
```

预期至少看到：
- `VitalAI agents HTTP smoke: OK`
- `agent_registry: OK count=7`
- `health_domain_dry_run: OK`
- `tool_dry_run: OK`
- `privacy_dry_run: OK`
- `reporting_dry_run: OK`

## 7. Manual API Checks

只有在 smoke 失败、或者你要看某条接口的具体 JSON 结构时，再去做手工请求。

优先看 README 里的这些段落：
- `Profile Memory 历史验收`
- `Health 历史验收`
- `Daily Life 历史验收`
- `Mental Care 历史验收`
- `用户交互入口验收`

README 已经有可复制的 `Invoke-RestMethod` 示例。

## Troubleshooting

如果 smoke 失败，先按这个顺序判断：

1. 服务是否真的启动在 `127.0.0.1:8124`
2. `GET /vitalai/health` 是否可访问
3. `.env` 是否改坏了核心运行配置
4. 最近修改是否碰到了：
   - `VitalAI/interfaces/api/**`
   - `VitalAI/application/workflows/**`
   - `VitalAI/interfaces/typed_flow_support.py`
5. 如果是自然语言入口失败，再看：
   - `intent recognition`
   - `intent decomposition`
   - `user_interaction_workflow`

## Suggested Daily Use

推荐的最小日常节奏：

1. 改后端入口或 workflow 后，先跑 `pytest tests -q`
2. 起服务后跑 `manual_smoke_http_api.py`
3. 如果改了 typed flow，再跑 `manual_smoke_typed_flow_http.py`
4. 如果改了自然语言入口，再跑 `manual_smoke_interactions_http.py`

这样可以避免“代码看起来没问题，但真实 HTTP 联调已经断了”。
