<template>
  <div class="page-container">
    <SearchBar :filters="filterOptions" @search="handleSearch" @reset="handleReset" />

    <div class="action-bar">
      <div class="left-actions">
        <el-button type="primary" v-permission="['admin']" @click="handleAdd">
          <el-icon><Plus /></el-icon>新增班级
        </el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="tableData" border stripe>
      <el-table-column prop="grade" label="年级" width="120" />
      <el-table-column prop="name" label="班级名称" min-width="140" />
      <el-table-column prop="head_teacher_name" label="班主任" width="140" />
      <el-table-column prop="max_count" label="人数上限" width="110" />
      <el-table-column prop="current_count" label="当前人数" width="110" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'">
            {{ row.status === 1 ? '在读' : '毕业' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="handleManageStudents(row)">
            管理学生
          </el-button>
          <el-button type="primary" link v-permission="['admin']" @click="handleEdit(row)">
            编辑
          </el-button>
          <el-button type="danger" link v-permission="['admin']" @click="handleDelete(row)">
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

    <ClassForm
      v-model:visible="formVisible"
      :class-data="currentClass"
      @success="handleFormSuccess"
    />

    <ClassStudentManager
      v-model:visible="studentManagerVisible"
      :class-data="currentClass"
      @success="handleStudentManagerSuccess"
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
import { deleteClass, getClassList } from '@/api/class_'
import { GRADES } from '@/utils/constants'
import ClassForm from './ClassForm.vue'
import ClassStudentManager from './ClassStudentManager.vue'

const filterOptions = [
  { key: 'grade', label: '年级', options: GRADES },
  {
    key: 'status',
    label: '状态',
    options: [
      { value: 1, label: '在读' },
      { value: 0, label: '毕业' }
    ]
  }
]

const queryParams = reactive({
  page: 1,
  page_size: 10,
  keyword: '',
  grade: '',
  status: 1
})

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const formVisible = ref(false)
const studentManagerVisible = ref(false)
const currentClass = ref(null)
const deleteVisible = ref(false)
const deleteLoading = ref(false)
const deleteClassId = ref(null)
const deleteMessage = ref('')

onMounted(() => {
  fetchList()
})

async function fetchList() {
  loading.value = true
  try {
    const res = await getClassList({
      page: queryParams.page,
      page_size: queryParams.page_size,
      grade: queryParams.grade || undefined,
      status: queryParams.status === '' ? undefined : queryParams.status
    })
    tableData.value = res.list
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function handleSearch(params) {
  Object.assign(queryParams, params, { page: 1 })
  if (queryParams.status !== '' && queryParams.status !== 0 && queryParams.status !== 1) {
    queryParams.status = 1
  }
  fetchList()
}

function handleReset() {
  Object.assign(queryParams, {
    page: 1,
    page_size: 10,
    keyword: '',
    grade: '',
    status: 1
  })
  fetchList()
}

function handlePageChange({ page, pageSize }) {
  queryParams.page = page
  queryParams.page_size = pageSize
  fetchList()
}

function handleAdd() {
  currentClass.value = null
  formVisible.value = true
}

function handleEdit(row) {
  currentClass.value = { ...row }
  formVisible.value = true
}

function handleManageStudents(row) {
  currentClass.value = { ...row }
  studentManagerVisible.value = true
}

function handleFormSuccess() {
  formVisible.value = false
  fetchList()
}

function handleStudentManagerSuccess() {
  studentManagerVisible.value = false
  fetchList()
}

function handleDelete(row) {
  deleteClassId.value = row.id
  deleteMessage.value = `确定删除班级“${row.name}”吗？删除后不可恢复。`
  deleteVisible.value = true
}

async function confirmDelete() {
  deleteLoading.value = true
  try {
    await deleteClass(deleteClassId.value)
    ElMessage.success('删除成功')
    deleteVisible.value = false
    fetchList()
  } finally {
    deleteLoading.value = false
  }
}
</script>
