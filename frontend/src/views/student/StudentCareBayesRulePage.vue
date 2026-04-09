<template>
  <div class="page-container bayes-page">
    <section class="hero-panel">
      <div class="hero-copy">
        <span class="hero-kicker">Student Care Bayesian Studio</span>
        <h1 class="hero-title">贝叶斯参数管理</h1>
        <p class="hero-subtitle">
          这不是单纯改数字，而是在调“系统如何理解证据”。先看规则画像，再做贝叶斯修正，最后按融合系数生成最终得分。
        </p>
        <div class="hero-tags">
          <span class="hero-tag">适用维度：情绪状态 / 校园安全 / 家庭支持</span>
          <span class="hero-tag">目标：让配置更容易理解、更容易调整、更不容易误改</span>
        </div>
      </div>
      <div class="hero-metrics">
        <div class="metric-card">
          <span class="metric-label">维度数量</span>
          <strong class="metric-value">{{ dimensionSummary.length }}</strong>
        </div>
        <div class="metric-card">
          <span class="metric-label">规则总数</span>
          <strong class="metric-value">{{ filteredRules.length }}</strong>
        </div>
        <div class="metric-card metric-card--accent">
          <span class="metric-label">数据库覆盖</span>
          <strong class="metric-value">{{ overriddenCount }}</strong>
        </div>
      </div>
    </section>

    <section class="principle-panel">
      <div class="section-head">
        <div>
          <div class="section-title">贝叶斯辅助层原理</div>
          <div class="section-subtitle">先理解这套判断逻辑，再改参数会更稳。</div>
        </div>
      </div>
      <div class="principle-grid">
        <article class="principle-card">
          <span class="principle-step">01</span>
          <strong>先算规则画像</strong>
          <p>系统先根据出勤、行为事件、家校沟通、关怀观察、AI 助手摘要等校内事实，计算规则画像基础分。</p>
        </article>
        <article class="principle-card">
          <span class="principle-step">02</span>
          <strong>再做概率修正</strong>
          <p>当关键证据命中时，系统会用先验概率和 LR 计算后验概率，判断这个维度是否需要被进一步抬高或压低。</p>
        </article>
        <article class="principle-card">
          <span class="principle-step">03</span>
          <strong>最后做融合</strong>
          <p>最终得分不是只看规则分，也不是只看贝叶斯结果，而是按融合系数共同决定。</p>
        </article>
      </div>
      <div class="formula-panel">
        <code>final_score = blend_alpha × linear_score + (1 - blend_alpha) × posterior</code>
      </div>
      <div class="guide-grid">
        <article class="guide-card">
          <strong>先验概率</strong>
          <p>主要影响“没有明显证据时，这个维度默认有多敏感”。调高后，即使事实较少，也更容易保持关注。</p>
        </article>
        <article class="guide-card">
          <strong>融合系数</strong>
          <p>主要影响“规则画像”和“贝叶斯修正”谁占比更高。越接近 1 越偏规则分，越低越容易受关键证据影响。</p>
        </article>
        <article class="guide-card">
          <strong>LR</strong>
          <p>主要影响“某条证据一旦命中，会把风险放大还是压低多少”。大于 1 倾向抬高风险，小于 1 常用于已处理或误报。</p>
        </article>
      </div>
    </section>

    <section class="toolbar-panel">
      <div class="toolbar-main">
        <div class="toolbar-group toolbar-group--search">
          <span class="toolbar-label">搜索规则</span>
          <el-input v-model="keyword" placeholder="搜索规则名称或参数键，例如 受伤 / resolved" clearable />
        </div>
        <div class="toolbar-group">
          <span class="toolbar-label">来源</span>
          <el-select v-model="selectedSource" placeholder="全部来源" clearable style="width: 160px">
            <el-option label="默认配置" value="default" />
            <el-option label="数据库覆盖" value="database" />
          </el-select>
        </div>
        <div class="toolbar-actions">
          <el-button :loading="loading" @click="fetchRules">刷新</el-button>
        </div>
      </div>

      <div class="dimension-switcher">
        <button
          v-for="item in dimensionSummary"
          :key="item.value"
          type="button"
          class="dimension-chip"
          :class="{ 'dimension-chip--active': activeDimension === item.value }"
          @click="activeDimension = item.value"
        >
          <span>{{ item.label }}</span>
          <strong>{{ dimensionRuleCount(item.value) }} 条</strong>
        </button>
      </div>
    </section>

    <section class="summary-grid">
      <article
        v-for="item in dimensionCards"
        :key="item.dimension"
        class="summary-card"
        :class="{ 'summary-card--active': activeDimension === item.dimension }"
        @click="activeDimension = item.dimension"
      >
        <div class="summary-head">
          <div>
            <div class="summary-title">{{ item.label }}</div>
            <div class="summary-caption">当前维度的整体基线与证据配置概览</div>
          </div>
          <span class="summary-badge">{{ item.overrides }} 个覆盖</span>
        </div>
        <div class="summary-stats">
          <div>
            <span class="summary-label">先验概率</span>
            <strong>{{ item.prior }}</strong>
          </div>
          <div>
            <span class="summary-label">融合系数</span>
            <strong>{{ item.blendAlpha }}</strong>
          </div>
          <div>
            <span class="summary-label">证据数量</span>
            <strong>{{ item.evidenceCount }}</strong>
          </div>
        </div>
      </article>
    </section>

    <section v-if="activeBaseRule" class="focus-panel">
      <div class="section-head">
        <div>
          <div class="section-title">{{ dimensionLabel(activeDimension) }}基础参数</div>
          <div class="section-subtitle">这一组参数决定该维度“默认有多敏感”，以及规则画像和贝叶斯修正如何融合。</div>
        </div>
        <el-button type="primary" @click="openEditor(activeBaseRule)">编辑基础参数</el-button>
      </div>

      <div class="base-grid">
        <article class="base-card">
          <span class="base-label">先验概率</span>
          <strong>{{ displayNumber(activeBaseRule.prior) }}</strong>
          <p>{{ basePriorExplanation(activeBaseRule) }}</p>
        </article>
        <article class="base-card">
          <span class="base-label">融合系数</span>
          <strong>{{ displayNumber(activeBaseRule.blend_alpha) }}</strong>
          <p>{{ baseBlendExplanation(activeBaseRule) }}</p>
        </article>
        <article class="base-card">
          <span class="base-label">当前状态</span>
          <strong>{{ activeBaseRule.enabled ? '启用' : '停用' }}</strong>
          <p>{{ activeBaseRule.source === 'database' ? '已被数据库覆盖，会直接影响后续画像与研判。' : '仍使用默认配置，尚未做个性化调整。' }}</p>
        </article>
      </div>
    </section>

    <section class="rules-panel">
      <div class="section-head">
        <div>
          <div class="section-title">{{ dimensionLabel(activeDimension) }}证据规则</div>
          <div class="section-subtitle">每张卡代表一类证据。调高后，系统会更看重这类事实；调低后，影响会变弱。</div>
        </div>
        <div class="rules-count">{{ activeEvidenceRules.length }} 条规则</div>
      </div>
      <div v-if="activeEvidenceRules.length" class="rules-grid">
        <article v-for="row in activeEvidenceRules" :key="ruleCardKey(row)" class="rule-card">
          <div class="rule-card__head">
            <div>
              <div class="rule-card__title">{{ humanizeRuleName(row) }}</div>
              <div class="rule-card__key">{{ row.evidence_key }}</div>
            </div>
            <div class="rule-card__badges">
              <span class="pill" :class="row.source === 'database' ? 'pill--db' : 'pill--default'">
                {{ row.source === 'database' ? '数据库覆盖' : '默认配置' }}
              </span>
              <span class="pill" :class="row.enabled ? 'pill--on' : 'pill--off'">
                {{ row.enabled ? '启用中' : '已停用' }}
              </span>
            </div>
          </div>

          <p class="rule-card__meaning">{{ ruleMeaning(row) }}</p>

          <div class="mini-stats">
            <div class="mini-stat">
              <span>LR</span>
              <strong>{{ displayNumber(row.likelihood_ratio) }}</strong>
            </div>
            <div class="mini-stat">
              <span>影响方向</span>
              <strong>{{ impactTag(row) }}</strong>
            </div>
            <div class="mini-stat">
              <span>应用结果</span>
              <strong>{{ row.enabled ? '参与判断' : '暂不参与' }}</strong>
            </div>
          </div>

          <div class="detail-list">
            <div class="detail-item">
              <span class="detail-label">主要受什么影响</span>
              <span class="detail-value">{{ ruleFactors(row) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">改动后会发生什么</span>
              <span class="detail-value">{{ impactText(row) }}</span>
            </div>
          </div>

          <div class="rule-card__actions">
            <button type="button" class="ghost-button" @click="toggleExpanded(ruleCardKey(row))">
              {{ isExpanded(ruleCardKey(row)) ? '收起详情' : '查看调参建议' }}
            </button>
            <el-button type="primary" @click="openEditor(row)">编辑</el-button>
          </div>

          <transition name="fade">
            <div v-if="isExpanded(ruleCardKey(row))" class="rule-card__expanded">
              <div class="expanded-block">
                <strong>业务提示</strong>
                <p>{{ ruleHint(row) }}</p>
              </div>
              <div class="expanded-block">
                <strong>调整建议</strong>
                <p>{{ adjustmentAdvice(row) }}</p>
              </div>
              <div class="expanded-block">
                <strong>备注</strong>
                <p>{{ row.description || '当前没有单独备注，建议在调整时写明原因，方便后续回看。' }}</p>
              </div>
            </div>
          </transition>
        </article>
      </div>

      <el-empty v-else description="当前筛选条件下没有可显示的证据规则" />
    </section>

    <el-dialog v-model="dialogVisible" width="620px" :title="dialogTitle" destroy-on-close>
      <div class="dialog-kicker">{{ editorMeta }}</div>
      <div class="dialog-helper">
        <strong>你正在调整：</strong>
        <span>{{ editorHelper }}</span>
      </div>
      <div class="dialog-guides">
        <div class="dialog-guide-card">
          <span class="dialog-guide-label">推荐范围</span>
          <strong>{{ recommendedRangeLabel }}</strong>
          <p>{{ recommendedRangeReason }}</p>
        </div>
        <div class="dialog-guide-card" :class="{ 'dialog-guide-card--warning': cautionLevel !== 'normal' }">
          <span class="dialog-guide-label">谨慎提示</span>
          <strong>{{ cautionTitle }}</strong>
          <p>{{ cautionMessage }}</p>
        </div>
      </div>

      <el-form :model="formState" label-width="120px">
        <el-form-item label="是否启用">
          <el-switch v-model="formState.enabled" />
        </el-form-item>
        <template v-if="editingRow?.evidence_key === BASE_KEY">
          <el-form-item label="先验概率">
            <el-input-number v-model="formState.prior" :min="0" :max="1" :step="0.01" style="width: 100%" />
          </el-form-item>
          <el-form-item label="融合系数">
            <el-input-number v-model="formState.blend_alpha" :min="0" :max="1" :step="0.01" style="width: 100%" />
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item label="风险放大/抑制系数">
            <el-input-number v-model="formState.likelihood_ratio" :min="0.01" :step="0.05" style="width: 100%" />
          </el-form-item>
        </template>
        <el-form-item label="调整备注">
          <el-input
            v-model="formState.description"
            type="textarea"
            :rows="4"
            placeholder="建议写明：为什么要调、希望解决什么问题、适用于哪些学生情形"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getStudentCareBayesRules, updateStudentCareBayesRule } from '@/api/studentCareBayes'

const BASE_KEY = '__base__'

const loading = ref(false)
const saving = ref(false)
const selectedSource = ref('')
const keyword = ref('')
const rules = ref([])
const dimensions = ref([])
const activeDimension = ref('emotion')
const dialogVisible = ref(false)
const editingRow = ref(null)
const expandedKeys = ref([])

const formState = reactive({
  enabled: true,
  prior: null,
  blend_alpha: null,
  likelihood_ratio: null,
  description: ''
})

const RULE_COPY = {
  __base__: {
    name: '基础参数',
    meaning: '用于设定该维度的整体基础敏感度与融合方式。',
    hint: '如果你觉得这个维度整体偏高、偏低，或想提高/降低贝叶斯修正的影响，优先调这里。'
  },
  assistant_self_report_assault: {
    name: '学生主动表达被打或受伤',
    meaning: '学生在 AI 助手中明确提到被打、受伤、受欺负等直接安全线索。',
    hint: '适合在学校希望更重视学生主动求助时调高。'
  },
  assistant_self_report_distress: {
    name: '学生主动表达痛苦情绪',
    meaning: '学生主动表达难受、崩溃、压抑、害怕等明显情绪困扰。',
    hint: '如果学校更关注学生主动求助，可适当调高。'
  },
  attendance_bruise_remark: {
    name: '出勤备注出现受伤线索',
    meaning: '出勤备注中出现淤青、受伤、疑似被打等描述。',
    hint: '适合在班主任日常观察记录较可靠时调高。'
  },
  attendance_worried_remark: {
    name: '出勤备注出现担忧状态',
    meaning: '出勤备注中出现神情担忧、状态不稳、明显焦虑等线索。',
    hint: '常用于情绪或安全维度的早期提醒。'
  },
  attendance_family_issue: {
    name: '出勤备注出现家庭原因',
    meaning: '出勤备注中出现家庭冲突、照护不足、家庭变故等信息。',
    hint: '适合在学校希望更快识别家庭支持不足时调高。'
  },
  care_observation_emotion: {
    name: '关怀观察记录到情绪异常',
    meaning: '教师或关怀记录中写明了低落、焦虑、压抑等情绪表现。',
    hint: '如果一线教师观察普遍比较准确，可以适度调高。'
  },
  care_talk_low_mood: {
    name: '谈话记录出现情绪低落',
    meaning: '关怀谈话中学生明确表达低落、无助、持续烦闷等状态。',
    hint: '正式谈话通常比零散观察更可靠，适合保持中高权重。'
  },
  family_negative_contact: {
    name: '家校沟通出现负面反馈',
    meaning: '家校沟通中出现支持不足、冲突加剧、照护缺失等负面信息。',
    hint: '会同时影响情绪与家庭支持两个维度。'
  },
  family_contact_negative: {
    name: '家校沟通提示家庭支持不足',
    meaning: '家校沟通记录表明家庭陪伴不足、沟通紧张或支持偏弱。',
    hint: '如果希望更重视家校沟通信号，可以适度调高。'
  },
  family_violence_hint: {
    name: '家庭暴力或强冲突线索',
    meaning: '出现疑似家庭暴力、严重争吵、明显家庭威胁等高敏感线索。',
    hint: '通常应保持较高权重，因为它对安全和家庭支持都很关键。'
  },
  score_drop_emotion: {
    name: '成绩下滑伴随情绪风险',
    meaning: '成绩明显下滑，被视作情绪波动或压力上升的辅助线索。',
    hint: '更适合作为辅助证据，不建议高于直接事实线索。'
  },
  behavior_bullying: {
    name: '行为事件涉及欺凌',
    meaning: '行为事件中出现欺凌、霸凌、持续针对等校园安全风险。',
    hint: '如果学校对欺凌事件零容忍，通常应保持较高权重。'
  },
  behavior_conflict: {
    name: '行为事件涉及冲突',
    meaning: '行为事件中出现冲突、打架、推搡等直接安全线索。',
    hint: '适合调节一般冲突对校园安全的影响强度。'
  },
  tag_family_hardship: {
    name: '学生标签含家庭困难',
    meaning: '学生标签中已有家庭困难、照护不足等背景信息。',
    hint: '这是背景线索，通常不应高于直接事实证据。'
  },
  teacher_review_false_alarm: {
    name: '老师确认属于误报',
    meaning: '老师复核后确认该问题不构成真实风险，或属于误判。',
    hint: '这类参数通常应小于 1，用于压低风险。'
  },
  teacher_review_resolved: {
    name: '老师确认问题已处理',
    meaning: '老师复核后确认已完成干预，当前问题已缓解或已解决。',
    hint: '这类参数通常应小于 1，避免旧风险长期残留。'
  }
}

const DEFAULT_RULE_COPY = {
  name: '自定义证据项',
  meaning: '这是一条可参与贝叶斯辅助判断的证据规则。',
  hint: '建议结合学校真实案例，在备注中写清适用场景。'
}

const dimensionSummary = computed(() =>
  (dimensions.value || []).map((item) => ({
    value: item,
    label: dimensionLabel(item)
  }))
)

const overriddenCount = computed(() => rules.value.filter((item) => item.source === 'database').length)

const filteredRules = computed(() =>
  rules.value.filter((item) => {
    if (selectedSource.value && item.source !== selectedSource.value) return false
    if (!keyword.value) return true
    const content = [
      item.evidence_key,
      humanizeRuleName(item),
      ruleMeaning(item),
      ruleFactors(item),
      ruleHint(item)
    ]
      .join(' ')
      .toLowerCase()
    return content.includes(keyword.value.toLowerCase())
  })
)

const dimensionCards = computed(() =>
  dimensionSummary.value.map((item) => {
    const rows = filteredRules.value.filter((row) => row.dimension === item.value)
    const base = rows.find((row) => row.evidence_key === BASE_KEY) || {}
    const evidenceRows = rows.filter((row) => row.evidence_key !== BASE_KEY)
    return {
      dimension: item.value,
      label: item.label,
      prior: displayNumber(base.prior),
      blendAlpha: displayNumber(base.blend_alpha),
      evidenceCount: evidenceRows.length,
      overrides: rows.filter((row) => row.source === 'database').length
    }
  })
)

const activeDimensionRules = computed(() =>
  filteredRules.value.filter((row) => row.dimension === activeDimension.value)
)

const activeBaseRule = computed(() =>
  activeDimensionRules.value.find((row) => row.evidence_key === BASE_KEY) || null
)

const activeEvidenceRules = computed(() =>
  activeDimensionRules.value.filter((row) => row.evidence_key !== BASE_KEY)
)

const dialogTitle = computed(() => {
  if (!editingRow.value) return '编辑贝叶斯参数'
  return editingRow.value.evidence_key === BASE_KEY ? '编辑基础参数' : '编辑证据规则'
})

const editorMeta = computed(() => {
  if (!editingRow.value) return ''
  return `${dimensionLabel(editingRow.value.dimension)} / ${humanizeRuleName(editingRow.value)}`
})

const editorHelper = computed(() => {
  if (!editingRow.value) return ''
  if (editingRow.value.evidence_key === BASE_KEY) {
    return '先验概率决定默认敏感度，融合系数决定规则画像和贝叶斯辅助层谁占比更高。一般只在你觉得这个维度整体偏高或偏低时调整。'
  }
  return `${ruleMeaning(editingRow.value)} ${impactText(editingRow.value)}`
})

const recommendedRangeLabel = computed(() => {
  if (!editingRow.value) return '-'
  const meta = getRangeMeta(editingRow.value)
  if (editingRow.value.evidence_key === BASE_KEY) {
    return `先验概率 ${formatRange(meta.priorRange)} / 融合系数 ${formatRange(meta.blendRange)}`
  }
  return formatRange(meta.lrRange)
})

const recommendedRangeReason = computed(() => {
  if (!editingRow.value) return ''
  return getRangeMeta(editingRow.value).reason
})

const cautionLevel = computed(() => {
  if (!editingRow.value) return 'normal'
  const meta = getRangeMeta(editingRow.value)
  if (editingRow.value.evidence_key === BASE_KEY) {
    const priorLevel = evaluateRangeLevel(formState.prior, meta.priorRange)
    const blendLevel = evaluateRangeLevel(formState.blend_alpha, meta.blendRange)
    if (priorLevel === 'danger' || blendLevel === 'danger') return 'danger'
    if (priorLevel === 'warning' || blendLevel === 'warning') return 'warning'
    return 'normal'
  }
  return evaluateRangeLevel(formState.likelihood_ratio, meta.lrRange)
})

const cautionTitle = computed(() => {
  if (!editingRow.value) return ''
  if (cautionLevel.value === 'danger') return '当前数值已明显偏离推荐范围'
  if (cautionLevel.value === 'warning') return '当前数值接近或轻微超出推荐范围'
  return '当前数值处于常见可控区间'
})

const cautionMessage = computed(() => {
  if (!editingRow.value) return ''
  if (editingRow.value.evidence_key === BASE_KEY) {
    if (cautionLevel.value === 'danger') {
      return '如果同时提高先验概率、降低融合系数，这个维度会明显变得更敏感，建议只在误报和漏报情况已经较清楚时再这样调整。'
    }
    if (cautionLevel.value === 'warning') {
      return '当前基础参数已开始偏离常见配置，保存前建议再确认：你是想让这个维度整体更敏感，还是只想强化某类具体证据。'
    }
    return '这组基础参数更适合做整体微调。如果你只是想加强某条具体线索，优先去调整对应证据规则。'
  }
  if (cautionLevel.value === 'danger') {
    return `这条规则一旦继续偏离推荐范围，${extremeImpactText(editingRow.value)}`
  }
  if (cautionLevel.value === 'warning') {
    return '当前值已经开始偏强或偏弱，保存后系统对这类证据的响应会更明显，建议结合近期真实案例一起判断。'
  }
  return '这个区间通常比较稳，既能体现证据作用，也不容易因为单条线索把结果拉得过猛。'
})

watch(
  dimensionSummary,
  (value) => {
    if (!value.length) return
    if (!value.some((item) => item.value === activeDimension.value)) {
      activeDimension.value = value[0].value
    }
  },
  { immediate: true }
)

onMounted(() => {
  fetchRules()
})

async function fetchRules() {
  loading.value = true
  try {
    const res = await getStudentCareBayesRules()
    rules.value = res.rules || []
    dimensions.value = res.dimensions || []
  } finally {
    loading.value = false
  }
}

function openEditor(row) {
  editingRow.value = { ...row }
  formState.enabled = row.enabled
  formState.prior = row.prior
  formState.blend_alpha = row.blend_alpha
  formState.likelihood_ratio = row.likelihood_ratio
  formState.description = row.description || ''
  dialogVisible.value = true
}

async function handleSave() {
  if (!editingRow.value) return
  if (cautionLevel.value === 'danger') {
    try {
      await ElMessageBox.confirm(
        `${cautionMessage.value}\n\n确认继续保存这次配置修改吗？`,
        '参数超出推荐范围',
        {
          type: 'warning',
          confirmButtonText: '仍然保存',
          cancelButtonText: '返回调整'
        }
      )
    } catch {
      return
    }
  }
  saving.value = true
  try {
    const payload = {
      enabled: formState.enabled,
      description: formState.description || null
    }
    if (editingRow.value.evidence_key === BASE_KEY) {
      payload.prior = formState.prior
      payload.blend_alpha = formState.blend_alpha
    } else {
      payload.likelihood_ratio = formState.likelihood_ratio
    }
    await updateStudentCareBayesRule(editingRow.value.dimension, editingRow.value.evidence_key, payload)
    ElMessage.success('贝叶斯参数已更新')
    dialogVisible.value = false
    fetchRules()
  } finally {
    saving.value = false
  }
}

function dimensionRuleCount(dimension) {
  return filteredRules.value.filter((row) => row.dimension === dimension && row.evidence_key !== BASE_KEY).length
}

function ruleCopy(row) {
  return RULE_COPY[row?.evidence_key] || DEFAULT_RULE_COPY
}

function humanizeRuleName(row) {
  if (row?.evidence_key === BASE_KEY) return `${dimensionLabel(row.dimension)}基础参数`
  return ruleCopy(row).name
}

function ruleMeaning(row) {
  if (row?.evidence_key === BASE_KEY) return `${dimensionLabel(row.dimension)}维度的整体基础参数。`
  return ruleCopy(row).meaning
}

function ruleHint(row) {
  if (row?.evidence_key === BASE_KEY) {
    return '如果你觉得这个维度整体偏高、偏低，或希望更稳/更敏感，优先调整这里。'
  }
  return ruleCopy(row).hint
}

function ruleFactors(row) {
  if (row?.evidence_key === BASE_KEY) {
    return '主要受该维度整体误报率、漏报率，以及学校希望它更稳还是更敏感的策略影响。'
  }
  const mapping = {
    assistant_self_report_assault: '主要受学生在 AI 助手中主动表达被打、受伤、被欺负等事实影响。',
    assistant_self_report_distress: '主要受学生在 AI 助手中主动表达难受、崩溃、害怕等情绪事实影响。',
    attendance_bruise_remark: '主要受出勤备注中出现淤青、受伤、可见异常状态等客观描述影响。',
    attendance_worried_remark: '主要受出勤备注中神情担忧、状态不稳、明显焦虑等观察记录影响。',
    attendance_family_issue: '主要受出勤备注中出现家庭变故、照护不足、家庭冲突等事实影响。',
    care_observation_emotion: '主要受教师观察、关怀记录里明确写下的情绪异常表现影响。',
    care_talk_low_mood: '主要受正式谈话中学生对低落、无助、压抑等自述影响。',
    family_negative_contact: '主要受家校沟通中支持不足、冲突、照护缺失等负面反馈影响。',
    family_contact_negative: '主要受家校沟通摘要里直接提到的家庭支持不足影响。',
    family_violence_hint: '主要受家庭暴力、强冲突、威胁等高敏感事实线索影响。',
    score_drop_emotion: '主要受成绩明显下滑且被视作情绪波动辅助信号的情况影响。',
    behavior_bullying: '主要受欺凌、霸凌、持续针对等行为事件影响。',
    behavior_conflict: '主要受打架、推搡、冲突等一般安全事件影响。',
    tag_family_hardship: '主要受学生背景标签中的家庭困难、照护不足等长期线索影响。',
    teacher_review_false_alarm: '主要受老师复核后确认误报、无实质风险的结论影响。',
    teacher_review_resolved: '主要受老师复核后确认已处理、已缓解的结论影响。'
  }
  return mapping[row?.evidence_key] || '主要受这条证据对应的校内事实是否真实、直接、稳定影响。'
}

function impactTag(row) {
  if (row?.evidence_key === BASE_KEY) return '整体基线'
  const lr = Number(row?.likelihood_ratio || 0)
  if (lr > 1) return '更易抬高风险'
  if (lr > 0 && lr < 1) return '更易压低风险'
  return '待设置'
}

function impactText(row) {
  if (row?.evidence_key === BASE_KEY) {
    return '会影响这个维度在缺少明显事实时的默认敏感度，以及规则分和贝叶斯修正的融合比例。'
  }
  const lr = Number(row?.likelihood_ratio || 0)
  if (lr > 1) return '命中这条证据后，该维度风险会更容易被抬高。'
  if (lr > 0 && lr < 1) return '命中这条证据后，该维度风险会被压低，多用于已处理或误报。'
  return '当前尚未设置明确影响。'
}

function adjustmentAdvice(row) {
  if (row?.evidence_key === BASE_KEY) {
    return '如果这个维度经常整体偏高，先尝试下调先验概率；如果关键证据出现时响应太慢，再考虑下调融合系数，让贝叶斯修正更有影响。'
  }
  const lr = Number(row?.likelihood_ratio || 0)
  if (lr >= 3) {
    return '当前这条证据影响较强，建议只在这类事实非常可靠、且学校希望快速预警时继续上调。'
  }
  if (lr > 1) {
    return '如果你觉得系统对这类事实反应不够敏感，可以适当上调；如果经常误报，则应往下调。'
  }
  return '这条规则主要用于压低风险。若发现已处理后风险仍残留太久，可以进一步调低；如果压得过猛，则适当调高。'
}

function basePriorExplanation(row) {
  const prior = Number(row?.prior || 0)
  if (prior >= 0.3) return '当前默认敏感度偏高，即使事实较少，也更容易保持关注。'
  if (prior >= 0.15) return '当前默认敏感度适中，适合希望保持稳定提醒的场景。'
  return '当前默认敏感度偏保守，更依赖明确事实后再抬高风险。'
}

function baseBlendExplanation(row) {
  const blend = Number(row?.blend_alpha || 0)
  if (blend >= 0.75) return '当前更偏向规则画像，整体会更稳，不容易被单条证据剧烈带动。'
  if (blend >= 0.55) return '当前规则画像和贝叶斯修正较为均衡。'
  return '当前更容易受关键证据影响，适合希望对突发线索更敏感的场景。'
}

function ruleCardKey(row) {
  return `${row.dimension}:${row.evidence_key}`
}

function toggleExpanded(key) {
  if (expandedKeys.value.includes(key)) {
    expandedKeys.value = expandedKeys.value.filter((item) => item !== key)
    return
  }
  expandedKeys.value = [...expandedKeys.value, key]
}

function isExpanded(key) {
  return expandedKeys.value.includes(key)
}

function getRangeMeta(row) {
  const baseRangeByDimension = {
    emotion: {
      priorRange: [0.08, 0.22],
      blendRange: [0.65, 0.85],
      reason: '情绪状态建议以稳定为主，避免因为单条模糊情绪线索被过度拉高。'
    },
    safety: {
      priorRange: [0.08, 0.2],
      blendRange: [0.55, 0.8],
      reason: '校园安全需要对强证据敏感，但也要避免在缺少直接事实时整体过高。'
    },
    family: {
      priorRange: [0.08, 0.2],
      blendRange: [0.65, 0.85],
      reason: '家庭支持更适合结合长期观察与家校沟通，通常不建议过于激进。'
    }
  }
  const lrRanges = {
    assistant_self_report_assault: [2.5, 4.5],
    assistant_self_report_distress: [1.8, 3.2],
    attendance_bruise_remark: [2.0, 3.5],
    attendance_worried_remark: [1.3, 2.2],
    attendance_family_issue: [1.3, 2.2],
    care_observation_emotion: [1.8, 2.8],
    care_talk_low_mood: [1.8, 2.8],
    family_negative_contact: [1.3, 2.2],
    family_contact_negative: [1.5, 2.5],
    family_violence_hint: [2.0, 3.2],
    score_drop_emotion: [1.2, 2.0],
    behavior_bullying: [2.5, 4.2],
    behavior_conflict: [1.6, 2.8],
    tag_family_hardship: [1.2, 2.0],
    teacher_review_false_alarm: [0.15, 0.6],
    teacher_review_resolved: [0.2, 0.6]
  }
  if (row?.evidence_key === BASE_KEY) {
    return baseRangeByDimension[row?.dimension] || baseRangeByDimension.emotion
  }
  return {
    lrRange: lrRanges[row?.evidence_key] || [1.0, 2.5],
    reason: `${humanizeRuleName(row)}建议先在较稳的常见区间内微调，确认效果后再继续放大。`
  }
}

function formatRange(range) {
  if (!Array.isArray(range) || range.length !== 2) return '-'
  return `${displayNumber(range[0])} - ${displayNumber(range[1])}`
}

function evaluateRangeLevel(value, range) {
  if (value === null || value === undefined || value === '' || !Array.isArray(range)) return 'normal'
  const numeric = Number(value)
  const [min, max] = range
  const span = Math.max(max - min, 0.01)
  if (numeric < min - span * 0.4 || numeric > max + span * 0.4) return 'danger'
  if (numeric < min || numeric > max) return 'warning'
  return 'normal'
}

function extremeImpactText(row) {
  const lr = Number(row?.likelihood_ratio || 0)
  if (lr > 1) {
    return '系统可能会因为这类证据过快抬高风险，尤其在事实还不够充分时更容易出现偏紧判断。'
  }
  return '系统可能会把已处理或误报类信息压得过快，导致仍需持续观察的情况被过早降下来。'
}

function displayNumber(value) {
  if (value === null || value === undefined || value === '') return '-'
  return Number(value).toFixed(2).replace(/\.00$/, '')
}

function dimensionLabel(value) {
  return {
    emotion: '情绪状态',
    safety: '校园安全',
    family: '家庭支持'
  }[value] || value
}
</script>

<style scoped lang="scss">
.bayes-page {
  display: grid;
  gap: 18px;
}

.hero-panel,
.principle-panel,
.toolbar-panel,
.focus-panel,
.rules-panel {
  padding: 22px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.14);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.05);
}

.hero-panel {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.9fr);
  gap: 18px;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(56, 189, 248, 0.16), transparent 28%),
    radial-gradient(circle at bottom right, rgba(14, 165, 233, 0.14), transparent 22%),
    linear-gradient(135deg, #f8fdff 0%, #ffffff 45%, #f8fafc 100%);
}

.hero-kicker {
  display: inline-flex;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(12, 74, 110, 0.08);
  color: #0c4a6e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-title {
  margin: 14px 0 10px;
  color: #0f172a;
  font-size: 30px;
  line-height: 1.05;
}

.hero-subtitle {
  margin: 0;
  max-width: 760px;
  color: #475569;
  line-height: 1.7;
}

.hero-tags {
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-tag {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.14);
  color: #334155;
  font-size: 12px;
}

.hero-metrics {
  display: grid;
  gap: 12px;
  align-content: end;
}

.metric-card {
  padding: 16px 18px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.metric-card--accent {
  background: linear-gradient(135deg, #eff6ff, #f8fafc);
}

.metric-label {
  display: block;
  font-size: 12px;
  color: #64748b;
}

.metric-value {
  display: block;
  margin-top: 8px;
  font-size: 28px;
  color: #0f172a;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.section-title {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
}

.section-subtitle {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.principle-grid,
.guide-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.principle-card,
.guide-card {
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.95), rgba(255, 255, 255, 0.96));
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.principle-step {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  background: #0f172a;
  color: #f8fafc;
  font-size: 12px;
  font-weight: 700;
}

.principle-card strong,
.guide-card strong {
  display: block;
  margin-top: 12px;
  font-size: 15px;
  color: #0f172a;
}

.principle-card p,
.guide-card p {
  margin: 8px 0 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}

.formula-panel {
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: 16px;
  background: #0f172a;
  color: #f8fafc;
  overflow-x: auto;
}

.formula-panel code {
  font-size: 13px;
}

.toolbar-panel {
  display: grid;
  gap: 16px;
}

.toolbar-main {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-items: end;
}

.toolbar-group {
  display: grid;
  gap: 8px;
}

.toolbar-group--search {
  min-width: 280px;
  flex: 1;
}

.toolbar-label {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.toolbar-actions {
  margin-left: auto;
}

.dimension-switcher {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.dimension-chip {
  appearance: none;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: #fff;
  padding: 14px 16px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  color: #334155;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.dimension-chip span {
  font-weight: 700;
}

.dimension-chip strong {
  font-size: 12px;
  color: #64748b;
}

.dimension-chip:hover,
.dimension-chip--active {
  transform: translateY(-1px);
  border-color: rgba(14, 165, 233, 0.38);
  box-shadow: 0 12px 24px rgba(14, 165, 233, 0.08);
}

.dimension-chip--active {
  background: linear-gradient(135deg, #eff6ff, #f8fafc);
  color: #0f172a;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
}

.summary-card {
  padding: 18px;
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.92));
  border: 1px solid rgba(148, 163, 184, 0.14);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.04);
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.summary-card:hover,
.summary-card--active {
  transform: translateY(-2px);
  border-color: rgba(14, 165, 233, 0.32);
  box-shadow: 0 18px 36px rgba(14, 165, 233, 0.08);
}

.summary-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.summary-title {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.summary-caption {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
}

.summary-badge {
  align-self: start;
  white-space: nowrap;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(14, 165, 233, 0.1);
  color: #0369a1;
  font-size: 12px;
  font-weight: 700;
}

.summary-stats,
.base-grid,
.rules-grid {
  margin-top: 16px;
}

.summary-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.summary-label,
.base-label {
  display: block;
  font-size: 11px;
  color: #64748b;
}

.summary-stats strong,
.base-card strong {
  display: block;
  margin-top: 6px;
  color: #0f172a;
  font-size: 20px;
}

.base-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.base-card {
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fbff, #fff);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.base-card p {
  margin: 10px 0 0;
  font-size: 13px;
  line-height: 1.7;
  color: #475569;
}

.rules-count {
  white-space: nowrap;
  font-size: 13px;
  color: #64748b;
}

.rules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 14px;
}

.rule-card {
  padding: 18px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.94));
  border: 1px solid rgba(148, 163, 184, 0.14);
  box-shadow: 0 16px 30px rgba(15, 23, 42, 0.04);
}

.rule-card__head,
.rule-card__actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.rule-card__title {
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.4;
}

.rule-card__key {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
  word-break: break-all;
}

.rule-card__badges {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.rule-card__meaning {
  margin: 14px 0 0;
  color: #334155;
  line-height: 1.7;
}

.mini-stats {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.mini-stat {
  padding: 12px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.mini-stat span {
  display: block;
  font-size: 11px;
  color: #64748b;
}

.mini-stat strong {
  display: block;
  margin-top: 6px;
  color: #0f172a;
  font-size: 16px;
}

.detail-list {
  margin-top: 16px;
  display: grid;
  gap: 10px;
}

.detail-item {
  display: grid;
  gap: 6px;
}

.detail-label {
  font-size: 12px;
  font-weight: 700;
  color: #475569;
}

.detail-value {
  color: #64748b;
  line-height: 1.7;
  font-size: 13px;
}

.rule-card__actions {
  margin-top: 16px;
  align-items: center;
}

.ghost-button {
  appearance: none;
  border: none;
  background: transparent;
  padding: 0;
  color: #0369a1;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.rule-card__expanded {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed rgba(148, 163, 184, 0.28);
  display: grid;
  gap: 12px;
}

.expanded-block {
  padding: 14px;
  border-radius: 16px;
  background: #f8fafc;
}

.expanded-block strong {
  display: block;
  color: #0f172a;
  font-size: 13px;
}

.expanded-block p {
  margin: 8px 0 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}

.pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.pill--db {
  background: rgba(14, 165, 233, 0.1);
  color: #0369a1;
}

.pill--default {
  background: rgba(100, 116, 139, 0.12);
  color: #475569;
}

.pill--on {
  background: rgba(34, 197, 94, 0.1);
  color: #15803d;
}

.pill--off {
  background: rgba(244, 63, 94, 0.1);
  color: #be123c;
}

.dialog-kicker {
  margin-bottom: 10px;
  color: #0369a1;
  font-size: 12px;
  font-weight: 700;
}

.dialog-helper {
  margin-bottom: 16px;
  padding: 14px 16px;
  border-radius: 14px;
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}

.dialog-helper strong {
  color: #0f172a;
  margin-right: 6px;
}

.dialog-guides {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.dialog-guide-card {
  padding: 14px 16px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.dialog-guide-card--warning {
  background: #fff7ed;
  border-color: rgba(249, 115, 22, 0.22);
}

.dialog-guide-label {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.dialog-guide-card strong {
  display: block;
  margin-top: 6px;
  color: #0f172a;
  font-size: 16px;
}

.dialog-guide-card p {
  margin: 8px 0 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (max-width: 1100px) {
  .hero-panel,
  .principle-grid,
  .guide-grid,
  .base-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .summary-stats,
  .mini-stats,
  .dialog-guides {
    grid-template-columns: 1fr;
  }

  .toolbar-actions {
    margin-left: 0;
  }

  .rule-card__head,
  .rule-card__actions,
  .section-head {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
