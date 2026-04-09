<template>
  <div class="page-container">
    <SearchBar :filters="filterOptions" @search="handleSearch" @reset="handleReset" />

    <div class="action-bar">
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>新增教师
      </el-button>
    </div>

    <el-table v-loading="loading" :data="tableData" border stripe>
      <el-table-column prop="name" label="姓名" width="120" />
      <el-table-column prop="subject" label="学科" width="140" />
      <el-table-column prop="title" label="职务" width="120">
        <template #default="{ row }">
          {{ row.title === 'head_teacher' ? '班主任' : '普通教师' }}
        </template>
      </el-table-column>
      <el-table-column prop="class_names" label="绑定班级" min-width="220" show-overflow-tooltip />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
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

    <TeacherForm
      v-model:visible="formVisible"
      :teacher="currentTeacher"
      @success="handleFormSuccess"
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
import { Plus } from '@element-plus/icons-vue'
import SearchBar from '@/components/common/SearchBar.vue'
import Pagination from '@/components/common/Pagination.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import TeacherForm from './TeacherForm.vue'
import { getTeacherList, deleteTeacher } from '@/api/teacher'
import { SUBJECTS } from '@/utils/constants'

const filterOptions = [
  { key: 'subject', label: '学科', options: SUBJECTS }
]

const queryParams = reactive({
  page: 1,
  page_size: 10,
  keyword: '',
  subject: ''
})

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const formVisible = ref(false)
const currentTeacher = ref(null)
const deleteVisible = ref(false)
const deleteLoading = ref(false)
const deleteTeacherId = ref(null)
const deleteMessage = ref('')

onMounted(() => {
  fetchList()
})

async function fetchList() {
  loading.value = true
  try {
    const res = await getTeacherList(queryParams)
    tableData.value = res.list
    total.value = res.total
  } finally {
    loading.value = false
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
    subject: ''
  })
  fetchList()
}

function handlePageChange({ page, pageSize }) {
  queryParams.page = page
  queryParams.page_size = pageSize
  fetchList()
}

function handleAdd() {
  currentTeacher.value = null
  formVisible.value = true
}

function handleEdit(row) {
  currentTeacher.value = { ...row }
  formVisible.value = true
}

function handleFormSuccess() {
  formVisible.value = false
  fetchList()
}

function handleDelete(row) {
  deleteTeacherId.value = row.id
  deleteMessage.value = `确定删除教师“${row.name}”吗？删除后不可恢复。`
  deleteVisible.value = true
}

async function confirmDelete() {
  deleteLoading.value = true
  try {
    await deleteTeacher(deleteTeacherId.value)
    ElMessage.success('删除成功')
    deleteVisible.value = false
    fetchList()
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
