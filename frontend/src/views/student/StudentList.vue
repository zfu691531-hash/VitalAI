<template>
  <div class="page-container">
    <SearchBar :filters="filterOptions" @search="handleSearch" @reset="handleReset" />

    <div class="agent-stats">
      <div class="stats-card">
        <div class="stats-title">研判总量</div>
        <div class="stats-value">{{ agentStats.total }}</div>
      </div>
      <div class="stats-card">
        <div class="stats-title">兜底率</div>
        <div class="stats-value">{{ Math.round((agentStats.fallback_rate || 0) * 100) }}%</div>
      </div>
      <div class="stats-card">
        <div class="stats-title">风险分布</div>
        <div class="stats-meta">
          <span>低 {{ agentStats.risk_distribution.low }}</span>
          <span>关注 {{ agentStats.risk_distribution.attention }}</span>
          <span>中 {{ agentStats.risk_distribution.medium }}</span>
          <span>高 {{ agentStats.risk_distribution.high }}</span>
        </div>
      </div>
      <div class="stats-card">
        <div class="stats-title">模型分布</div>
        <div class="stats-meta">
          <span v-for="(count, name) in agentStats.model_distribution" :key="name">
            {{ name }} {{ count }}
          </span>
        </div>
      </div>
      <div class="stats-card">
        <div class="stats-title">近五日趋势</div>
        <div class="stats-meta">
          <span v-for="item in agentStats.daily_trend.slice(-5)" :key="item.date">
            {{ item.date }} {{ item.count }}
          </span>
        </div>
      </div>
      <div class="stats-refresh">
        <el-button size="small" :loading="agentStatsLoading" @click="fetchAgentStats">
          刷新统计
        </el-button>
      </div>
    </div>

    <div class="action-bar">
      <div class="left-actions">
        <el-button type="primary" @click="handleAdd" v-permission="['teacher', 'admin']">
          <el-icon><Plus /></el-icon>新增学生
        </el-button>
        <FileUpload
          button-text="批量导入"
          :template-action="handleDownloadTemplate"
          @success="handleImport"
          v-permission="['teacher', 'admin']"
        />
        <ExportButton :formats="['excel']" @export="handleExport" />
      </div>
      <div class="right-actions">
        <el-button
          type="danger"
          :disabled="selectedIds.length === 0"
          @click="handleBatchDelete"
          v-permission="['admin']"
        >
          <el-icon><Delete /></el-icon>批量删除
        </el-button>
      </div>
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="50" />
      <el-table-column prop="student_no" label="学号" width="120" />
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="gender" label="性别" width="80">
        <template #default="{ row }">
          {{ row.gender === 'male' ? '男' : '女' }}
        </template>
      </el-table-column>
      <el-table-column prop="age" label="年龄" width="80" />
      <el-table-column prop="grade" label="年级" width="90" />
      <el-table-column prop="class_name" label="班级" width="120" />
      <el-table-column prop="contact" label="联系方式" width="130" />
      <el-table-column prop="specialty" label="特长" min-width="120" show-overflow-tooltip />
      <el-table-column prop="tags" label="标签" width="180">
        <template #default="{ row }">
          <template v-if="row.tags">
            <el-tag
              v-for="tag in parseTags(row.tags)"
              :key="tag"
              :type="getTagType(tag)"
              size="small"
              class="tag-item"
            >
              {{ tag }}
            </el-tag>
          </template>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="230" fixed="right">
        <template #default="{ row }">
          <el-button type="warning" link @click="handleCare(row)" v-permission="['teacher']">
            关怀画像
          </el-button>
          <el-button type="primary" link @click="handleEdit(row)" v-permission="['teacher', 'admin']">
            编辑
          </el-button>
          <el-button type="danger" link @click="handleDelete(row)" v-permission="['admin']">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <Pagination
      :total="total"
      :page="queryParams.page"
      :page-size="queryParams.page_size"
      @change="handlePageChange"
    />

    <StudentForm
      v-model:visible="formVisible"
      :student="currentStudent"
      @success="handleFormSuccess"
    />

    <StudentCareDrawer
      v-model:visible="careVisible"
      :student="careStudent"
      :profile="careProfile"
      :signals="careSignals"
      :actions="careActions"
      :data-quality="careDataQuality"
      :isolation-analysis="careIsolationAnalysis"
      :isolation-loading="careIsolationLoading"
      :loading="careLoading"
      :agent-result="careAgentResult"
      :agent-loading="careAgentLoading"
      :agent-history="careAgentHistory"
      :agent-history-total="careAgentHistoryTotal"
      :agent-history-page="careAgentHistoryPage"
      :agent-history-loading="careAgentHistoryLoading"
      :graph-health="careGraphHealth"
      :graph-loading="careGraphLoading"
      :graph-view="careGraphView"
      :graph-view-loading="careGraphViewLoading"
      :graph-syncing="careGraphSyncing"
      :graph-last-sync="careGraphLastSync"
      :graph-auto-sync="careGraphAutoSync"
      @recalculate="handleCareRecalculate"
      @agent-eval="handleCareAgentEval"
      @agent-review="handleCareAgentReview"
      @agent-history-page-change="fetchCareAgentHistory"
      @graph-sync="handleCareGraphSync"
      @data-changed="handleCareDataChanged"
    />

    <ConfirmDialog
      v-model:visible="deleteVisible"
      title="删除确认"
      :message="deleteMessage"
      confirm-type="danger"
      confirm-text="删除"
      :loading="deleteLoading"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Plus } from '@element-plus/icons-vue'
import SearchBar from '@/components/common/SearchBar.vue'
import Pagination from '@/components/common/Pagination.vue'
import FileUpload from '@/components/common/FileUpload.vue'
import ExportButton from '@/components/common/ExportButton.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import StudentForm from './StudentForm.vue'
import StudentCareDrawer from './StudentCareDrawer.vue'
import {
  batchDeleteStudents,
  deleteStudent,
  downloadStudentTemplate,
  exportStudents,
  getStudentList,
  importStudents
} from '@/api/student'
import { getClassList } from '@/api/class_'
import {
  confirmStudentCareAgentReview,
  getStudentCareAgentEval,
  getStudentCareAgentHistory,
  getStudentCareAgentStats,
  getStudentCareGraphHealth,
  getStudentCareGraphView,
  getStudentCareIsolationBn,
  getStudentCareProfile,
  syncStudentCareGraph
} from '@/api/studentCare'

const filterOptions = ref([
  { key: 'class_id', label: '班级', options: [] },
  {
    key: 'gender',
    label: '性别',
    options: [
      { value: 'male', label: '男' },
      { value: 'female', label: '女' }
    ]
  },
  {
    key: 'tag',
    label: '标签',
    options: [
      { value: '关怀', label: '关怀' },
      { value: '违纪', label: '违纪' }
    ]
  }
])

const queryParams = reactive({
  page: 1,
  page_size: 10,
  keyword: '',
  class_id: '',
  gender: '',
  tag: ''
})

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const selectedIds = ref([])

const formVisible = ref(false)
const currentStudent = ref(null)

const careVisible = ref(false)
const careLoading = ref(false)
const careStudent = ref(null)
const careProfile = ref(null)
const careSignals = ref([])
const careActions = ref([])
const careDataQuality = ref(null)
const careIsolationAnalysis = ref(null)
const careIsolationLoading = ref(false)
const careAgentResult = ref(null)
const careAgentLoading = ref(false)
const careAgentHistory = ref([])
const careAgentHistoryTotal = ref(0)
const careAgentHistoryPage = ref(1)
const careAgentHistoryLoading = ref(false)
const careGraphHealth = ref(null)
const careGraphLoading = ref(false)
const careGraphView = ref(null)
const careGraphViewLoading = ref(false)
const careGraphSyncing = ref(false)
const careGraphLastSync = ref(null)
const careGraphAutoSync = ref({
  status: 'idle',
  message: '',
  synced_at: ''
})

const deleteVisible = ref(false)
const deleteMessage = ref('')
const deleteLoading = ref(false)
const deleteTarget = ref(null)

const agentStatsLoading = ref(false)
const agentStats = ref({
  total: 0,
  fallback_rate: 0,
  risk_distribution: { low: 0, attention: 0, medium: 0, high: 0 },
  model_distribution: {},
  daily_trend: []
})

onMounted(() => {
  fetchList()
  fetchClassOptions()
  fetchAgentStats()
})

async function fetchClassOptions() {
  try {
    const res = await getClassList({ page: 1, page_size: 100 })
    filterOptions.value[0].options = (res.list || []).map((item) => ({
      value: item.id,
      label: item.name
    }))
  } catch (error) {
    console.error('获取班级列表失败', error)
  }
}

async function fetchList() {
  loading.value = true
  try {
    const res = await getStudentList(queryParams)
    tableData.value = res.list || []
    total.value = res.total || 0
  } catch (error) {
    console.error('获取学生列表失败', error)
  } finally {
    loading.value = false
  }
}

async function fetchAgentStats() {
  agentStatsLoading.value = true
  try {
    const res = await getStudentCareAgentStats()
    agentStats.value = res || agentStats.value
  } catch (error) {
    console.error('获取研判统计失败', error)
  } finally {
    agentStatsLoading.value = false
  }
}

function handleSearch(params) {
  Object.assign(queryParams, params, { page: 1 })
  fetchList()
}

function handleReset() {
  Object.assign(queryParams, {
    page: 1,
    page_size: 10,
    keyword: '',
    class_id: '',
    gender: '',
    tag: ''
  })
  fetchList()
}

function handlePageChange({ page, pageSize }) {
  queryParams.page = page
  queryParams.page_size = pageSize
  fetchList()
}

function handleSelectionChange(selection) {
  selectedIds.value = selection.map((item) => item.id)
}

function handleAdd() {
  currentStudent.value = null
  formVisible.value = true
}

function handleEdit(row) {
  currentStudent.value = { ...row }
  formVisible.value = true
}

function handleFormSuccess() {
  formVisible.value = false
  fetchList()
}

async function handleCare(row) {
  careVisible.value = true
  careStudent.value = { ...row }
  careLoading.value = true
  careGraphHealth.value = null
  careGraphView.value = null
  careGraphLastSync.value = null
    careGraphAutoSync.value = { status: 'idle', message: '', synced_at: '' }
    careProfile.value = null
    careSignals.value = []
    careActions.value = []
    careDataQuality.value = null
    careIsolationAnalysis.value = null
    careAgentResult.value = null
    careAgentHistory.value = []
    careAgentHistoryTotal.value = 0
    careAgentHistoryPage.value = 1
    try {
      const res = await getStudentCareProfile(row.id)
      careStudent.value = res.student || careStudent.value
      careProfile.value = res.profile || null
      careSignals.value = res.signals || []
      careActions.value = res.actions || []
      careDataQuality.value = res.data_quality || null
      await Promise.all([
        fetchCareIsolationAnalysis(row.id),
        fetchCareAgentHistory(1),
        fetchCareGraphHealth(),
        fetchCareGraphView(row.id)
      ])
    } catch (error) {
      careVisible.value = false
      console.error('获取学生关怀画像失败', error)
    } finally {
      careLoading.value = false
    }
  }

async function handleCareRecalculate(options = {}) {
  if (!careStudent.value?.id) return
  const { silent = false } = options
  careLoading.value = true
  try {
    const res = await getStudentCareProfile(careStudent.value.id)
    careStudent.value = res.student || careStudent.value
    careProfile.value = res.profile || null
    careSignals.value = res.signals || []
    careActions.value = res.actions || []
    careDataQuality.value = res.data_quality || null
    await fetchCareIsolationAnalysis(careStudent.value.id)
    if (!silent) {
      ElMessage.success('已重新计算')
    }
  } catch (error) {
    console.error('重新计算失败', error)
  } finally {
    careLoading.value = false
  }
}

async function fetchCareIsolationAnalysis(studentId = careStudent.value?.id) {
  if (!studentId) return
  careIsolationLoading.value = true
  try {
    const res = await getStudentCareIsolationBn(studentId)
    careIsolationAnalysis.value = res || null
  } catch (error) {
    careIsolationAnalysis.value = null
    console.error('获取孤立预警推理失败', error)
  } finally {
    careIsolationLoading.value = false
  }
}

async function fetchCareGraphHealth() {
  careGraphLoading.value = true
  try {
    const res = await getStudentCareGraphHealth()
    careGraphHealth.value = res || null
  } catch (error) {
    careGraphHealth.value = {
      enabled: null,
      connected: false,
      error: true,
      reason: '获取关系图谱状态失败'
    }
    console.error('获取关系图谱状态失败', error)
  } finally {
    careGraphLoading.value = false
  }
}

async function fetchCareGraphView(studentId = careStudent.value?.id) {
  if (!studentId) return
  careGraphViewLoading.value = true
  try {
    const res = await getStudentCareGraphView(studentId)
    careGraphView.value = res || null
  } catch (error) {
    careGraphView.value = null
    console.error('获取关系图谱视图失败', error)
  } finally {
    careGraphViewLoading.value = false
  }
}

async function handleCareGraphSync() {
  if (!careStudent.value?.id) return
  careGraphSyncing.value = true
  try {
    const res = await syncStudentCareGraph(careStudent.value.id)
    if (res?.enabled && res?.synced) {
      careGraphLastSync.value = {
        ...(res || {}),
        synced_at: new Date().toLocaleString('zh-CN', { hour12: false })
      }
      ElMessage.success('关系图谱已完成同步')
      await Promise.all([
        handleCareRecalculate(),
        fetchCareGraphHealth(),
        fetchCareGraphView(careStudent.value.id)
      ])
    } else {
      careGraphLastSync.value = null
      await Promise.all([
        fetchCareGraphHealth(),
        fetchCareGraphView(careStudent.value.id)
      ])
      ElMessage.warning('关系图谱层当前未启用，本次未实际执行同步')
    }
  } catch (error) {
    console.error('关系图谱同步失败', error)
  } finally {
    careGraphSyncing.value = false
  }
}

async function handleCareDataChanged() {
  if (!careStudent.value?.id) return
  careGraphAutoSync.value = {
    status: 'syncing',
    message: '关怀数据已变更，系统正在自动刷新画像与关系图谱。',
    synced_at: ''
  }
  careLoading.value = true
  try {
    await Promise.all([
      handleCareRecalculate({ silent: true }),
      fetchCareGraphHealth(),
      fetchCareGraphView(careStudent.value.id)
    ])
    careGraphAutoSync.value = {
      status: 'success',
      message: '系统已根据最新关怀数据自动刷新画像与关系图谱。',
      synced_at: new Date().toLocaleString('zh-CN', { hour12: false })
    }
    ElMessage.success('关怀画像与关系图谱已自动同步')
  } catch (error) {
    console.error('关怀数据联动刷新失败', error)
    careGraphAutoSync.value = {
      status: 'error',
      message: '关怀数据已更新，但自动刷新图谱失败，建议稍后重试或手动同步图谱。',
      synced_at: ''
    }
  } finally {
    careLoading.value = false
  }
}

async function handleCareAgentEval() {
  if (!careStudent.value?.id) return
  careAgentLoading.value = true
  try {
    const res = await getStudentCareAgentEval(careStudent.value.id)
    careAgentResult.value = res || null
    ElMessage.success('研判已生成')
    fetchCareAgentHistory(1)
  } catch (error) {
    console.error('智能研判失败', error)
  } finally {
    careAgentLoading.value = false
  }
}

async function handleCareAgentReview(payload) {
  if (!payload?.recordId) return
  try {
    const res = await confirmStudentCareAgentReview(payload.recordId, {
      reviewed_result: payload.reviewedResult,
      teacher_notes: payload.teacherNotes,
      resolution_status: payload.resolutionStatus,
      review_labels: payload.reviewLabels
    })
    careAgentResult.value = {
      ...(careAgentResult.value || {}),
      review_status: res.review_status,
      reviewed_result: res.reviewed_result,
      review_labels: res.review_labels,
      teacher_notes: res.teacher_notes,
      resolution_status: res.resolution_status,
      confirmed_at: res.confirmed_at,
      confirmed_by: res.confirmed_by
    }
    ElMessage.success('研判确认已保存')
    fetchCareAgentHistory(1)
  } catch (error) {
    console.error('确认研判失败', error)
  }
}

async function fetchCareAgentHistory(page) {
  if (!careStudent.value?.id) return
  careAgentHistoryLoading.value = true
  try {
    const res = await getStudentCareAgentHistory(careStudent.value.id, {
      page,
      page_size: 5
    })
    careAgentHistory.value = res.list || []
    careAgentHistoryTotal.value = res.total || 0
    careAgentHistoryPage.value = page
  } catch (error) {
    console.error('获取研判历史失败', error)
  } finally {
    careAgentHistoryLoading.value = false
  }
}

function handleDelete(row) {
  deleteTarget.value = { type: 'single', id: row.id }
  deleteMessage.value = `确定删除学生“${row.name}”吗？删除后不可恢复。`
  deleteVisible.value = true
}

function handleBatchDelete() {
  if (!selectedIds.value.length) return
  deleteTarget.value = { type: 'batch', ids: selectedIds.value }
  deleteMessage.value = `确定删除选中的 ${selectedIds.value.length} 名学生吗？删除后不可恢复。`
  deleteVisible.value = true
}

async function confirmDelete() {
  deleteLoading.value = true
  try {
    if (deleteTarget.value.type === 'single') {
      await deleteStudent(deleteTarget.value.id)
    } else {
      await batchDeleteStudents(deleteTarget.value.ids)
    }
    ElMessage.success('删除成功')
    deleteVisible.value = false
    fetchList()
  } catch (error) {
    console.error('删除失败', error)
  } finally {
    deleteLoading.value = false
  }
}

async function handleImport(file) {
  try {
    const res = await importStudents(file)
    ElMessage.success(`导入成功 ${res.success_count} 条`)
    fetchList()
  } catch (error) {
    console.error('导入失败', error)
  }
}

async function handleExport() {
  try {
    const res = await exportStudents(queryParams)
    downloadFile(res, '学生列表.xlsx')
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('导出失败', error)
  }
}

async function handleDownloadTemplate() {
  try {
    const res = await downloadStudentTemplate()
    downloadFile(res, '学生导入模板.xlsx')
  } catch (error) {
    console.error('下载模板失败', error)
  }
}

function downloadFile(res, filename) {
  const blob = new Blob([res], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  window.URL.revokeObjectURL(url)
}

function parseTags(tags) {
  if (!tags) return []
  return tags
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function getTagType(tag) {
  if (tag.includes('关怀')) return 'warning'
  if (tag.includes('违纪') || tag.includes('迟到')) return 'danger'
  return 'info'
}
</script>

<style scoped lang="scss">
.action-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;

  .left-actions,
  .right-actions {
    display: flex;
    gap: 12px;
  }
}

.agent-stats {
  margin: 12px 0 16px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.stats-card {
  padding: 12px 14px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.16);
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
}

.stats-title {
  font-size: 12px;
  color: #64748b;
}

.stats-value {
  margin-top: 6px;
  font-size: 22px;
  font-weight: 700;
  color: #1f2937;
}

.stats-meta {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #475569;
}

.stats-refresh {
  display: flex;
  align-items: flex-end;
}

.tag-item {
  margin-right: 4px;
  margin-bottom: 4px;

  &:last-child {
    margin-right: 0;
  }
}
</style>

