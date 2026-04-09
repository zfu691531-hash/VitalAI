<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">标签字典管理</div>
        <div class="page-subtitle">管理员维护标签分类与正负向标注</div>
      </div>
      <el-button type="primary" @click="openCreate">新增标签</el-button>
    </div>

    <div class="filter-bar">
      <el-select v-model="queryParams.scope_type" placeholder="范围类型" clearable style="width: 160px">
        <el-option label="学校" value="school" />
        <el-option label="年级" value="grade" />
        <el-option label="班级" value="class" />
      </el-select>
      <el-input v-model="queryParams.keyword" placeholder="标签关键词" style="width: 220px" />
      <el-button size="small" type="success" @click="fetchList">筛选</el-button>
      <el-button size="small" @click="resetFilters">重置</el-button>
    </div>

    <el-table v-loading="loading" :data="tableData" border stripe>
      <el-table-column prop="tag_text" label="标签" width="160" />
      <el-table-column prop="scope_type" label="范围" width="100">
        <template #default="{ row }">{{ scopeLabel(row.scope_type) }}</template>
      </el-table-column>
      <el-table-column prop="scope_value" label="范围值" width="160">
        <template #default="{ row }">{{ scopeValueLabel(row) }}</template>
      </el-table-column>
      <el-table-column prop="polarity" label="正负向" width="100">
        <template #default="{ row }">{{ polarityLabel(row.polarity) }}</template>
      </el-table-column>
      <el-table-column prop="dimension" label="维度" width="120">
        <template #default="{ row }">{{ dimensionLabel(row.dimension) }}</template>
      </el-table-column>
      <el-table-column prop="weight" label="权重" width="80" />
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEdit(row)">编辑</el-button>
          <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <Pagination
      :total="total"
      :page="queryParams.page"
      :page-size="queryParams.page_size"
      @change="handlePageChange"
    />

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="560px">
      <el-form ref="formRef" :model="formState" label-width="100px">
        <el-form-item label="范围类型" prop="scope_type">
          <el-select v-model="formState.scope_type" placeholder="请选择">
            <el-option label="学校" value="school" />
            <el-option label="年级" value="grade" />
            <el-option label="班级" value="class" />
          </el-select>
        </el-form-item>
        <el-form-item label="范围值" prop="scope_value">
          <el-select
            v-if="formState.scope_type === 'class'"
            v-model="formState.scope_value"
            placeholder="请选择班级"
            filterable
          >
            <el-option v-for="item in classOptions" :key="item.value" :label="item.label" :value="String(item.value)" />
          </el-select>
          <el-input
            v-else
            v-model="formState.scope_value"
            placeholder="学校范围可留空，年级可填 高一/高二"
          />
        </el-form-item>
        <el-form-item label="标签内容" prop="tag_text">
          <el-input v-model="formState.tag_text" placeholder="请输入标签" />
        </el-form-item>
        <el-form-item label="正负向" prop="polarity">
          <el-select v-model="formState.polarity" placeholder="请选择">
            <el-option label="正向" value="positive" />
            <el-option label="中性" value="neutral" />
            <el-option label="负向" value="negative" />
          </el-select>
        </el-form-item>
        <el-form-item label="维度" prop="dimension">
          <el-select v-model="formState.dimension" placeholder="可选">
            <el-option label="情绪状态" value="emotion" />
            <el-option label="社交融入" value="social" />
            <el-option label="校园安全" value="safety" />
            <el-option label="家庭支持" value="family" />
            <el-option label="学习压力" value="study" />
            <el-option label="行为稳定" value="behavior" />
          </el-select>
        </el-form-item>
        <el-form-item label="权重" prop="weight">
          <el-input-number v-model="formState.weight" :min="0" :max="1" :step="0.05" style="width: 100%" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="formState.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import Pagination from '@/components/common/Pagination.vue'
import { getClassList } from '@/api/class_'
import {
  createTagDefinition,
  deleteTagDefinition,
  getTagDefinitions,
  updateTagDefinition
} from '@/api/tagDefinitions'

const loading = ref(false)
const saving = ref(false)
const tableData = ref([])
const total = ref(0)
const classOptions = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('新增标签')
const currentId = ref(null)

const queryParams = reactive({
  page: 1,
  page_size: 10,
  scope_type: '',
  keyword: ''
})

const formState = reactive({
  scope_type: 'school',
  scope_value: '',
  tag_text: '',
  polarity: 'neutral',
  dimension: '',
  weight: null,
  description: ''
})

onMounted(() => {
  fetchList()
  fetchClassOptions()
})

async function fetchList() {
  loading.value = true
  try {
    const res = await getTagDefinitions({
      page: queryParams.page,
      page_size: queryParams.page_size,
      scope_type: queryParams.scope_type || undefined,
      keyword: queryParams.keyword || undefined
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
  queryParams.scope_type = ''
  queryParams.keyword = ''
  fetchList()
}

function openCreate() {
  dialogTitle.value = '新增标签'
  currentId.value = null
  Object.assign(formState, {
    scope_type: 'school',
    scope_value: '',
    tag_text: '',
    polarity: 'neutral',
    dimension: '',
    weight: null,
    description: ''
  })
  dialogVisible.value = true
}

function openEdit(row) {
  dialogTitle.value = '编辑标签'
  currentId.value = row.id
  Object.assign(formState, {
    scope_type: row.scope_type,
    scope_value: row.scope_value || '',
    tag_text: row.tag_text,
    polarity: row.polarity,
    dimension: row.dimension || '',
    weight: row.weight ?? null,
    description: row.description || ''
  })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const payload = { ...formState }
    if (!payload.scope_value) payload.scope_value = null
    if (currentId.value) {
      await updateTagDefinition(currentId.value, payload)
      ElMessage.success('标签已更新')
    } else {
      await createTagDefinition(payload)
      ElMessage.success('标签已创建')
    }
    dialogVisible.value = false
    fetchList()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  await deleteTagDefinition(row.id)
  ElMessage.success('已删除')
  fetchList()
}

function scopeLabel(value) {
  return { school: '学校', grade: '年级', class: '班级' }[value] || value
}

function polarityLabel(value) {
  return { positive: '正向', neutral: '中性', negative: '负向' }[value] || value
}

function dimensionLabel(value) {
  return {
    emotion: '情绪状态',
    social: '社交融入',
    safety: '校园安全',
    family: '家庭支持',
    study: '学习压力',
    behavior: '行为稳定'
  }[value] || value
}

function scopeValueLabel(row) {
  if (row.scope_type === 'class') {
    const match = classOptions.value.find((item) => String(item.value) === String(row.scope_value))
    return match ? match.label : row.scope_value
  }
  return row.scope_value || '-'
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
