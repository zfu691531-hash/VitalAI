<template>
  <div class="page-container">
    <SearchBar :filters="filterOptions" @search="handleSearch" @reset="handleReset" />

    <div class="action-bar">
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>新增校规
      </el-button>
    </div>

    <el-table v-loading="loading" :data="tableData" border stripe>
      <el-table-column prop="category" label="分类" width="140" />
      <el-table-column prop="title" label="标题" min-width="180" />
      <el-table-column prop="content" label="内容摘要" min-width="320" show-overflow-tooltip />
      <el-table-column prop="updated_at" label="更新时间" width="180" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEditDialog(row)">编辑</el-button>
          <el-button type="danger" link @click="openDeleteDialog(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <Pagination
      :total="total"
      :page="queryParams.page"
      :page-size="queryParams.page_size"
      @change="handlePageChange"
    />

    <el-dialog
      v-model="dialogVisible"
      :title="currentRule?.id ? '编辑校规' : '新增校规'"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="formState" :rules="rules" label-width="90px">
        <el-form-item label="分类" prop="category">
          <el-select v-model="formState.category" placeholder="请选择分类" style="width: 100%">
            <el-option
              v-for="item in categoryOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="标题" prop="title">
          <el-input v-model="formState.title" placeholder="请输入校规标题" />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input
            v-model="formState.content"
            type="textarea"
            :rows="8"
            placeholder="请输入校规正文"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
          {{ submitLoading ? '提交中...' : '确定' }}
        </el-button>
      </template>
    </el-dialog>

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
import { Plus } from '@element-plus/icons-vue'
import SearchBar from '@/components/common/SearchBar.vue'
import Pagination from '@/components/common/Pagination.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import {
  createSchoolRule,
  deleteSchoolRule,
  getSchoolRuleCategories,
  getSchoolRuleList,
  updateSchoolRule
} from '@/api/schoolRule'
import { RULE_CATEGORIES } from '@/utils/constants'

const queryParams = reactive({
  page: 1,
  page_size: 10,
  category: ''
})

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const submitLoading = ref(false)
const deleteVisible = ref(false)
const deleteLoading = ref(false)
const deleteRuleId = ref(null)
const deleteMessage = ref('')
const currentRule = ref(null)
const formRef = ref(null)
const categoryOptions = ref([...RULE_CATEGORIES])
const filterOptions = ref([
  { key: 'category', label: '分类', options: categoryOptions.value }
])

const formState = reactive({
  category: '',
  title: '',
  content: ''
})

const rules = {
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入内容', trigger: 'blur' }]
}

onMounted(async () => {
  await fetchCategories()
  await fetchList()
})

async function fetchCategories() {
  const res = await getSchoolRuleCategories()
  if (Array.isArray(res) && res.length > 0) {
    categoryOptions.value = res.map((item) => ({
      value: item.name,
      label: `${item.name} (${item.count})`
    }))
  }
  filterOptions.value = [{ key: 'category', label: '分类', options: categoryOptions.value }]
}

async function fetchList() {
  loading.value = true
  try {
    const res = await getSchoolRuleList(queryParams)
    tableData.value = res.list
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function handleSearch(params) {
  queryParams.page = 1
  queryParams.category = params.category || ''
  fetchList()
}

function handleReset() {
  Object.assign(queryParams, {
    page: 1,
    page_size: 10,
    category: ''
  })
  fetchList()
}

function handlePageChange({ page, pageSize }) {
  queryParams.page = page
  queryParams.page_size = pageSize
  fetchList()
}

function resetForm() {
  formState.category = ''
  formState.title = ''
  formState.content = ''
}

function openCreateDialog() {
  currentRule.value = null
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row) {
  currentRule.value = row
  formState.category = row.category
  formState.title = row.title
  formState.content = row.content
  dialogVisible.value = true
}

function openDeleteDialog(row) {
  deleteRuleId.value = row.id
  deleteMessage.value = `确定删除校规“${row.title}”吗？删除后不可恢复。`
  deleteVisible.value = true
}

async function handleSubmit() {
  await formRef.value?.validate()
  submitLoading.value = true

  try {
    if (currentRule.value?.id) {
      await updateSchoolRule(currentRule.value.id, { ...formState })
      ElMessage.success('校规已更新')
    } else {
      await createSchoolRule({ ...formState })
      ElMessage.success('校规已创建')
    }

    dialogVisible.value = false
    await fetchCategories()
    await fetchList()
  } finally {
    submitLoading.value = false
  }
}

async function confirmDelete() {
  deleteLoading.value = true
  try {
    await deleteSchoolRule(deleteRuleId.value)
    ElMessage.success('删除成功')
    deleteVisible.value = false
    await fetchCategories()
    await fetchList()
  } finally {
    deleteLoading.value = false
  }
}
</script>

<style scoped lang="scss">
.action-bar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}
</style>
