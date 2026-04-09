<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">标签审核</div>
        <div class="page-subtitle">管理员与班主任可确认新增标签的语义与极性</div>
      </div>
    </div>

    <div class="filter-bar">
      <el-select v-model="queryParams.status" placeholder="状态" clearable style="width: 140px">
        <el-option label="待审核" value="pending" />
        <el-option label="已通过" value="approved" />
        <el-option label="已驳回" value="rejected" />
      </el-select>
      <el-input v-model="queryParams.keyword" placeholder="标签关键词" style="width: 220px" />
      <el-select
        v-if="isAdmin"
        v-model="queryParams.class_id"
        placeholder="班级"
        clearable
        style="width: 200px"
      >
        <el-option v-for="item in classOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-input v-model="queryParams.grade" placeholder="年级" style="width: 140px" />
      <el-button size="small" type="success" @click="fetchList">筛选</el-button>
      <el-button size="small" @click="resetFilters">重置</el-button>
    </div>

    <el-table v-loading="loading" :data="tableData" border stripe>
      <el-table-column prop="tag_text" label="标签" min-width="140" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="class_id" label="班级" min-width="120">
        <template #default="{ row }">{{ classLabel(row.class_id) }}</template>
      </el-table-column>
      <el-table-column prop="grade" label="年级" width="100" />
      <el-table-column prop="source" label="来源" width="120">
        <template #default="{ row }">{{ sourceLabel(row.source) }}</template>
      </el-table-column>
      <el-table-column prop="suggested_polarity" label="建议极性" width="110">
        <template #default="{ row }">{{ polarityLabel(row.suggested_polarity) }}</template>
      </el-table-column>
      <el-table-column prop="suggested_dimension" label="建议维度" width="120">
        <template #default="{ row }">{{ dimensionLabel(row.suggested_dimension) }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending'" type="primary" link @click="openApprove(row)">通过</el-button>
          <el-button v-if="row.status === 'pending'" type="danger" link @click="openReject(row)">驳回</el-button>
          <span v-else>—</span>
        </template>
      </el-table-column>
    </el-table>

    <Pagination
      :total="total"
      :page="queryParams.page"
      :page-size="queryParams.page_size"
      @change="handlePageChange"
    />

    <el-dialog v-model="approveVisible" title="标签审核通过" width="580px">
      <el-form :model="approveForm" label-width="100px">
        <el-form-item label="标签内容">
          <el-input v-model="approveForm.tag_text" disabled />
        </el-form-item>
        <el-form-item label="范围类型">
          <el-select v-model="approveForm.scope_type">
            <el-option label="班级" value="class" />
            <el-option label="年级" value="grade" />
            <el-option label="学校" value="school" />
          </el-select>
        </el-form-item>
        <el-form-item label="范围值">
          <el-select
            v-if="approveForm.scope_type === 'class'"
            v-model="approveForm.scope_value"
            filterable
            placeholder="选择班级"
          >
            <el-option v-for="item in classOptions" :key="item.value" :label="item.label" :value="String(item.value)" />
          </el-select>
          <el-input
            v-else
            v-model="approveForm.scope_value"
            placeholder="年级填 高一/高二，学校可留空"
          />
        </el-form-item>
        <el-form-item label="极性">
          <el-select v-model="approveForm.polarity">
            <el-option label="正向" value="positive" />
            <el-option label="中性" value="neutral" />
            <el-option label="负向" value="negative" />
          </el-select>
        </el-form-item>
        <el-form-item label="维度">
          <el-select v-model="approveForm.dimension" placeholder="可选">
            <el-option label="情绪状态" value="emotion" />
            <el-option label="社交融入" value="social" />
            <el-option label="校园安全" value="safety" />
            <el-option label="家庭支持" value="family" />
            <el-option label="学习压力" value="study" />
            <el-option label="行为稳定" value="behavior" />
          </el-select>
        </el-form-item>
        <el-form-item label="权重">
          <el-input-number v-model="approveForm.weight" :min="0" :max="1" :step="0.05" style="width: 100%" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="approveForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="审核备注">
          <el-input v-model="approveForm.review_note" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approveVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitApprove">确认通过</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="rejectVisible" title="驳回标签" width="460px">
      <el-form :model="rejectForm" label-width="80px">
        <el-form-item label="标签">
          <el-input v-model="rejectForm.tag_text" disabled />
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="rejectForm.review_note" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="submitReject">确认驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import Pagination from '@/components/common/Pagination.vue'
import { useUserStore } from '@/stores/user'
import { getClassList } from '@/api/class_'
import { approveTagReview, getTagReviews, rejectTagReview } from '@/api/tagReviews'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const tableData = ref([])
const total = ref(0)
const classOptions = ref([])
const approveVisible = ref(false)
const rejectVisible = ref(false)

const isAdmin = computed(() => userStore.role === 'admin')

const queryParams = reactive({
  page: 1,
  page_size: 10,
  status: 'pending',
  keyword: '',
  class_id: '',
  grade: ''
})

const approveForm = reactive({
  id: null,
  tag_text: '',
  scope_type: 'class',
  scope_value: '',
  polarity: 'neutral',
  dimension: '',
  weight: null,
  description: '',
  review_note: ''
})

const rejectForm = reactive({
  id: null,
  tag_text: '',
  review_note: ''
})

onMounted(() => {
  fetchList()
  fetchClassOptions()
})

async function fetchList() {
  loading.value = true
  try {
    const res = await getTagReviews({
      page: queryParams.page,
      page_size: queryParams.page_size,
      status: queryParams.status || undefined,
      keyword: queryParams.keyword || undefined,
      class_id: queryParams.class_id || undefined,
      grade: queryParams.grade || undefined
    })
    tableData.value = res.list || []
    total.value = res.total || 0
  } finally {
    loading.value = false
  }
}

async function fetchClassOptions() {
  const res = await getClassList({ page: 1, page_size: 200 })
  classOptions.value = (res.list || []).map((item) => ({
    value: item.id,
    label: `${item.grade} · ${item.name}`
  }))
}

function handlePageChange({ page, pageSize }) {
  queryParams.page = page
  queryParams.page_size = pageSize
  fetchList()
}

function resetFilters() {
  queryParams.page = 1
  queryParams.page_size = 10
  queryParams.status = 'pending'
  queryParams.keyword = ''
  queryParams.class_id = ''
  queryParams.grade = ''
  fetchList()
}

function openApprove(row) {
  approveForm.id = row.id
  approveForm.tag_text = row.tag_text
  approveForm.scope_type = row.suggested_scope_type || (row.class_id ? 'class' : row.grade ? 'grade' : 'school')
  approveForm.scope_value = row.suggested_scope_value || (row.class_id ? String(row.class_id) : row.grade || '')
  approveForm.polarity = row.suggested_polarity || 'neutral'
  approveForm.dimension = row.suggested_dimension || ''
  approveForm.weight = row.suggested_weight ?? null
  approveForm.description = row.suggested_description || ''
  approveForm.review_note = ''
  approveVisible.value = true
}

function openReject(row) {
  rejectForm.id = row.id
  rejectForm.tag_text = row.tag_text
  rejectForm.review_note = ''
  rejectVisible.value = true
}

async function submitApprove() {
  saving.value = true
  try {
    const payload = { ...approveForm }
    if (!payload.scope_value) payload.scope_value = null
    await approveTagReview(approveForm.id, payload)
    ElMessage.success('已通过')
    approveVisible.value = false
    fetchList()
  } finally {
    saving.value = false
  }
}

async function submitReject() {
  saving.value = true
  try {
    await rejectTagReview(rejectForm.id, { review_note: rejectForm.review_note })
    ElMessage.success('已驳回')
    rejectVisible.value = false
    fetchList()
  } finally {
    saving.value = false
  }
}

function statusLabel(value) {
  return { pending: '待审核', approved: '已通过', rejected: '已驳回' }[value] || value
}

function statusType(value) {
  return { pending: 'warning', approved: 'success', rejected: 'info' }[value] || 'info'
}

function sourceLabel(value) {
  return { teacher_input: '教师录入', ai_detected: 'AI识别' }[value] || value || '-'
}

function classLabel(id) {
  if (!id) return '-'
  const match = classOptions.value.find((item) => String(item.value) === String(id))
  return match ? match.label : id
}

function polarityLabel(value) {
  return { positive: '正向', neutral: '中性', negative: '负向' }[value] || '-'
}

function dimensionLabel(value) {
  return {
    emotion: '情绪状态',
    social: '社交融入',
    safety: '校园安全',
    family: '家庭支持',
    study: '学习压力',
    behavior: '行为稳定'
  }[value] || '-'
}
</script>

<style scoped lang="scss">
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
}

.page-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
</style>
