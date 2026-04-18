# VitalAI 系统总体技术文档

> 版本 v1.0 | 2026-04-17
> 基于 docs/archive/design-assets 全部技术设计文档 + 当前代码实现整合输出

---

## 一、项目概述

### 1.1 项目定位

VitalAI 是一个面向养老陪护场景的**服务端多 Agent 智能系统**，核心目标是构建一个能理解老人自然语言、长期记忆偏好与状态、统一调度多个领域 Agent、具备反馈学习与紧急中断能力的"养老智能大脑"。

一句话概括：

> VitalAI = 意图识别 + 长期记忆 + 多Agent调度 + 反馈闭环 + 紧急中断 + 冲突仲裁

### 1.2 核心用户与场景

**主线人物**：王奶奶，72岁，退休教师，独居北京西城区，患高血压，腿脚略有不便。子女在外地工作，每周视频通话一次。

**典型场景**：

| 场景 | 用户输入 | 系统响应 |
|------|---------|---------|
| 简单意图 | "我头晕" | 意图识别→health_alert→写入预警历史→拍快照 |
| 复合意图 | "我心里慌，药还要不要天天吃" | 意图识别→复合意图→LLM拆解→路由守门→返回候选 |
| 日常签到 | "我需要买菜" | daily_life_checkin→写入签到历史 |
| 记忆查询 | "我还记得我喜欢喝什么吗" | profile_memory_query→返回画像快照 |
| 精神关怀 | "人老了，没意思" | mental_care_checkin→HMM情绪感知→记忆触发引导 |

### 1.3 技术栈

| 层面 | 技术选型 |
|------|---------|
| 后端框架 | Python FastAPI |
| 持久化 | SQLite（开发期）/ PostgreSQL + Neo4j（设计目标） |
| 意图识别第一层 | 规则引擎 + 微调 BERT（6类分类） |
| 意图识别第二层 | OpenAI-compatible LLM + Schema校验 + 路由守门 |
| LLM | 通义千问（base_qwen）/ OpenAI-compatible |
| 记忆系统 | Hindsight 四网络架构（W/E/O/S） |
| 健康评估 | Fuzzy Logic + HMM + 贝叶斯 |
| 日常调度 | MAB多臂老虎机 + PSO粒子群优化 + Dijkstra |
| 可观测 | 自研 ObservabilityCollector |
| 安全 | 自研 SensitiveDataGuard + 差分隐私 |
| 测试 | pytest（220+ 测试用例） |

---

## 二、系统架构

### 2.1 总体架构：Base + VitalAI 两层分离

```
d:/VitalAI/
├── Base/            ← 地基：通用技术能力（可跨项目复用）
│   ├── Config/      → 配置中心（Pydantic Settings + .env）
│   ├── Ai/          → LLM 封装（Qwen/DeepSeek 基类）
│   ├── Repository/  → 数据库基类（ORM基类 + SQLite/MySQL/PG连接器）
│   ├── Client/      → 外部客户端（MySQL/Redis/Milvus/MinIO/ASR/Jieba）
│   ├── Service/     → 服务封装（AI/ASR/邮件/LLM会话/调度）
│   ├── RicUtils/    → 通用工具（文件/Excel/PDF/Word/HTTP/Redis/音频/日期）
│   └── Meta/        → 元编程（单例元类）
│
└── VitalAI/         ← 房子：养老业务系统
    ├── application/ → 应用编排层
    ├── platform/     → 平台机制层
    ├── domains/      → 领域层
    ├── interfaces/   → 接口层
    └── shared/       → 共享层
```

**核心原则**：Base 只放通用能力，VitalAI 的业务逻辑绝不塞回 Base。

**VitalAI 实际用到的 Base 能力**：
1. `Config/logConfig` → 日志初始化
2. `Config/setting` → 环境配置读取
3. `Ai/llms/qwenLlm` → 意图分解时的 LLM 调用（可选）
4. `Repository/connections/sqliteConnection` → 领域仓储的数据库连接
5. `Repository/base/baseDBModel` → 领域持久化模型的 ORM 基类

### 2.2 VitalAI 五层洋葱架构

```
        从外到内 ↓

┌──────────────────────────────────────────┐
│  ⑤ interfaces/  接口层                    │  最外层，最薄
│  "外面怎么进来"                            │
│  ┌──────────────────────────────────────┐│
│  │  ④ application/  应用层               ││  编排中心
│  │  "先做什么再做什么"                     ││
│  │  ┌──────────────────────────────────┐││
│  │  │  ③ platform/  平台层              │││  系统机制
│  │  │  "系统怎么运转"                    │││
│  │  │  ┌──────────────────────────────┐│││
│  │  │  │  ② domains/  领域层           ││││  最核心
│  │  │  │  "业务规则是什么"               ││││
│  │  │  └──────────────────────────────┘│││
│  │  └──────────────────────────────────┘││
│  └──────────────────────────────────────┘│
│                                          │
│  ① shared/  共享层（横切，少量通用常量/错误） │
└──────────────────────────────────────────┘
```

**依赖方向**：外层→内层，内层不依赖外层。领域层最纯粹，不知道 HTTP、数据库、消息队列是什么。

**与 MVC / DDD 的对比**：

| 维度 | 传统 MVC | DDD 分层 | 本项目洋葱架构 |
|------|---------|---------|--------------|
| 组织方式 | 按技术角色分 | 按领域分 | 按领域分+横切平台 |
| 系统机制 | 散在各处 | 散在各处 | platform/ 统一 |
| 接口层厚度 | 胖 | 中等 | 极薄 |
| 多Agent协作 | 不支持 | 需自己补 | 原生支持 |
| 运行时韧性 | 无 | 无 | 快照/故障转移/降级开箱即用 |

---

## 三、领域层详细设计

### 3.1 领域总览

```
domains/
├── health/          🏥 健康监测
├── daily_life/      🍚 日常生活
├── mental_care/     💚 心理关怀
├── profile_memory/  🧠 用户画像记忆
└── reporting/       📊 报告反馈
```

每个领域统一包含 `agents/ models/ policies/ repositories/ services/` 五个子目录，结构完全一致。

### 3.2 Health 健康监测领域

#### 3.2.1 核心能力

| 功能 | 技术方案 | 核心设计 |
|------|---------|---------|
| HMM步态异常感知 | 隐马尔可夫模型 | 四状态序列：normal→cautious→unsteady→fall_risk；20步滑动窗口；个体基线校准 |
| Fuzzy Logic血压评估 | 模糊逻辑 | 连续风险分0-1替代硬阈值；个人基线动态校正（同值144，老人A等效158/老人C等效142） |
| 药物冲突检测 | 规则引擎+药品数据库 | 3级冲突严重度（严重/中等/轻微）；自动生成"给医生看的用药清单" |
| 久坐检测 | 传感器加速度+座椅压力 | 阈值45/90/120分钟递增；午睡时段不触发；P1血压异常时不触发运动提醒 |
| 体检报告解读 | OCR+LLM | 识别后结合个人历史对比；分好消息/需关注/建议行动三部分 |

#### 3.2.2 HMM步态感知技术细节

**转移矩阵**（基于老年步态数据训练）：

| 状态 | normal | cautious | unsteady | fall_risk |
|------|--------|----------|----------|-----------|
| normal | 0.90 | 0.08 | 0.015 | 0.005 |
| cautious | 0.15 | 0.70 | 0.12 | 0.03 |
| unsteady | 0.05 | 0.20 | 0.60 | 0.15 |
| fall_risk | 0.02 | 0.08 | 0.30 | 0.60 |

**特征提取**：步长(cm)、步频(步/分)、左右不对称指数(0-1)、加速度方差、落脚冲击力

**个体基线校准**：王奶奶的"正常步长"是38cm（非通用标准50cm），38cm不触发告警，降到30cm才异常

**预警效果**：旧方式=老人摔倒→传感器检测→触发P0（已太晚）；新方式=步态变差→提前30分钟预警→避免摔倒

#### 3.2.3 Fuzzy Logic血压评估

**风险区间**：

| 校正后血压 | Fuzzy评分 | 系统响应 | 推送方式 |
|-----------|----------|---------|---------|
| <130 | 0.0-0.35 | NORMAL | 无推送 |
| 130-145 | 0.35-0.55 | WATCH观察 | 日报中记录趋势 |
| 145-160 | 0.55-0.75 | P1警告 | 主动询问感受，通知家属 |
| 160-180 | 0.75-0.90 | P1紧急 | 立即告警，停止外出计划 |
| >180 | 0.90-1.0 | P0急救 | 拨打120，联系家属 |

**核心差异**：同样的血压值144，对基线120/75的老人A等效158（P1预警），对基线145/92的老人C等效142（NORMAL正常）。

#### 3.2.4 当前实现状态

- ✅ 健康预警写入闭环：HealthAlertTriageService → HealthAlertRepository → SQLite
- ✅ 只读查询闭环：HealthAlertHistoryQuery → use case → workflow → API
- ✅ 最小状态流：新告警默认 `raised`，支持 `acknowledged → resolved` 状态迁移
- ✅ CRITICAL 级别自动触发快照
- ✅ medication_signal 无论 severity 都阻止路由（`_ALWAYS_REVIEW_RISK_KINDS`）

### 3.3 Daily Life 日常生活领域

#### 3.3.1 核心能力

| 功能 | 技术方案 | 核心设计 |
|------|---------|---------|
| MAB推送调度 | 多臂老虎机+Thompson Sampling | 一天8时段探索最优提醒时间；响应率从42%→81% |
| 购物比价 | 协同过滤+Tool Agent比价 | 找相似老年群体偏好；3平台价格对比；只推荐1-2个选项 |
| 近途出行 | 改良Dijkstra | 台阶×10米、坡度×8米重新定义权重；有扶手惩罚减半；步态偏弱时权重×1.5 |
| 远途出行 | PSO粒子群优化 | 多目标：体力0.4+距离0.3+费用0.2+时间0.1；10000+组合快速收敛 |
| 防诈骗 | Knowledge Graph+规则引擎 | 三维识别：陌生号码+官方词汇+要求转账；久未联系突然借钱；价格虚高保健品 |

#### 3.3.2 老年人专属Dijkstra权重设计

```
weight = base_distance
+ stairs_count × 10 × (has_handrail ? 0.5 : 1.0)    // 台阶惩罚，有扶手减半
+ slope_deg × 8                                        // 坡度惩罚
× surface_penalty(smooth:1.0, brick:1.3, gravel:2.0, broken:3.0)  // 路面质量
× (is_summer && has_shade ? 0.8 : 1.0)                // 遮阳加分
× (gait_state=="cautious" ? 1.5 : gait_state=="unsteady" ? 2.0 : 1.0)  // 步态修正
+ public_toilet_nearby ? -10 : 0                       // 附近有厕所加分
```

#### 3.3.3 当前实现状态

- ✅ 签到写入闭环：DailyLifeCheckInSupportService → DailyLifeCheckInRepository → SQLite
- ✅ 只读查询闭环，支持 `urgency_filter` 和 `limit`
- ✅ 单条签到详情：`GET /vitalai/flows/daily-life-checkins/{user_id}/{checkin_id}`
- ✅ 完整率低于60%时归一化为0.0

### 3.4 Mental Care 心理关怀领域

#### 3.4.1 核心能力

| 功能 | 技术方案 | 核心设计 |
|------|---------|---------|
| HMM情绪状态感知 | 隐马尔可夫模型 | 四状态：正常/轻微下降/持续低落/急性低落；连续3天低分触发干预 |
| 记忆检索与连续性 | Hindsight记忆系统Recall | 对话前自动召回相关记忆；让王奶奶感觉"这个助手真的记得我说过的话" |
| 智慧传承 | LLM+RAG | 引导讲述人生故事→实时提取实体/情感→自动生成"人生故事册" |
| 反思评分 | LLM+Reflect操作 | 每日21:00轻松日总结；根据情绪选对话风格（celebratory/warm/gentle_support） |

#### 3.4.2 情绪感知特征提取

| 特征维度 | 具体指标 | 情绪含义 |
|---------|---------|---------|
| 语言特征 | 句子平均长度、正向词比例、自我提及次数、未来提及次数、负向标记词 | 句子短→情绪低；"算了/没意思"→负向信号 |
| 对话行为 | 回应延迟、沉默次数、话题主动性 | 延迟长+沉默多→情绪低落 |
| HMM序列 | 7天情绪评分趋势 | 斜率<-0.05+连续3天<0.5→prolonged_low |

#### 3.4.3 智慧传承

**故事类型与引导**：

| 故事类型 | 引导问题示例 | 写入字段 | 家属可见 |
|---------|------------|---------|---------|
| 童年记忆 | "您小时候最开心的事是什么？" | is_life_story=true, emotion_tag=nostalgia | 是 |
| 职业成就 | "您教过哪个学生让您最骄傲？" | is_life_story=true, emotion_tag=pride | 是 |
| 家庭故事 | "您和老伴是怎么认识的？" | is_life_story=true, emotion_tag=love | 是 |
| 人生智慧 | "您觉得什么是最重要的事？" | is_life_story=true, emotion_tag=wisdom | 是 |
| 心愿清单 | "有没有特别想做但还没做的事？" | 遗愿清单，单独标记 | 仅授权家属 |

**3个月后产出**：42个人生故事 + 自动识别人生主题 + 提炼智慧语录

#### 3.4.4 当前实现状态

- ✅ 签到写入闭环：MentalCareCheckInSupportService → MentalCareCheckInRepository → SQLite
- ✅ 只读查询闭环，支持 `mood_filter`
- ✅ 单条签到详情读取
- ✅ mood_signal归一化（calm/anxious等枚举值）

### 3.5 Profile Memory 用户画像记忆

#### 3.5.1 Hindsight 四网络记忆架构

基于 Hindsight 论文（LongMemEval 准确率从39%提升到91.4%），核心主张：不要把"我知道的事实"和"我认为的观点"和"我对某人的印象"混在一起。

**四网络映射**：

| 网络 | 论文定义 | 项目映射 | 主要写入者 | 主要读取者 |
|------|---------|---------|-----------|-----------|
| **W 世界网络** | 关于外部世界的客观事实 | 王奶奶的医疗事实、家庭关系、社区信息 | 隐私卫士Agent、智能汇报Agent、Tool Agent | 急救Agent、出行Agent、日常管理Agent |
| **E 经历网络** | Agent自身的第一人称经历 | 系统为王奶奶做过的事情、推荐过的路线、被拒绝的建议 | 日常管理Agent、健康模块Agent、精神模块Agent | 反馈聚合器、决策核心、精神模块Agent |
| **O 观点网络** | Agent的主观判断，带置信度 | 系统对王奶奶的个性化判断（"王奶奶09:30是最佳运动时段，置信度0.87"） | L3长期反馈模块、精神模块Agent、智能汇报Agent | 冲突仲裁层、MAB推送调度、决策核心 |
| **S 观察网络** | 对实体的客观摘要 | 王奶奶的综合画像摘要（"72岁独居老人，高血压患者，腿脚略有不便"） | 自动后台任务（从W+E综合生成） | 意图识别层、精神模块Agent、智能汇报Agent |

**三操作**：

| 操作 | 实现 | 触发时机 |
|------|------|---------|
| **Retain（记忆写入）** | 把事件提炼为叙事性事实，分类写入对应网络 | 每次L1反馈、每次对话结束、每次健康数据更新 |
| **Recall（记忆召回）** | 四路并行检索（语义+关键词+图遍历+时间过滤）+ RRF融合 + 神经重排序 | 用户输入预处理时、决策核心需要参考历史时、Agent执行前需要个人信息时 |
| **Reflect（反思）** | 基于检索到的记忆，结合Agent性格参数（Skepticism/Literalism/Empathy），生成回复并更新观点网络 | 每天23:00 L2聚合、每月L3深度提炼、精神Agent每次对话结束 |

**记忆图结构**：G = (V, E)，每条记忆是一个节点V，四类边E：时序边、语义边、实体边、因果边

#### 3.5.2 当前实现状态

- ✅ SQLite 持久化写入与只读查询闭环
- ✅ 支持按 `memory_key` 精确查询，不传 key 时返回完整 snapshot
- ✅ snapshot 包含只读派生字段 `memory_keys` 和 `readable_summary`
- ✅ upsert 语义：同一 key 多次写入更新时间和值

### 3.6 Reporting 报告反馈领域

#### 3.6.1 智能汇报Agent核心能力

| 功能 | 技术方案 | 核心设计 |
|------|---------|---------|
| 贝叶斯多信号融合风险预测 | 贝叶斯网络 | 6个独立信号→1个综合风险概率；发现单指标看不到的隐患 |
| 家属每日摘要报告 | LLM生成+差分隐私 | 低风险日→一句话摘要；高风险日→结构化详情 |
| 医生就诊辅助报告 | LLM生成 | 30天健康趋势+用药依从性+生活规律+情绪心理+近期异常事件 |
| HMM趋势分析 | 隐马尔可夫 | 区分"暂时波动"和"持续恶化" |

#### 3.6.2 贝叶斯多信号融合示例

**今日数据**：
- P(血压高)=0.60，P(情绪低落)=0.72，P(寒冷天气)=0.85，P(久坐不动)=0.70，P(睡眠差)=0.55

**贝叶斯网络计算**：考虑信号间相关性后，综合健康风险 P(health_risk=high) = 0.83

**如果只看单个指标**：血压0.60→WATCH，不触发任何动作

**贝叶斯综合风险0.83→触发行动**：增强监护频率→精神Agent主动联系→家属发送摘要

---

## 四、平台层详细设计

### 4.1 平台层总览

```
platform/
├── messaging/      📨 通信层    —— Agent 之间怎么说话
├── feedback/       🔄 反馈层    —— 做完事怎么反馈
├── arbitration/    ⚖️ 仲裁层    —— 冲突了听谁的
├── interrupt/      🚨 中断层    —— 出事了怎么打断
├── observability/  👁️ 可观测层  —— 系统在干什么看得见
├── security/       🔒 安全层    —— 敏感数据怎么保护
│
└── runtime/        🧠 运行时    —— 整个系统的"心脏"
    ├── decision_core.py         决策核心
    ├── event_aggregator.py      事件聚合器
    ├── snapshots.py             快照系统
    ├── failover.py              故障转移
    ├── health_monitor.py        健康监控
    ├── shadow_decision_core.py  影子决策核心（热备）
    ├── degradation.py           降级策略
    └── signal_wiring.py         信号桥接
```

### 4.2 通信基础设施层（第一层）

#### 4.2.1 三种通信模式

| 模式 | 类比 | 适用场景 | 特点 | 技术选型 |
|------|------|---------|------|---------|
| 同步 Request-Reply | 打电话 | 需要即时结果的数据查询 | 阻塞等待，实时获取 | gRPC / HTTP REST |
| 异步 Pub/Sub | 发朋友圈 | 一对多的状态广播 | 非阻塞，一发多收 | Redis Pub/Sub / Kafka |
| 异步消息队列 | 发快递 | 需要保证送达的持久化消息 | 持久化存储，不丢失 | Kafka / RabbitMQ |

#### 4.2.2 统一消息信封 MessageEnvelope

所有组件间通信的唯一格式：

```
MessageEnvelope {
    from_agent:     string        // 谁发的
    to_agent:       string        // 发给谁
    payload:        dict          // 内容
    priority:       CRITICAL | HIGH | NORMAL | LOW  // 四级优先级
    ttl:            int           // 生存时间（秒）
    require_ack:    bool          // 是否需要回执
    expire_at:      datetime      // 过期时间
    msg_id:         uuid          // 消息ID
    trace_id:       uuid          // 链路追踪ID
    version:        int           // 版本号
}
```

**优先级语义**：
- CRITICAL：最高，立即处理（如老人摔倒）
- HIGH：紧急，尽快处理（如血压异常）
- NORMAL：普通，正常排队（如日常签到）
- LOW：最低，有空再处理（如定期报告）

### 4.3 反馈闭环层（第二层）

#### 4.3.1 三层反馈模型

| 层级 | 名称 | 时间范围 | 数据来源 | 触发方式 | 核心价值 |
|------|------|---------|---------|---------|---------|
| L1 | 即时反馈层 | < 5秒 | Agent执行结果 | 自动推送 | Supervisor实时感知，快速响应异常 |
| L2 | 短期反馈层 | 小时/天 | L1聚合+用户行为 | 定时聚合（每日23:00） | 日/周行为总结，更新近期偏好 |
| L3 | 长期反馈层 | 周/月 | L2模式提取 | 定期深度分析 | 长期习惯沉淀，驱动个性化演进 |

#### 4.3.2 四类反馈事件

| 事件类型 | 触发时机 | 示例 |
|---------|---------|------|
| FEEDBACK_POS | Agent高质量完成任务 | 反思Agent生成精准日总结，置信度0.92 |
| FEEDBACK_NEG | Agent执行失败或质量低 | 任务Agent因API超时未完成，质量评分0.1 |
| USER_APPROVE | 用户点赞/采纳建议 | 用户点击"接受今日运动计划" |
| USER_REJECT | 用户划掉/忽略/明确拒绝 | 用户连续3次划掉"减少咖啡"建议 |

#### 4.3.3 置信度评分机制

| Agent类型 | 评分维度 | 评分示例 |
|-----------|---------|---------|
| 反思Agent | 情感识别准确率+内容完整度 | 0.9+0.85→综合0.87 |
| 健康Agent | 数据完整性+数据新鲜度 | 1.0+0.7→综合0.85 |
| 任务Agent | 任务完成率+步骤准确率 | 1.0+0.6→综合0.8 |

#### 4.3.4 用户拒绝行为处理

连续拒绝3次→大幅降低该建议权重，未来30天不再推送；单次拒绝→轻微降低权重，调整推送时间。拒绝行为写入E网络（经历网络），确保不会重复推送。

### 4.4 冲突仲裁层（第三层）

#### 4.4.1 四象限冲突分类

| 冲突类型 | 核心矛盾 | 典型场景 | 自动解决策略 | 需用户介入 |
|---------|---------|---------|-------------|-----------|
| 资源冲突 | 争夺同一稀缺资源（注意力/推送频道） | 早9点三个Agent同时要推消息 | 优先级排队+消息合并+时间错位 | ❌ |
| 目标冲突 | 两个Agent目标方向相反 | 健康Agent要休息 vs 任务Agent要专注 | 全局目标权重仲裁 | ⚠️ 权重差值≤0.3时是 |
| 信息冲突 | 对同一数据有不同解读 | 心率Agent vs 健康Agent判断不一致 | 权威数据源仲裁 | ⚠️ 无法确认权威源时是 |
| 指令冲突 | Supervisor全局指令与Agent本地策略矛盾 | "今天休息日"但任务Agent仍在执行 | 上级指令优先 | ❌ |

#### 4.4.2 意图声明池（Intent Declaration Pool）

任何Agent在执行行动前，必须提交意图声明：

```
IntentDeclaration {
    intent_id:        string      // 意图ID
    agent_id:         string      // 哪个Agent
    action:           string      // 计划做什么
    target_time:      datetime    // 计划什么时间做
    resources_needed: []string    // 需要什么资源
    goal_type:        enum        // 目标类型
    goal_weight:      float       // 目标权重（用于仲裁）
    flexibility: {                // 可接受的妥协
        time_shift:   string      // 时间可偏移范围
        can_merge:    bool        // 是否可合并
        can_delay:    bool        // 是否可延迟
    }
}
```

#### 4.4.3 全局目标优先级

| 目标类型 | 默认权重 | 可调整 | 说明 |
|---------|---------|--------|------|
| 生命安全 | 1.00 | ❌ 不可降低 | 永远最高优先级 |
| 健康维持 | 0.85 | ✅ 0.7~1.0 | 用户健康相关目标 |
| 情绪稳定 | 0.75 | ✅ 0.6~0.9 | 心理健康相关目标 |
| 任务完成 | 0.70 | ✅ 0.5~0.9 | 工作任务相关目标 |
| 习惯养成 | 0.60 | ✅ 0.4~0.8 | 长期习惯培养目标 |
| 娱乐休闲 | 0.50 | ✅ 0.3~0.7 | 放松娱乐相关目标 |

#### 4.4.4 乐观锁机制

个人信息库并发写入保护：读取时记录版本号，写入时检查版本是否一致。不一致→触发合并策略（两段判断都保留，标注数据来源和时间戳），而非直接覆盖。

### 4.5 紧急中断层（第四层）

#### 4.5.1 四级中断优先级

| 级别 | 名称 | 触发条件 | 响应时限 | 影响范围 | 绕过Supervisor |
|------|------|---------|---------|---------|--------------|
| P0 🔴 | 生命安全 | 跌倒/心率骤变/SOS手势/血压>180 | < 1秒 | 全局冻结所有非急救Agent | 是 |
| P1 🟠 | 健康预警 | 血压连续3次>145/久坐>2小时/睡眠<4小时 | < 5秒 | 暂停日常任务，健康模块切监控强化 | 否 |
| P2 🟡 | 任务冲突 | 多Agent争夺注意力且仲裁无法自动解决 | < 30秒 | 仅暂停冲突Agent | 否 |
| P3 🟢 | 普通提醒 | 日程到期/吃药提醒/视频通话提醒 | < 5分钟 | 不影响任何Agent | 否 |

#### 4.5.2 六态状态机

```
NORMAL → INTERRUPT_DETECTED → EVALUATING → CONFIRMING → EXECUTING → RECOVERING → NORMAL
                                      ↓                                    ↑
                                  NORMAL（误触发）                  ESCALATING（情况恶化）
```

| 状态 | 含义 | 允许的下一步 |
|------|------|------------|
| NORMAL | 系统正常运行 | → INTERRUPT_DETECTED |
| INTERRUPT_DETECTED | 检测到触发信号 | → EVALUATING |
| EVALUATING | 评估优先级和影响域 | → CONFIRMING 或 NORMAL（误触发） |
| CONFIRMING | 等待用户确认或P0的3秒倒计时 | → EXECUTING 或 NORMAL（用户撤销） |
| EXECUTING | 中断逻辑执行中 | → RECOVERING 或 ESCALATING |
| RECOVERING | 各Agent恢复状态 | → NORMAL |

#### 4.5.3 快照与恢复

中断发生前，先保存各Agent的完整状态快照：

```
RuntimeSnapshot {
    snapshot_id:    string    // 哪个场景的快照
    payload:        dict      // 当时系统状态
    version:        int       // 版本号（递增）
    trace_id:       string    // 哪次请求触发
    captured_at:    datetime  // 什么时候拍的
}
```

**保留策略**：P0=永久，P1=24h，P2/P3=1h

**存储方式**：
- 默认→进程内存（重启即丢失）
- 配置 `VITALAI_RUNTIME_SNAPSHOT_STORE_PATH` → 本地文件（重启仍在）
- 支持历史版本保留上限 `VITALAI_RUNTIME_SNAPSHOT_MAX_VERSIONS_PER_ID`

#### 4.5.4 P0的3秒撤销窗口

P0中断触发后，显示3秒倒计时，期间用户可撤销。撤销后记录为误报，用于优化触发阈值。

### 4.6 运行时核心

#### 4.6.1 为什么不是一个大Supervisor

**传统Supervisor的问题**：
- 原始事件全量涌入，中心容易过载
- 高频聚合和高价值决策抢同一资源
- 日志IO拖慢决策
- 中心挂了，整体失能

**本项目的解决方案**：拆成一组协作组件

```
事件聚合器（去重/合并/排序/TTL校验）
       │
       ▼ 结构化摘要
决策核心（查handler→执行→返回出站消息）
       │
  ┌────┼────┐
  ▼    ▼    ▼
快照  故障  降级
系统  转移  策略
       │
  ┌────┴────┐
  ▼         ▼
可观测     安全
记录       审查
```

#### 4.6.2 故障转移

- **主决策核心**（active）+ **影子决策核心**（standby热备）
- 正常时：主核心同步状态到影子核心
- 故障时：Health Monitor检测到主核心失联→影子核心从最新快照恢复→5秒内接管
- 类比：主刀医生不行了→护士发出中断信号→副手根据刚才看到的进度立刻接上

#### 4.6.3 降级策略

| Level | 名称 | 行为 |
|-------|------|------|
| Level 0 | 正常 | 一切正常运行 |
| Level 1 | 自治惯性 | 中心不可用，各领域按最近规则自己跑 |
| Level 2 | 保底运行 | 只处理CRITICAL，其他全拒绝 |
| Level 3 | 只记录 | 什么都执行不了，至少把事件记下来 |

### 4.7 可观测 + 安全横切面

#### 4.7.1 信号桥接 SignalBridge

每个关键动作自动推入桥接，桥接同时分发给可观测+安全。**领域代码不需要感知这两个横切面的存在，不会遗漏。**

```
所有关键动作 → SignalBridge → 👁️ 可观测记录 + 🔒 安全扫描
```

#### 4.7.2 可观测层 ObservabilityCollector

自动记录：消息接收、决策输出、快照保存、中断触发、反馈产生、仲裁裁决、故障转移。

#### 4.7.3 安全层 SensitiveDataGuard

**三级数据权限**：

| 数据类别 | 老人自己 | 家属（授权） | 医生（授权） | 第三方App |
|---------|---------|------------|------------|----------|
| 对话内容 | ✅完整查看 | ❌默认不可见 | ❌ | ❌ |
| 健康体征 | ✅ | ✅ | ✅授权后 | ❌ |
| 医疗记录 | ✅ | ✅（急救用） | ✅ | ❌永远不对外 |
| 情绪评分 | ✅ | ⚠️仅趋势摘要 | ❌ | ❌ |
| 人生故事 | ✅ | ⚠️老人显式授权 | ❌ | ❌ |

**出境数据脱敏**：
- Level1：直接标识符脱敏（姓名→伪名，电话→掩码，地址→区级模糊）
- Level2：准标识符泛化（血压152→150精度降低）
- Level3：敏感属性特殊处理（过敏史/慢性病永远不发给非医疗机构）

**AI输出内容审查**：
- 禁止具体用药建议（不能说"您应该增加降压药剂量"）
- 禁止确定性诊断（不能说"您患有xxx病"）
- 禁止无法兑现的承诺（不能说"我会永远陪着您"）

**差分隐私**：统计查询加Laplace噪声，ε=0.5（较强保护），保护个人信息不被差值攻击还原。

---

## 五、应用层详细设计

### 5.1 应用层结构

```
application/
├── commands/     📝 命令（写操作的输入）
├── queries/      🔍 查询（读操作的输入）
├── use_cases/    🎯 用例（一个步骤的业务逻辑）
├── workflows/    🔗 工作流（多个步骤串起来）
└── assembly.py   🏗️ 装配器（依赖注入容器）
```

### 5.2 CQRS 模式

写操作和读操作完全分开：

```
写路径：Command → FlowWorkflow → RunXxxFlowUseCase → 写入 SQLite
读路径：Query   → QueryWorkflow → RunXxxQueryUseCase → 从 SQLite 读取
```

### 5.3 Assembly 装配器

系统的依赖注入容器，负责把仓储、领域服务、平台组件和工作流拼装在一起。

**核心设计**：
- **惰性初始化**：用到才创建，不浪费
- **环境感知**：`ApplicationAssemblyEnvironment.from_environment()` → `.to_config()` → `ApplicationAssembly(config)`
- **角色感知**：API角色全量拼装，Scheduler/Consumer角色关闭reporting和runtime_signals

**配置示例**：

```bash
# 意图识别器选择
VITALAI_INTENT_RECOGNIZER=rule_based|bert|hybrid

# 第二层拆解器选择
VITALAI_INTENT_DECOMPOSER=placeholder|llm

# LLM配置
VITALAI_INTENT_DECOMPOSER_LLM_PROVIDER=openai_compatible|base_qwen
VITALAI_INTENT_DECOMPOSER_LLM_MODEL=qwen-plus
VITALAI_INTENT_DECOMPOSER_LLM_API_KEY=xxx
VITALAI_INTENT_DECOMPOSER_LLM_BASE_URL=xxx
VITALAI_INTENT_DECOMPOSER_LLM_TEMPERATURE=0.3
VITALAI_INTENT_DECOMPOSER_LLM_TIMEOUT_SECONDS=30

# Runtime Snapshot
VITALAI_RUNTIME_SNAPSHOT_STORE_PATH=.runtime/runtime_snapshots.json
VITALAI_RUNTIME_SNAPSHOT_MAX_VERSIONS_PER_ID=10

# Admin 控制面
VITALAI_RUNTIME_CONTROL_ENABLED=true
VITALAI_ADMIN_TOKEN=dev-admin-token
```

---

## 六、意图识别系统详细设计

### 6.1 双层意图识别架构

```
用户消息 → [输入预处理] → [第一层：边缘快思考] → [第二层：LLM深度理解] → [路由层] → Agent执行
```

#### 6.1.1 为什么不能直接把用户输入发给大模型

| 方案 | 优点 | 致命缺点 | 对本项目的影响 |
|------|------|---------|--------------|
| 所有输入直接发LLM | 实现简单 | 每次调用2~5秒，成本高 | 老人问"现在几点"要等5秒 |
| 关键词匹配 | 延迟极低 | 无法理解模糊表达 | "腿有点酸"无法匹配到健康Agent |
| **双层架构** | 速度+理解兼顾 | 实现略复杂 | 简单问题<100ms，复杂问题<2s |

### 6.2 输入预处理

三道预处理：噪声清洗、语境融合、安全过滤。

```python
# InputPreprocessor 当前实现
1. trim（首尾空格去除）
2. 连续空白收敛为单个空格
3. 保留原始输入（preprocessing.original_message）
4. 空消息拦截
5. 基础异常标记（preprocessing.flags）
```

**设计文档中的完整预处理**（含ASR和语境融合，当前为简化版）：
- ASR语音转文字 + 老人口音纠错
- 用户状态注入（血压/步态/用药/情绪/时间）
- 隐私卫士安全过滤

### 6.3 第一层：边缘快思考

#### 6.3.1 意图类别体系

| 意图 | 描述 | 典型输入 |
|------|------|---------|
| health_alert | 健康预警 | "我头晕"、"摔倒" |
| daily_life_checkin | 日常签到 | "买菜"、"做饭" |
| mental_care_checkin | 心理关怀 | "焦虑"、"孤单" |
| profile_memory_update | 记忆写入 | "记住"、"我喜欢" |
| profile_memory_query | 记忆查询 | "你还记得"、"我之前说过" |
| unknown | 无法识别 | — |
| needs_decomposition | 复合意图（评估标签） | "我心里慌，药还要不要天天吃" |

#### 6.3.2 三道防线

```
用户消息
    │
    ▼
1. 复合意图检测（needs_decomposition_detector）
    │ 不是复合意图
    ▼
2. hard-case guard（已知易混淆场景拦截）
    │ "药+不适" → health_alert ✅
    ▼
3. BERT推理 / 规则匹配
    │ 置信度够高 → 用BERT/规则结果
    │ 不够高 → fallback到rule_based
```

#### 6.3.3 方案选择

通过环境变量在启动时配置（运维配的，不是运行时动态切换）：

```
VITALAI_INTENT_RECOGNIZER=rule_based  ← 默认，全用规则
VITALAI_INTENT_RECOGNIZER=bert        ← 优先BERT，失败fallback到规则
VITALAI_INTENT_RECOGNIZER=hybrid      ← 预留
```

**bert模式下的动态决策**：每条输入根据识别结果决定——BERT成功且置信度高用BERT，失败或低置信fallback到规则。

#### 6.3.4 BERT模型

- **模型类型**：6类 bootstrap intent sequence-classification
- **训练数据**：180条baseline + 108条holdout（33条needs_decomposition + 18条hardcase_guard_precision_v1 + 其他）
- **评估结果**：rule_based全量288/288；BERT holdout 108/108（含hard-case guard 27条 + BERT直接识别33条 + 低置信fallback 15条）
- **置信度阈值**：0.65（BERT低于此值自动fallback到规则）
- **本地模型路径**：`D:\AI\Models\fine-tuned-bert-intent-vitalai-trained`

### 6.4 第二层：LLM深度理解与意图拆分

#### 6.4.1 触发条件

第一层检测到复合/多任务/模糊表达时，返回 `decomposition_needed`。

#### 6.4.2 LLM输出格式

```json
{
    "primary_task": {
        "intent": "health_alert",
        "priority": "high",
        "confidence": 0.85
    },
    "secondary_tasks": [{
        "intent": "mental_care_checkin",
        "priority": "normal",
        "confidence": 0.7
    }],
    "risk_flags": [{
        "severity": "high",
        "category": "medication",
        "description": "涉及用药决策，需谨慎"
    }]
}
```

#### 6.4.3 四道关卡

```
LLM拆解
  │
  ▼
1. Schema校验（primary_task不能为空、intent必须是合法值、confidence在0-1之间）
  │
  ▼
2. 路由守门（RunIntentDecompositionRoutingGuardUseCase）
  │ 低风险+高置信 → routing_candidate
  │ 高风险/低置信/缺primary → blocked
  │
  ▼
3. 非执行态（当前不直接执行领域workflow，只返回候选）
  │
  ▼
4. 返回响应（accepted=false, decomposition_needed, 候选任务+风险标记+澄清问题）
```

**为什么拆完还不执行**：养老场景涉及健康和用药，宁可多确认一次，也不可误操作。

#### 6.4.4 第二层评测体系

| 组件 | 路径 | 功能 |
|------|------|------|
| hard-case评测 | `data/intent_eval/second_layer_hard_cases.jsonl` | 22条样本，当前14 valid / 8 invalid |
| 原始响应快照 | `data/intent_eval/second_layer_response_snapshots.jsonl` | 8条样本，6 valid / 2 invalid |
| 采样脚手架 | `scripts/intent_eval/capture_second_layer_response_snapshots.py` | 支持 `--id`/`--category`/`--limit`/`--skip-existing` |
| 审核队列管理 | `scripts/intent_eval/manage_second_layer_snapshot_review_queue.py` | summary/triage-report/list/show/set-status/bulk-set-status |
| 正式入库 | `scripts/intent_eval/promote_second_layer_snapshot_review_queue.py` | 只提升approved_for_baseline的项 |
| baseline审计 | `scripts/intent_eval/audit_second_layer_snapshot_baseline.py` | 统计expected分布/review provenance/重复id |

---

## 七、接口层详细设计

### 7.1 三种入口通道

| 入口 | 角色 | 谁触发 | require_ack | TTL | 报告生成 | 运行时信号 |
|------|------|--------|------------|-----|---------|-----------|
| HTTP API | API角色 | 用户主动请求 | 可选 | 120秒 | ✅ | ✅ |
| 定时任务 | Scheduler角色 | 定时器自动触发 | false | 300秒 | ❌ | ❌ |
| 消息消费 | Consumer角色 | 外部系统推送 | true | 60秒 | ❌ | ❌ |

### 7.2 API路由一览

| 路径 | 方法 | 功能 |
|------|------|------|
| `/vitalai/health` | GET | 健康检查 |
| `/vitalai/interactions` | POST | 统一用户交互入口 |
| `/vitalai/flows/profile-memory` | POST | 写入画像记忆 |
| `/vitalai/flows/profile-memory/{user_id}` | GET | 查询画像快照 |
| `/vitalai/flows/health-alert` | POST | 写入健康预警 |
| `/vitalai/flows/health-alerts/{user_id}` | GET | 查询预警历史 |
| `/vitalai/flows/health-alerts/{user_id}/{alert_id}` | GET | 单条预警详情 |
| `/vitalai/flows/daily-life-checkin` | POST | 写入日常签到 |
| `/vitalai/flows/daily-life-checkins/{user_id}` | GET | 查询签到历史 |
| `/vitalai/flows/daily-life-checkins/{user_id}/{checkin_id}` | GET | 单条签到详情 |
| `/vitalai/flows/mental-care-checkin` | POST | 写入心理签到 |
| `/vitalai/flows/mental-care-checkins/{user_id}` | GET | 查询签到历史 |
| `/vitalai/flows/mental-care-checkins/{user_id}/{checkin_id}` | GET | 单条签到详情 |
| `/vitalai/users/{user_id}/overview` | GET | 用户综合概览 |
| `/vitalai/admin/runtime-diagnostics/api` | POST | 运行时诊断 |
| `/vitalai/admin/runtime-diagnostics/api/health-failover` | POST | 故障转移演练 |

### 7.3 接口层设计原则

**极薄**：接口层只做三件事——接收输入、调用应用层、返回结果。业务逻辑全在应用层。换入口方式零成本。

### 7.4 Admin控制面安全

三道门：
1. 默认关闭：`VITALAI_RUNTIME_CONTROL_ENABLED=true` 不配则403
2. 必须带Token：`X-VitalAI-Admin-Token: xxx`
3. Token从环境变量读取：`VITALAI_ADMIN_TOKEN=xxx`

---

## 八、数据持久化设计

### 8.1 当前存储方案

| 领域 | SQLite路径 | 核心表 | 写入模式 |
|------|-----------|--------|---------|
| profile_memory | `.runtime/profile_memory.sqlite3` | profile_memory_records | upsert（同key更新） |
| health | `.runtime/health.sqlite3` | health_alert_records | append（新记录追加） |
| daily_life | `.runtime/daily_life.sqlite3` | daily_life_checkin_records | append |
| mental_care | `.runtime/mental_care.sqlite3` | mental_care_checkin_records | append |
| runtime_snapshot | `.runtime/runtime_snapshots.json` | — | 文件型JSON存储 |

### 8.2 设计目标：三层分级存储

| 层 | 存储 | 数据特征 | 读写频率 | 响应要求 |
|----|------|---------|---------|---------|
| 热数据层 | Redis | 当前会话状态、今日体征、实时情绪 | 每30秒~1分钟 | 毫秒级 |
| 温数据层 | PostgreSQL | 近3个月行为模式、偏好、L2聚合 | 每次对话 | 秒级 |
| 冷数据层 | Neo4j + RAG向量库 | 长期事实、人生故事、医疗记录 | 每天/每周/每月 | 分钟级可接受 |

**冷数据层的RAG与Knowledge Graph边界**：
- **Neo4j图数据库**：结构化关系（家庭关系图谱、医疗事实、过敏史）→ 支持图遍历检索
- **RAG向量库**：非结构化描述（人生故事、对话记录）→ 支持语义检索
- 两者绝不混用，查询路由层根据查询类型自动选择

### 8.3 统一查询路由层

所有Agent不再直接访问存储层，而是通过Data Router：

```
Agent查询请求 → Data Router → 判断查询类型/时间范围/数据类型
                            → 热数据层（实时状态）
                            → 温数据层（近期模式）
                            → 冷数据层（长期事实）
```

### 8.4 数据生命周期

```
热数据（实时） → 24h → 自动迁移到温数据
温数据（近期） → 3个月 → 自动迁移到冷数据
冷数据（长期） → 永久保留，定期压缩
```

---

## 九、Tool Agent（工具Agent）详细设计

### 9.1 核心定位

所有外部系统调用的统一入口。核心价值：**标准化、隔离、安全、降级**。

### 9.2 工具清单

| 工具类 | 工具名 | 调用时机 | 老年场景特殊处理 |
|--------|--------|---------|----------------|
| 天气与环境 | 天气查询 | 出行规划前、日常健康评估时 | 气温<10℃→标注"血压风险"；AQI>150→标注"呼吸道风险" |
| 天气与环境 | 穿衣建议 | 每日早晨 | 结合降压药+血压偏高时建议多穿 |
| 地图与出行 | 老年友好路径 | 出行规划时 | 台阶/坡度/遮阳/厕所重新评分；步态偏弱时惩罚翻倍 |
| 医疗信息 | 药品数据库查询 | 新药录入时 | 只返回"建议咨询医生"，不返回"您应该怎么调整" |
| 医疗信息 | 医院预约 | 需就医时 | 就诊记录写入前必须用户确认 |
| 医疗信息 | 体检报告OCR | 上传体检报告时 | 识别后不保留原始图片，只保留结构化数据 |

### 9.3 统一降级策略

```
Tool Agent.call(tool_name, params):
    for attempt in 1..max_retries:
        try:
            result = call_with_timeout(tool, params, timeout_ms)
            cache.set(key, result, TTL)    // 成功：写入缓存
            return result
        except:
            sleep(attempt * 1000)           // 指数退避：1s→2s→4s
    // 最终失败
    cached = cache.get(key)                 // 尝试读缓存
    if cached: return {**cached, is_cached: true}
    if fallback: return fallback(params)    // 调用方提供的降级函数
    dlq.push(tool_name, params, error)      // 进入死信队列
    throw ToolUnavailableError
```

**缓存TTL**：

| 工具 | 缓存时间 |
|------|---------|
| 天气 | 30分钟 |
| 药物冲突 | 24小时 |
| 路线 | 1小时 |
| 商品价格 | 5分钟 |
| 医院信息 | 24小时 |

---

## 十、一条请求的完整旅程

### 10.1 简单请求："我头晕"

```
👴 老人说："我头晕"
│
▼
① 接口层：POST /vitalai/interactions
│
▼
② 应用层：UserInteractionWorkflow
│  ②-1 输入预处理：trim + 连续空白收敛
│  ②-2 意图识别（第一层）：rule_based/bert → health_alert, confidence=0.92
│  ②-3 路由分发：识别出 health_alert → 分发到 HealthAlertWorkflow
│
▼
③ HealthAlertWorkflow 执行
│  ③-1 构建 MessageEnvelope：priority=CRITICAL
│  ③-2 RunHealthAlertFlowUseCase
│      ③-2-1 消息入聚合器 EventAggregator.ingest()
│      ③-2-2 聚合器生成摘要 → 同时推入信号桥接 → 可观测记录 + 安全审查
│      ③-2-3 决策核心 DecisionCore.process_summary() → 查表→调用健康分诊
│      ③-2-4 领域服务 HealthAlertTriageService.triage()
│      ③-2-5 写入历史 HealthAlertRepository.save() → .runtime/health.sqlite3
│  ③-3 快照（CRITICAL级别自动触发）
│  ③-4 收集反馈 + 报告
│
▼
④ 返回响应
{
    accepted: true,
    routed_event_type: "HEALTH_ALERT",
    response: { risk_level: "high", ... },
    intent: { primary_intent: "health_alert", source: "rule_based" },
    runtime_signals: [...],
    preprocessing: { original_message: "我头晕", normalized_message: "我头晕", changed: false }
}
```

### 10.2 复杂请求："我心里慌，药还要不要天天吃"

```
👴 老人说："我心里慌，药还要不要天天吃"
│
▼
①② 应用层：UserInteractionWorkflow
│  预处理：无变化
│  意图识别（第一层）：检测到复合意图！
│
▼
③ 第二层意图拆解
│  LLM拆解：primary_task=health_alert(用药), secondary_task=mental_care_checkin(心理)
│  risk_flags: [{ severity: "high", category: "medication" }]
│
▼
④ Schema校验：✅ 格式合法
│
▼
⑤ 路由守门：❌ 高风险（medication），阻断
│
▼
⑥ 返回响应
{
    accepted: false,
    error: "decomposition_needed",
    error_details: {
        decomposition: {
            candidate_tasks: [health_alert, mental_care_checkin],
            risk_flags: [{ severity: "high", category: "medication" }]
        },
        decomposition_guard: {
            status: "blocked",
            blocked_reasons: ["high_risk_medication"],
            clarification_question: "用药问题需医生确认，是否继续？"
        }
    }
}
```

---

## 十一、四层协同完整示例：一次寒冷清晨的P1预警

```
【06:50】王奶奶刚醒来
│
▼ 传感器采集
健康Agent：血压148/95（Fuzzy Logic评分0.68，校正后等效158→P1级别）
精神Agent：情绪评分0.55（比昨日低0.15）
天气API（Tool Agent）：气温7℃→标注"血压风险"
│
▼ ① 第一层：通信层
健康Agent通过MessageEnvelope(priority=HIGH)发布血压数据更新
→ 订阅者：Supervisor、日常Agent、精神Agent同时收到
│
▼ ② 第二层：反馈层
健康Agent构造L1反馈：FEEDBACK_POS, quality_score=0.85
→ Supervisor实时感知血压异常
│
▼ ③ 第三层：冲突仲裁层
健康Agent提交意图声明：goal_type=HEALTH_MAINTENANCE, goal_weight=0.85
→ "今日应降低外出强度"
日常Agent原计划09:00推送"今日5个待办"→冲突检测→自动降级
→ 合并为一条："今日血压偏高，减少3个低优先级待办"
│
▼ ④ 第四层：紧急中断层
P1级中断触发：久坐2小时阈值激活
→ 日常任务Agent暂停（保存快照，current_step记录）
→ 健康Agent切监控强化模式
→ 中断处理完→任务Agent从快照恢复继续
│
▼ 贝叶斯综合风险评估
P(血压高)=0.60, P(情绪低落)=0.55, P(寒冷)=0.85, P(久坐)=0.70
→ 综合风险=0.78→触发：增加监护频率+精神Agent主动联系+家属摘要
│
▼ 家属报告（智能汇报Agent生成）
"今日提醒：妈妈今天有几项指标需要您关注：
 ① 血压连续4天上升（今日148），已触发强化监护
 ② 情绪偏低，可能和天气寒冷有关
 ③ 建议今晚打个视频通话"
```

---

## 十二、隐私卫士Agent详细设计

### 12.1 核心定位

系统内所有数据出境的安全网关。核心能力：数据脱敏、权限分级管控、隐私预算、合规检查、AI输出稳定性防护。

### 12.2 出境数据脱敏三步

```
Level1: 直接标识符脱敏
  "王奶奶" → "用户001"
  "138XXXX5678" → "****5678"
  精确地址 → 区级模糊
  1953年出生 → "70-75岁"

Level2: 准标识符泛化（防重识别攻击）
  血压152 → 150（精度降低）
  （但不发给医院API时保留精度）

Level3: 敏感属性特殊处理
  过敏史/慢性病 → 永远不发给非医疗机构
```

### 12.3 AI输出审查规则

| 规则 | 检测正则 | 严重度 | 处理 |
|------|---------|--------|------|
| 禁止用药建议 | `/增加.*剂量\|停止服用\|换.*药/` | high | 替换为"建议咨询您的医生" |
| 禁止确定性诊断 | `/您患有\|这是.*病/` | critical | 阻断 |
| 禁止虚假承诺 | `/永远\|一定会\|保证/` | medium | 替换 |

---

## 十三、测试与验收

### 13.1 测试覆盖

- **pytest 全量测试**：220+ 测试用例通过
- **health**：alert写入后读取、空用户读取、limit限制、HTTP route读写、状态迁移
- **daily_life**：check-in写入后读取、空用户读取、limit限制、HTTP route读写
- **mental_care**：check-in写入后读取、空用户读取、limit限制、HTTP route读写
- **profile_memory**：写入后读取、空用户读取、按key查询、可读性派生字段
- **interactions**：profile memory写读、health alert、unsupported event、缺失字段、非法context、输入预处理、自然语言识别、澄清响应、decomposition_needed、routing guard、BERT adapter fallback
- **admin**：无token、错token、正确token、生产禁用
- **intent**：baseline/holdout分组评估、BERT直接识别/fallback/clarification/decomposition

### 13.2 验收脚本

| 脚本 | 功能 |
|------|------|
| `scripts/manual_smoke_typed_flow_history.py` | 四条typed flow写后读闭环验证 |
| `scripts/manual_smoke_http_api.py` | HTTP API基线验证 |
| `scripts/manual_smoke_typed_flow_http.py` | 四条typed flow HTTP闭环验证 |
| `scripts/manual_smoke_interactions_http.py` | 自然语言interactions入口验证 |
| `scripts/manual_smoke_user_overview_http.py` | 用户综合概览验证 |
| `scripts/dev_start_and_smoke.py` | 一键启动+smoke |
| `scripts/evaluate_intents.py` | 意图识别离线评估 |
| `scripts/check_bert_intent_runtime.py` | BERT模型自检 |
| `scripts/train_bert_intent_classifier.py` | BERT模型训练 |

---

## 十四、技术宝盒接入总览

| 技术 | 接入领域 | 具体作用 | 接入位置 |
|------|---------|---------|---------|
| HMM隐马尔可夫 | 健康+精神 | 步态序列建模、情绪状态序列建模 | 每步触发+20步窗口；7天情绪序列 |
| Fuzzy Logic模糊逻辑 | 健康+精神 | 血压连续风险评估、情绪强度量化 | 每次采集体征后；每次情绪分析 |
| 贝叶斯网络 | 智能汇报 | 多信号融合健康风险预测 | 定期分析时调用 |
| MAB多臂老虎机 | 日常管理 | Thompson Sampling学习最优提醒时段 | 推送调度系统 |
| PSO粒子群优化 | 日常管理 | 复杂长途行程多目标优化 | 远途出行规划 |
| 改良Dijkstra | 日常管理+Tool Agent | 台阶/坡度/遮阳/厕所重定义最优路径 | 近途出行规划 |
| 协同过滤 | 日常管理 | 找相似老年群体购物偏好 | 购物推荐 |
| Knowledge Graph | 日常管理+隐私卫士 | 防诈骗联系人分析、权限图谱 | 联系人风险检测 |
| 差分隐私 | 隐私卫士 | 统计查询加Laplace噪声 | 家属报告数据保护 |
| LangGraph | 全系统 | 多Agent协作工作流建模 | 复杂意图分解→多Agent协作完成 |
| 强化学习 | 运行时 | Supervisor任务调度策略优化 | 哪类任务在哪种系统状态下优先 |

---

## 十五、当前状态与演进路线

### 15.1 当前阶段：工程化基线阶段

**已完成**：
- ✅ 五层架构稳定：application/platform/domains/interfaces/shared
- ✅ 四条读写闭环：profile_memory/health/daily_life/mental_care
- ✅ 双层意图识别：rule_based/bert + placeholder/llm拆解
- ✅ 运行时韧性：快照/故障转移/降级
- ✅ 可观测+安全横切面
- ✅ 220+测试用例通过
- ✅ BERT bootstrap模型可运行
- ✅ Admin控制面最小token权限
- ✅ 文档治理完成归档

**尚未完成**：
- ⏳ 生产级分布式持久化方案
- ⏳ 完整用户/角色权限体系
- ⏳ 完整前端UI或多轮对话系统
- ⏳ BERT模型生产泛化能力
- ⏳ 第二层直接执行领域workflow
- ⏳ 更多真实业务域深度

### 15.2 演进路线图

| 阶段 | 目标 | 关键交付 |
|------|------|---------|
| P0 已收口 | 用户输入与意图识别工程闭环 | BERT高置信误判清单、InputPreprocessor、baseline/holdout分组评估 |
| P1 当前 | 收束现有读写闭环、改善验收体验 | 四条读写链路本地快速验收、三条领域flow不再只是占位 |
| P2 下一步 | 补足运行时、权限、持久化边界 | runtime snapshot清理策略、admin开发生产边界、更稳定的启动脚本 |
| P3 未来 | 智能化增强 | LLM深度意图拆分、多意图decomposition schema、用户状态注入、多轮session |

### 15.3 当前不该做的事

- ❌ 微服务拆分
- ❌ 引入重型工作流引擎
- ❌ 为了未来假想规模做大而全抽象
- ❌ 一次性扩很多新业务域
- ❌ 直接接入LLM深度拆分主链路

---

## 十六、附录

### 16.1 设计文档索引

| 文档 | 路径 | 核心内容 |
|------|------|---------|
| 系统核心机制深化设计 | `docs/archive/design-assets/系统核心机制深化设计（详细版）.docx` | 反馈闭环+紧急中断+冲突仲裁+Agent通信 |
| 记忆系统技术文档 | `docs/archive/design-assets/记忆系统技术文档.docx` | Hindsight四网络+三操作 |
| 用户输入处理与意图识别 | `docs/archive/design-assets/用户输入处理与意图识别技术文档.docx` | 双层意图识别架构 |
| 健康模块Agent | `docs/archive/design-assets/健康模块Agent设计文档.docx` | HMM+Fuzzy Logic+药物冲突 |
| 日常管理Agent | `docs/archive/design-assets/日常管理Agent设计文档.docx` | MAB+PSO+Dijkstra+防诈骗 |
| 精神模块总Agent | `docs/archive/design-assets/精神模块总Agent设计文档.docx` | HMM情绪感知+智慧传承 |
| Tool Agent | `docs/archive/design-assets/Tool-Agent设计文档.docx` | 外部系统集成+降级策略 |
| 智能汇报Agent | `docs/archive/design-assets/智能汇报Agent设计文档.docx` | 贝叶斯+HMM趋势+家属报告 |
| 隐私卫士Agent | `docs/archive/design-assets/隐私卫士Agent设计文档.docx` | 数据脱敏+差分隐私+AI输出审查 |
| 第一层-通信基础设施层 | `docs/archive/design-assets/第一层-通信基础设施层.docx` | 三种通信模式+消息信封+链路追踪 |
| 第二层-反馈闭环数据流层 | `docs/archive/design-assets/第二层-反馈闭环数据流层.docx` | L1/L2/L3三层反馈+置信度评分 |
| 第三层-冲突仲裁中间层 | `docs/archive/design-assets/第三层-冲突仲裁中间层.docx` | 四象限冲突+意图声明池+乐观锁 |
| 第四层-紧急中断覆盖层 | `docs/archive/design-assets/第四层-紧急中断覆盖层.docx` | P0-P3四级中断+六态状态机+快照恢复 |
| 个人信息库读写优化 | `docs/archive/design-assets/问题二-个人信息库读写压力优化方案.docx` | 三层分级存储+查询路由 |
| 技术宝盒激活方案 | `docs/archive/design-assets/问题三-技术宝盒激活方案.docx` | MAB/Fuzzy/HMM/PSO/LangGraph接入契约 |
| Supervisor单点问题优化 | `docs/archive/design-assets/项目单点问题优化方案.docx` | DecisionCore拆分+影子Supervisor+降级 |

### 16.2 术语表

| 术语 | 全称 | 含义 |
|------|------|------|
| CQRS | Command Query Responsibility Segregation | 命令查询职责分离 |
| HMM | Hidden Markov Model | 隐马尔可夫模型 |
| MAB | Multi-Armed Bandit | 多臂老虎机 |
| PSO | Particle Swarm Optimization | 粒子群优化 |
| RAG | Retrieval-Augmented Generation | 检索增强生成 |
| RRF | Reciprocal Rank Fusion | 倒数排名融合 |
| TTL | Time To Live | 生存时间 |
| BERT | Bidirectional Encoder Representations from Transformers | 双向编码器表示 |
| LLM | Large Language Model | 大语言模型 |
| ASR | Automatic Speech Recognition | 自动语音识别 |
| OCR | Optical Character Recognition | 光学字符识别 |
