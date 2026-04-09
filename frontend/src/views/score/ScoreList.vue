<template>
  <div class="page-container">
    <SearchBar :filters="filterOptions" @search="handleSearch" @reset="handleReset" />

    <div class="stats-bar">
      <el-card v-for="item in statsData" :key="item.subject" shadow="never" class="stats-card">
        <div class="stats-title">{{ item.subject }}</div>
        <div class="stats-row">平均分：{{ item.average }}</div>
        <div class="stats-row">最高分：{{ item.maximum }}</div>
        <div class="stats-row">最低分：{{ item.minimum }}</div>
      </el-card>
    </div>

    <div class="action-bar">
      <div class="left-actions">
        <el-button type="primary" @click="handleAdd" v-permission="['teacher', 'admin']">
          <el-icon><Plus /></el-icon>录入成绩
        </el-button>
        <FileUpload button-text="批量导入" :template-action="handleDownloadTemplate" @success="handleImport" />
        <ExportButton :formats="['excel']" @export="handleExport" />
      </div>
      <div class="right-actions">
        <el-button
          type="danger"
          :disabled="selectedIds.length === 0"
          v-permission="['admin']"
          @click="handleBatchDelete"
        >
          <el-icon><Delete /></el-icon>批量删除
        </el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="tableData" border stripe @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="50" />
      <el-table-column prop="student_name" label="学生" width="120" />
      <el-table-column prop="class_name" label="班级" width="140" />
      <el-table-column prop="exam_batch" label="考试批次" width="140" />
      <el-table-column prop="subject" label="科目" width="120" />
      <el-table-column prop="score" label="分数" width="100">
        <template #default="{ row }">
          <span :class="{ 'score-danger': Number(row.score) < 60 }">{{ row.score }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="170" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link v-permission="['teacher', 'admin']" @click="handleEdit(row)">
            编辑
          </el-button>
          <el-button type="danger" link v-permission="['teacher', 'admin']" @click="handleDelete(row)">
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

    <ScoreForm v-model:visible="formVisible" :score-data="currentScore" @success="fetchData" />

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
import ScoreForm from './ScoreForm.vue'
import {
  batchDeleteScores,
  deleteScore,
  downloadScoreTemplate,
  exportScores,
  getScoreList,
  getScoreStats,
  importScores
} from '@/api/score'
import { EXAM_BATCHES, SUBJECTS } from '@/utils/constants'
import { getClassList } from '@/api/class_'

const filterOptions = ref([
  { key: 'class_id', label: '班级', options: [] },
  { key: 'exam_batch', label: '考试批次', options: EXAM_BATCHES },
  { key: 'subject', label: '科目', options: SUBJECTS }
])

const queryParams = reactive({
  page: 1,
  page_size: 10,
  class_id: '',
  exam_batch: '',
  subject: ''
})

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const statsData = ref([])
const selectedIds = ref([])
const formVisible = ref(false)
const currentScore = ref(null)
const deleteVisible = ref(false)
const deleteLoading = ref(false)
const deleteTarget = ref(null)
const deleteMessage = ref('')

onMounted(async () => {
  await fetchClassOptions()
  await fetchData()
})

async function fetchClassOptions() {
  const res = await getClassList({ page: 1, page_size: 100 })
  filterOptions.value[0].options = res.list.map((item) => ({
    value: item.id,
    label: item.name
  }))
}

async function fetchData() {
  loading.value = true
  try {
    const [listRes, statsRes] = await Promise.all([
      getScoreList(queryParams),
      getScoreStats({
        class_id: queryParams.class_id || undefined,
        exam_batch: queryParams.exam_batch || undefined,
        subject: queryParams.subject || undefined
      })
    ])
    tableData.value = listRes.list
    total.value = listRes.total
    statsData.value = statsRes
  } finally {
    loading.value = false
  }
}

function handleSearch(params) {
  Object.assign(queryParams, params, { page: 1 })
  fetchData()
}

function handleReset() {
  Object.assign(queryParams, {
    page: 1,
    page_size: 10,
    class_id: '',
    exam_batch: '',
    subject: ''
  })
  fetchData()
}

function handlePageChange({ page, pageSize }) {
  queryParams.page = page
  queryParams.page_size = pageSize
  fetchData()
}

function handleSelectionChange(selection) {
  selectedIds.value = selection.map((item) => item.id)
}

function handleAdd() {
  currentScore.value = null
  formVisible.value = true
}

function handleEdit(row) {
  currentScore.value = { ...row }
  formVisible.value = true
}

function handleDelete(row) {
  deleteTarget.value = { type: 'single', id: row.id }
  deleteMessage.value = `确定删除 ${row.student_name} 的这条成绩吗？`
  deleteVisible.value = true
}

function handleBatchDelete() {
  deleteTarget.value = { type: 'batch', ids: [...selectedIds.value] }
  deleteMessage.value = `确定删除选中的 ${selectedIds.value.length} 条成绩吗？`
  deleteVisible.value = true
}

async function confirmDelete() {
  deleteLoading.value = true
  try {
    if (deleteTarget.value.type === 'single') {
      await deleteScore(deleteTarget.value.id)
    } else {
      await batchDeleteScores(deleteTarget.value.ids)
    }
    ElMessage.success('删除成功')
    deleteVisible.value = false
    await fetchData()
  } finally {
    deleteLoading.value = false
  }
}

async function handleImport(file) {
  const res = await importScores(file)
  ElMessage.success(`导入成功 ${res.success_count} 条`)
  await fetchData()
  return res
}

async function handleExport() {
  const res = await exportScores(queryParams)
  downloadBlob(res, '成绩列表.xlsx')
  ElMessage.success('导出成功')
}

async function handleDownloadTemplate() {
  const res = await downloadScoreTemplate()
  downloadBlob(res, '成绩导入模板.xlsx')
}

function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  window.URL.revokeObjectURL(url)
}
</script>

<style scoped lang="scss">
.stats-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.stats-card {
  .stats-title {
    font-weight: 600;
    margin-bottom: 8px;
  }

  .stats-row {
    font-size: 13px;
    color: #606266;
    line-height: 1.8;
  }
}

.action-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}

.left-actions,
.right-actions {
  display: flex;
  gap: 12px;
}

.score-danger {
  color: #f56c6c;
  font-weight: 600;
}
</style>
