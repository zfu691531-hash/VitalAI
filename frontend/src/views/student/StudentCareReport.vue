<template>
  <div class="page-container">
    <div class="report-header">
      <div>
        <div class="report-title">关怀研判报表</div>
        <div class="report-subtitle">面向班主任与管理员的研判质量与风险概览</div>
      </div>
      <div class="header-actions">
        <el-button size="small" :loading="loading" @click="fetchStats">刷新</el-button>
        <el-button size="small" type="primary" @click="exportStats">导出</el-button>
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
      <el-button size="small" type="success" @click="applyFilters">应用筛选</el-button>
    </div>

    <div class="stats-grid">
      <div class="stats-card">
        <div class="stats-label">研判总量</div>
        <div class="stats-value">{{ formatCount(stats.total) }}</div>
      </div>
      <div class="stats-card">
        <div class="stats-label">兜底率</div>
        <div class="stats-value accent-warn">{{ formatPercent(stats.fallback_rate) }}</div>
      </div>
      <div class="stats-card">
        <div class="stats-label">高风险占比</div>
        <div class="stats-value accent-danger">{{ formatPercent(highRiskRatio) }}</div>
      </div>
      <div class="stats-card">
        <div class="stats-label">模型数量</div>
        <div class="stats-value">{{ formatCount(Object.keys(stats.model_distribution || {}).length) }}</div>
      </div>
    </div>

    <div class="report-grid">
      <div class="panel-card">
        <div class="panel-title">风险等级分布</div>
        <div class="donut-wrap" v-if="stats.total">
          <svg class="donut" viewBox="0 0 120 120">
            <circle class="donut-track" cx="60" cy="60" r="44" />
            <circle
              v-for="slice in donutSlices"
              :key="slice.key"
              class="donut-slice"
              cx="60"
              cy="60"
              r="44"
              :style="{
                stroke: slice.color,
                strokeDasharray: `${slice.length} ${donutTotal}`,
                strokeDashoffset: `${slice.offset}`
              }"
            />
          </svg>
          <div class="donut-legend">
            <div v-for="item in riskBars" :key="item.key" class="legend-row">
              <span class="legend-dot" :style="{ background: item.color }" />
              <span class="legend-label">{{ item.label }}</span>
              <span class="legend-value">{{ formatCount(item.count) }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-text">暂无风险分布数据</div>
      </div>

      <div class="panel-card">
        <div class="panel-title">模型分布</div>
        <div v-if="modelBars.length" class="model-bars">
          <div v-for="item in modelBars" :key="item.key" class="model-item">
            <div class="model-head">
              <span>{{ item.label }}</span>
              <span>{{ formatCount(item.count) }}</span>
            </div>
            <div class="model-track">
              <div class="model-fill" :style="{ width: item.percent + '%' }" />
            </div>
          </div>
        </div>
        <div v-else class="empty-text">暂无模型分布数据</div>
      </div>

      <div class="panel-card panel-wide">
        <div class="panel-title">近 30 天研判趋势</div>
        <div v-if="trendBars.length" class="sparkline">
          <div v-for="item in trendBars" :key="item.date" class="spark-bar">
            <div class="spark-fill" :style="{ height: item.percent + '%' }" />
            <span class="spark-label">{{ formatCount(item.count) }}</span>
          </div>
        </div>
        <div v-if="trendBars.length" class="spark-axis">
          <span v-for="item in trendBars.slice(-7)" :key="item.date">{{ formatDateLabel(item.date) }}</span>
        </div>
        <div v-else class="empty-text">暂无趋势数据</div>
      </div>
    </div>

    <div class="alert-card" :class="{ warning: showWarning }">
      <div class="alert-title">研判质量提示</div>
      <div class="alert-body">
        <template v-if="showWarning">
          <div v-if="stats.fallback_rate > 0.3">兜底率偏高，建议检查模型稳定性或补充数据来源。</div>
          <div v-if="highRiskRatio > 0.2">高风险占比偏高，建议关注班级或年级的异常波动。</div>
        </template>
        <template v-else>
          当前研判质量稳定，暂无明显异常提示。
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
import { exportStudentCareAgentStats, getStudentCareAgentStats } from '@/api/studentCare'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.role === 'admin')

const loading = ref(false)
const stats = ref({
  total: 0,
  fallback_rate: 0,
  risk_distribution: { low: 0, attention: 0, medium: 0, high: 0 },
  model_distribution: {},
  daily_trend: []
})

const classOptions = ref([])
const classId = ref('')

const dateRange = ref([formatDate(daysAgo(30)), formatDate(new Date())])

const highRiskRatio = computed(() => {
  const total = stats.value.total || 0
  if (!total) return 0
  return (stats.value.risk_distribution?.high || 0) / total
})

const showWarning = computed(() => stats.value.fallback_rate > 0.3 || highRiskRatio.value > 0.2)

const riskBars = computed(() => {
  const total = stats.value.total || 1
  const dist = stats.value.risk_distribution || {}
  const items = [
    { key: 'low', label: '低风险', color: '#22c55e' },
    { key: 'attention', label: '关注', color: '#facc15' },
    { key: 'medium', label: '中风险', color: '#fb923c' },
    { key: 'high', label: '高风险', color: '#ef4444' }
  ]
  return items.map((item) => ({
    ...item,
    count: dist[item.key] || 0,
    percent: Math.round(((dist[item.key] || 0) / total) * 100)
  }))
})

const donutTotal = 2 * Math.PI * 44

const donutSlices = computed(() => {
  const items = riskBars.value
  let offset = 0
  return items.map((item) => {
    const length = (item.percent / 100) * donutTotal
    const slice = {
      key: item.key,
      color: item.color,
      length,
      offset: -offset
    }
    offset += length
    return slice
  })
})

const modelBars = computed(() => {
  const dist = stats.value.model_distribution || {}
  const total = Object.values(dist).reduce((sum, value) => sum + value, 0) || 1
  return Object.entries(dist).map(([key, count]) => ({
    key,
    label: key,
    count,
    percent: Math.round((count / total) * 100)
  }))
})

const trendBars = computed(() => {
  const rows = stats.value.daily_trend || []
  if (!rows.length) return []
  const max = Math.max(...rows.map((item) => item.count)) || 1
  return rows.map((item) => ({
    date: item.date,
    count: item.count,
    percent: Math.round((item.count / max) * 100)
  }))
})

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

function buildParams() {
  const [start, end] = dateRange.value || []
  return {
    start_date: start || undefined,
    end_date: end || undefined,
    class_id: isAdmin.value ? classId.value || undefined : undefined
  }
}

async function fetchStats() {
  loading.value = true
  try {
    const res = await getStudentCareAgentStats(buildParams())
    stats.value = res || stats.value
  } catch (error) {
    console.error('获取研判统计失败', error)
  } finally {
    loading.value = false
  }
}

async function applyFilters() {
  await fetchStats()
}

async function exportStats() {
  try {
    const blob = await exportStudentCareAgentStats(buildParams())
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'student-care-report.csv'
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

function formatDateLabel(value) {
  if (!value) return '--'
  return value.slice(5)
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
  fetchStats()
})
</script>

<style scoped lang="scss">
.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.report-title {
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
}

.report-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 12px;
  color: #64748b;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.stats-card {
  padding: 14px 16px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.16);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.05);
}

.stats-label {
  font-size: 12px;
  color: #64748b;
}

.stats-value {
  margin-top: 6px;
  font-size: 22px;
  font-weight: 700;
  color: #111827;
}

.stats-value.accent-warn {
  color: #f59e0b;
}

.stats-value.accent-danger {
  color: #ef4444;
}

.report-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.panel-card {
  padding: 16px 18px;
  border-radius: 16px;
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.16);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

.panel-wide {
  grid-column: span 2;
}

.panel-title {
  font-size: 14px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 12px;
}

.donut-wrap {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 16px;
  align-items: center;
}

.donut {
  width: 120px;
  height: 120px;
}

.donut-track {
  fill: none;
  stroke: #eef2f7;
  stroke-width: 12;
}

.donut-slice {
  fill: none;
  stroke-width: 12;
  stroke-linecap: round;
  transform: rotate(-90deg);
  transform-origin: 60px 60px;
}

.donut-legend {
  display: grid;
  gap: 8px;
}

.legend-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #475569;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-label {
  flex: 1;
}

.legend-value {
  font-weight: 600;
  color: #1f2937;
}

.model-bars {
  display: grid;
  gap: 10px;
}

.model-item {
  display: grid;
  gap: 6px;
}

.model-head {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #475569;
}

.model-track {
  height: 8px;
  background: #eef2f7;
  border-radius: 999px;
  overflow: hidden;
}

.model-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #6366f1, #4f46e5);
}

.sparkline {
  display: grid;
  grid-auto-flow: column;
  align-items: end;
  gap: 6px;
  height: 120px;
  margin-bottom: 8px;
}

.spark-bar {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 4px;
  height: 100%;
}

.spark-fill {
  width: 100%;
  border-radius: 6px 6px 0 0;
  background: linear-gradient(180deg, #34d399, #10b981);
  min-height: 6px;
}

.spark-label {
  font-size: 10px;
  color: #64748b;
  text-align: center;
}

.spark-axis {
  display: grid;
  grid-auto-flow: column;
  gap: 6px;
  font-size: 10px;
  color: #94a3b8;
}

.empty-text {
  padding: 10px 0;
  font-size: 12px;
  color: #94a3b8;
}

.alert-card {
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: #f8fafc;
}

.alert-card.warning {
  border-color: rgba(251, 146, 60, 0.3);
  background: rgba(255, 237, 213, 0.55);
}

.alert-title {
  font-size: 13px;
  font-weight: 700;
  color: #1f2937;
}

.alert-body {
  margin-top: 6px;
  font-size: 12px;
  color: #475569;
  line-height: 1.6;
}

@media (max-width: 960px) {
  .report-grid {
    grid-template-columns: 1fr;
  }

  .panel-wide {
    grid-column: span 1;
  }

  .donut-wrap {
    grid-template-columns: 1fr;
  }

  .filter-bar {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
