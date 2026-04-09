<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">研判评估</div>
        <div class="page-subtitle">聚焦老师复核结果，帮助我们判断学生关怀研判是否稳、是否准。</div>
      </div>
      <div class="header-actions">
        <el-button size="small" :loading="loading" @click="fetchSummary">刷新</el-button>
        <el-button size="small" type="primary" @click="exportSummary">导出</el-button>
      </div>
    </div>

    <div class="filter-bar">
      <div class="filter-item">
        <span class="filter-label">时间范围</span>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          unlink-panels
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
        />
      </div>
      <div v-if="isAdmin" class="filter-item">
        <span class="filter-label">班级</span>
        <el-select v-model="classId" placeholder="全部班级" clearable filterable>
          <el-option v-for="item in classOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </div>
      <el-button size="small" type="success" @click="fetchSummary">应用筛选</el-button>
    </div>

    <div class="stats-grid">
      <div class="stats-card">
        <div class="stats-label">总研判记录</div>
        <div class="stats-value">{{ formatCount(summary.total_records) }}</div>
      </div>
      <div class="stats-card">
        <div class="stats-label">已复核</div>
        <div class="stats-value">{{ formatCount(summary.confirmed_reviews) }}</div>
        <div class="stats-meta">复核覆盖率 {{ formatPercent(summary.reviewed_ratio) }}</div>
      </div>
      <div class="stats-card">
        <div class="stats-label">老师确认真风险</div>
        <div class="stats-value accent-danger">{{ formatCount(summary.true_risk_count) }}</div>
      </div>
      <div class="stats-card">
        <div class="stats-label">老师判定误报</div>
        <div class="stats-value accent-warn">{{ formatCount(summary.false_alarm_count) }}</div>
      </div>
      <div class="stats-card">
        <div class="stats-label">系统与老师一致率</div>
        <div class="stats-value accent-primary">{{ formatPercent(summary.agreement_rate) }}</div>
      </div>
      <div class="stats-card">
        <div class="stats-label">老师平均确认信心</div>
        <div class="stats-value">{{ formatConfidence(summary.avg_teacher_confidence) }}</div>
        <div class="stats-meta">满分 5 分</div>
      </div>
    </div>

    <div class="panel-grid">
      <div class="panel-card panel-wide">
        <div class="panel-title">规则影响洞察</div>
        <div class="impact-grid">
          <div class="impact-card">
            <div class="impact-label">受数据缺口影响的复核记录</div>
            <div class="impact-value">{{ formatCount(summary.rule_impact.data_gap_record_count) }}</div>
            <div class="impact-meta">其中老师最终确认风险 {{ formatCount(summary.rule_impact.teacher_confirmed_with_data_gap) }}</div>
          </div>
          <div class="impact-card">
            <div class="impact-label">出现保护性证据的复核记录</div>
            <div class="impact-value accent-success">{{ formatCount(summary.rule_impact.protective_record_count) }}</div>
            <div class="impact-meta">其中老师判为误报 {{ formatCount(summary.rule_impact.false_alarm_with_protective) }}</div>
          </div>
          <div class="impact-card">
            <div class="impact-label">存在历史衰减信号的复核记录</div>
            <div class="impact-value accent-primary">{{ formatCount(summary.rule_impact.attenuated_record_count) }}</div>
            <div class="impact-meta">其中老师最终确认风险 {{ formatCount(summary.rule_impact.teacher_confirmed_with_attenuated) }}</div>
          </div>
          <div class="impact-card">
            <div class="impact-label">误报且伴随数据缺口</div>
            <div class="impact-value accent-warn">{{ formatCount(summary.rule_impact.false_alarm_with_data_gap) }}</div>
            <div class="impact-meta">可优先回查缺勤、家校沟通、AI 摘要等缺失来源</div>
          </div>
        </div>
      </div>
      <div class="panel-card">
        <div class="panel-title">场景分布</div>
        <div v-if="sceneBars.length" class="bar-list">
          <div v-for="item in sceneBars" :key="item.key" class="bar-item">
            <div class="bar-head">
              <span>{{ item.label }}</span>
              <span>{{ formatCount(item.count) }}</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill bar-fill-blue" :style="{ width: item.percent + '%' }" />
            </div>
          </div>
        </div>
        <div v-else class="empty-text">暂无复核场景数据</div>
      </div>

      <div class="panel-card">
        <div class="panel-title">严重度分布</div>
        <div v-if="severityBars.length" class="pill-grid">
          <div v-for="item in severityBars" :key="item.key" class="pill-card">
            <div class="pill-label">{{ item.label }}</div>
            <div class="pill-value">{{ formatCount(item.count) }}</div>
          </div>
        </div>
        <div v-else class="empty-text">暂无严重度数据</div>
      </div>

      <div class="panel-card">
        <div class="panel-title">处理状态</div>
        <div v-if="resolutionBars.length" class="bar-list">
          <div v-for="item in resolutionBars" :key="item.key" class="bar-item">
            <div class="bar-head">
              <span>{{ item.label }}</span>
              <span>{{ formatCount(item.count) }}</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill" :class="item.className" :style="{ width: item.percent + '%' }" />
            </div>
          </div>
        </div>
        <div v-else class="empty-text">暂无处理状态数据</div>
      </div>

      <div class="panel-card">
        <div class="panel-title">系统与老师对照</div>
        <div class="compare-grid">
          <div class="compare-item">
            <div class="compare-label">系统提示风险，老师确认属实</div>
            <div class="compare-value accent-success">
              {{ formatCount(summary.system_vs_teacher.system_positive_teacher_yes) }}
            </div>
          </div>
          <div class="compare-item">
            <div class="compare-label">系统提示风险，老师判定误报</div>
            <div class="compare-value accent-warn">
              {{ formatCount(summary.system_vs_teacher.system_positive_teacher_no) }}
            </div>
          </div>
          <div class="compare-item">
            <div class="compare-label">系统判低风险，老师后续确认有风险</div>
            <div class="compare-value accent-danger">
              {{ formatCount(summary.system_vs_teacher.system_low_teacher_yes) }}
            </div>
          </div>
          <div class="compare-item">
            <div class="compare-label">系统判低风险，老师也认为无风险</div>
            <div class="compare-value">
              {{ formatCount(summary.system_vs_teacher.system_low_teacher_no) }}
            </div>
          </div>
        </div>
      </div>

      <div class="panel-card panel-wide">
        <div class="panel-title">复核趋势</div>
        <div v-if="trendBars.length" class="trend-wrap">
          <div class="trend-chart">
            <div v-for="item in trendBars" :key="item.date" class="trend-column">
              <div class="trend-stack">
                <div class="trend-bar trend-bar-total" :style="{ height: item.totalPercent + '%' }" />
                <div class="trend-bar trend-bar-true" :style="{ height: item.truePercent + '%' }" />
              </div>
              <div class="trend-value">{{ item.confirmed_count }}</div>
            </div>
          </div>
          <div class="trend-axis">
            <span v-for="item in trendBars.slice(-7)" :key="item.date">{{ formatDateLabel(item.date) }}</span>
          </div>
        </div>
        <div v-else class="empty-text">暂无复核趋势数据</div>
      </div>

      <div class="panel-card panel-wide">
        <div class="panel-title">场景下钻</div>
        <el-table :data="sceneBreakdown" size="small" border stripe empty-text="暂无场景评估数据">
          <el-table-column prop="scene" label="场景" min-width="140">
            <template #default="{ row }">
              {{ sceneLabels[row.scene] || row.scene }}
            </template>
          </el-table-column>
          <el-table-column prop="review_count" label="复核数" width="90" />
          <el-table-column prop="true_risk_count" label="真风险" width="90" />
          <el-table-column prop="false_alarm_count" label="误报" width="90" />
          <el-table-column prop="unresolved_count" label="未闭环" width="90" />
          <el-table-column label="一致率" width="100">
            <template #default="{ row }">
              {{ formatPercent(row.agreement_rate) }}
            </template>
          </el-table-column>
          <el-table-column label="老师信心" width="100">
            <template #default="{ row }">
              {{ formatConfidence(row.avg_teacher_confidence) }}
            </template>
          </el-table-column>
          <el-table-column label="严重度分布" min-width="180">
            <template #default="{ row }">
              低 {{ row.severity_distribution.low || 0 }}
              / 中 {{ row.severity_distribution.medium || 0 }}
              / 高 {{ row.severity_distribution.high || 0 }}
            </template>
          </el-table-column>
          <el-table-column label="规则影响" min-width="220">
            <template #default="{ row }">
              缺口 {{ row.rule_impact?.data_gap_record_count || 0 }}
              / 保护 {{ row.rule_impact?.protective_record_count || 0 }}
              / 衰减 {{ row.rule_impact?.attenuated_record_count || 0 }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="panel-card panel-wide">
        <div class="panel-title">最近复核记录</div>
        <el-table :data="recentReviews" size="small" border stripe empty-text="暂无复核记录">
          <el-table-column prop="student_name" label="学生" min-width="120" />
          <el-table-column prop="class_name" label="班级" min-width="120" />
          <el-table-column label="场景" min-width="120">
            <template #default="{ row }">
              {{ sceneLabels[row.scene] || row.scene }}
            </template>
          </el-table-column>
          <el-table-column label="老师判断" width="110">
            <template #default="{ row }">
              {{ riskTruthLabel(row.is_true_risk) }}
            </template>
          </el-table-column>
          <el-table-column label="系统等级" width="100">
            <template #default="{ row }">
              {{ systemLevelLabel(row.system_level) }}
            </template>
          </el-table-column>
          <el-table-column label="处理状态" width="100">
            <template #default="{ row }">
              {{ resolutionLabels[row.resolution_status] || row.resolution_status }}
            </template>
          </el-table-column>
          <el-table-column label="老师备注" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.teacher_notes || '—' }}
            </template>
          </el-table-column>
          <el-table-column prop="confirmed_at" label="确认时间" min-width="170" />
          <el-table-column label="规则标签" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              {{ buildImpactText(row) }}
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <div class="insight-card" :class="{ warning: hasQualityRisk }">
      <div class="insight-title">评估提示</div>
      <div class="insight-body">
        <template v-if="hasQualityRisk">
          <div v-if="summary.reviewed_ratio < 0.3">当前复核覆盖率偏低，建议先推动老师对高风险记录做结构化确认。</div>
          <div v-if="summary.agreement_rate < 0.6">系统与老师一致率偏低，建议优先检查规则权重、文本极性和时间衰减。</div>
          <div v-if="summary.false_alarm_count > summary.true_risk_count">当前误报数量高于老师确认真风险数量，建议优先优化误报控制。</div>
        </template>
        <template v-else>
          当前复核覆盖率与一致率整体可用，已经可以作为下一轮规则调优的基础视图。
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { getClassList } from '@/api/class_'
import {
  getStudentCareEvaluationDetail,
  exportStudentCareEvaluationSummary,
  getStudentCareEvaluationSummary
} from '@/api/studentCare'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.role === 'admin')

const loading = ref(false)
const classOptions = ref([])
const classId = ref('')
const dateRange = ref([formatDate(daysAgo(30)), formatDate(new Date())])

const summary = ref({
  total_records: 0,
  confirmed_reviews: 0,
  reviewed_ratio: 0,
  true_risk_count: 0,
  false_alarm_count: 0,
  unresolved_count: 0,
  agreement_rate: 0,
  avg_teacher_confidence: 0,
  scene_distribution: {},
  severity_distribution: { low: 0, medium: 0, high: 0, unknown: 0 },
  resolution_distribution: { pending: 0, in_progress: 0, resolved: 0, false_alarm: 0 },
  rule_impact: {
    data_gap_record_count: 0,
    protective_record_count: 0,
    attenuated_record_count: 0,
    false_alarm_with_data_gap: 0,
    false_alarm_with_protective: 0,
    teacher_confirmed_with_data_gap: 0,
    teacher_confirmed_with_attenuated: 0
  },
  system_vs_teacher: {
    aligned: 0,
    misaligned: 0,
    system_positive_teacher_yes: 0,
    system_positive_teacher_no: 0,
    system_low_teacher_yes: 0,
    system_low_teacher_no: 0
  },
  trend: []
})
const sceneBreakdown = ref([])
const recentReviews = ref([])

const sceneLabels = {
  social_isolation: '社交孤立',
  emotion: '情绪状态',
  safety: '校园安全',
  family: '家庭支持',
  study: '学业压力',
  behavior: '行为稳定',
  other: '其他'
}

const severityLabels = {
  low: '低',
  medium: '中',
  high: '高',
  unknown: '未标注'
}

const resolutionLabels = {
  pending: '待处理',
  in_progress: '处理中',
  resolved: '已缓解',
  false_alarm: '误报'
}

const sceneBars = computed(() => buildBars(summary.value.scene_distribution, sceneLabels))
const severityBars = computed(() => buildBars(summary.value.severity_distribution, severityLabels))
const resolutionBars = computed(() =>
  buildBars(summary.value.resolution_distribution, resolutionLabels).map((item) => ({
    ...item,
    className: resolutionClassName(item.key)
  }))
)

const trendBars = computed(() => {
  const rows = summary.value.trend || []
  if (!rows.length) return []
  const max = Math.max(...rows.map((item) => item.confirmed_count || 0), 1)
  return rows.map((item) => ({
    ...item,
    totalPercent: Math.round(((item.confirmed_count || 0) / max) * 100),
    truePercent: Math.round(((item.true_risk_count || 0) / max) * 100)
  }))
})

const hasQualityRisk = computed(() => {
  return (
    Number(summary.value.reviewed_ratio || 0) < 0.3 ||
    Number(summary.value.agreement_rate || 0) < 0.6 ||
    Number(summary.value.false_alarm_count || 0) > Number(summary.value.true_risk_count || 0)
  )
})

function buildParams() {
  const [start, end] = dateRange.value || []
  return {
    start_date: start || undefined,
    end_date: end || undefined,
    class_id: isAdmin.value ? classId.value || undefined : undefined
  }
}

function buildBars(source = {}, labels = {}) {
  const entries = Object.entries(source || {}).filter(([, count]) => Number(count) > 0)
  const max = Math.max(...entries.map(([, count]) => Number(count)), 1)
  return entries
    .map(([key, count]) => ({
      key,
      label: labels[key] || key,
      count: Number(count) || 0,
      percent: Math.round(((Number(count) || 0) / max) * 100)
    }))
    .sort((a, b) => b.count - a.count)
}

function resolutionClassName(key) {
  if (key === 'resolved') return 'bar-fill-green'
  if (key === 'false_alarm') return 'bar-fill-amber'
  if (key === 'in_progress') return 'bar-fill-orange'
  return 'bar-fill-slate'
}

async function fetchClassOptions() {
  if (!isAdmin.value) return
  try {
    const res = await getClassList({ page: 1, page_size: 200 })
    classOptions.value = (res.list || []).map((item) => ({
      value: item.id,
      label: item.name
    }))
  } catch (error) {
    console.error('获取班级列表失败', error)
  }
}

async function fetchSummary() {
  loading.value = true
  try {
    const [summaryRes, detailRes] = await Promise.all([
      getStudentCareEvaluationSummary(buildParams()),
      getStudentCareEvaluationDetail(buildParams())
    ])
    summary.value = summaryRes || summary.value
    sceneBreakdown.value = detailRes?.scene_breakdown || []
    recentReviews.value = detailRes?.recent_reviews || []
  } catch (error) {
    console.error('获取研判评估失败', error)
  } finally {
    loading.value = false
  }
}

async function exportSummary() {
  try {
    const blob = await exportStudentCareEvaluationSummary(buildParams())
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'student-care-evaluation-summary.csv'
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

function formatPercent(value) {
  const num = Number(value) || 0
  return `${Math.round(num * 100)}%`
}

function formatCount(value) {
  if (!value) return '0'
  return Number(value).toLocaleString()
}

function formatConfidence(value) {
  const num = Number(value) || 0
  return num ? num.toFixed(1) : '0.0'
}

function formatDateLabel(value) {
  if (!value) return '--'
  return value.slice(5)
}

function riskTruthLabel(value) {
  if (value === 'yes') return '属实'
  if (value === 'no') return '误报'
  return '未标注'
}

function systemLevelLabel(value) {
  if (value === 'high') return '高风险'
  if (value === 'medium') return '中风险'
  if (value === 'attention') return '关注'
  return '低风险'
}

function buildImpactText(row) {
  const tags = []
  if (row.has_data_gap) {
    const missing = (row.missing_sources || []).length ? `：${(row.missing_sources || []).join('、')}` : ''
    tags.push(`数据缺口${missing}`)
  }
  if (row.has_protective) {
    tags.push('保护性证据')
  }
  if (row.has_attenuated) {
    tags.push('历史信号已衰减')
  }
  return tags.length ? tags.join(' / ') : '无明显规则影响标签'
}

function daysAgo(days) {
  const date = new Date()
  date.setDate(date.getDate() - days)
  return date
}

function formatDate(value) {
  const date = value instanceof Date ? value : new Date(value)
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

onMounted(() => {
  fetchClassOptions()
  fetchSummary()
})
</script>

<style scoped lang="scss">
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #172033;
}

.page-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: #607086;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 14px 16px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(243, 247, 255, 0.95));
  border: 1px solid rgba(125, 149, 179, 0.18);
  box-shadow: 0 14px 28px rgba(16, 24, 40, 0.05);
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 12px;
  color: #607086;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
}

.stats-card,
.panel-card,
.insight-card {
  border-radius: 20px;
  border: 1px solid rgba(125, 149, 179, 0.16);
  background: #fff;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.06);
}

.stats-card {
  padding: 16px 18px;
}

.stats-label {
  font-size: 12px;
  color: #607086;
}

.stats-value {
  margin-top: 8px;
  font-size: 26px;
  font-weight: 700;
  color: #172033;
}

.stats-meta {
  margin-top: 6px;
  font-size: 12px;
  color: #7a8799;
}

.accent-danger {
  color: #d14343;
}

.accent-warn {
  color: #d68a22;
}

.accent-primary {
  color: #2459d1;
}

.accent-success {
  color: #169c66;
}

.panel-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.panel-card {
  padding: 18px 20px;
}

.panel-wide {
  grid-column: span 2;
}

.panel-title {
  margin-bottom: 14px;
  font-size: 15px;
  font-weight: 700;
  color: #172033;
}

.bar-list {
  display: grid;
  gap: 12px;
}

.bar-item {
  display: grid;
  gap: 6px;
}

.bar-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  color: #49566a;
}

.bar-track {
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: #edf2f8;
}

.bar-fill {
  height: 100%;
  border-radius: inherit;
}

.bar-fill-blue {
  background: linear-gradient(90deg, #4c7ff7, #2756c7);
}

.bar-fill-green {
  background: linear-gradient(90deg, #38c793, #169c66);
}

.bar-fill-amber {
  background: linear-gradient(90deg, #f2c14e, #d68a22);
}

.bar-fill-orange {
  background: linear-gradient(90deg, #fb923c, #ea580c);
}

.bar-fill-slate {
  background: linear-gradient(90deg, #94a3b8, #64748b);
}

.pill-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.pill-card {
  padding: 14px 12px;
  border-radius: 16px;
  background: linear-gradient(180deg, #f7faff, #eef4fb);
  text-align: center;
}

.pill-label {
  font-size: 12px;
  color: #607086;
}

.pill-value {
  margin-top: 8px;
  font-size: 24px;
  font-weight: 700;
  color: #172033;
}

.compare-grid {
  display: grid;
  gap: 12px;
}

.impact-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.impact-card {
  padding: 14px 16px;
  border-radius: 16px;
  background: linear-gradient(180deg, #f7faff, #eef4fb);
  border: 1px solid rgba(125, 149, 179, 0.14);
}

.impact-label {
  font-size: 12px;
  color: #607086;
}

.impact-value {
  margin-top: 8px;
  font-size: 24px;
  font-weight: 700;
  color: #172033;
}

.impact-meta {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.6;
  color: #7a8799;
}

.compare-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #f8fbff;
}

.compare-label {
  font-size: 13px;
  color: #49566a;
}

.compare-value {
  min-width: 44px;
  text-align: right;
  font-size: 22px;
  font-weight: 700;
  color: #172033;
}

.trend-wrap {
  display: grid;
  gap: 10px;
}

.trend-chart {
  display: grid;
  grid-auto-flow: column;
  align-items: end;
  gap: 8px;
  min-height: 180px;
}

.trend-column {
  display: flex;
  flex-direction: column;
  justify-content: end;
  gap: 6px;
  min-width: 18px;
}

.trend-stack {
  position: relative;
  height: 140px;
  display: flex;
  align-items: end;
  justify-content: center;
}

.trend-bar {
  position: absolute;
  bottom: 0;
  width: 14px;
  border-radius: 10px 10px 0 0;
}

.trend-bar-total {
  background: linear-gradient(180deg, #bfd4ff, #5a84ef);
}

.trend-bar-true {
  width: 8px;
  background: linear-gradient(180deg, #ffb26c, #d14343);
}

.trend-value {
  font-size: 11px;
  color: #607086;
  text-align: center;
}

.trend-axis {
  display: grid;
  grid-auto-flow: column;
  gap: 8px;
  font-size: 11px;
  color: #98a4b5;
}

.empty-text {
  padding: 12px 0;
  font-size: 12px;
  color: #98a4b5;
}

.insight-card {
  margin-top: 16px;
  padding: 16px 18px;
  background: linear-gradient(135deg, #f7fbff, #edf4ff);
}

.insight-card.warning {
  background: linear-gradient(135deg, rgba(255, 245, 230, 0.95), rgba(255, 236, 214, 0.92));
  border-color: rgba(214, 138, 34, 0.22);
}

.insight-title {
  font-size: 14px;
  font-weight: 700;
  color: #172033;
}

.insight-body {
  margin-top: 8px;
  display: grid;
  gap: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: #49566a;
}

@media (max-width: 960px) {
  .page-header,
  .filter-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .panel-grid {
    grid-template-columns: 1fr;
  }

  .panel-wide {
    grid-column: span 1;
  }

  .pill-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .impact-grid {
    grid-template-columns: 1fr;
  }
}
</style>
