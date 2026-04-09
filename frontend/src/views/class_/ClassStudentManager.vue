<template>
  <el-dialog
    v-model="dialogVisible"
    title="班级学生管理"
    width="980px"
    :close-on-click-modal="false"
    @closed="handleClosed"
  >
    <div class="manager-head">
      <div>
        <div class="class-name">{{ classData?.name || '未命名班级' }}</div>
        <div class="class-meta">
          {{ classData?.grade || '-' }} · 班主任：{{ classData?.head_teacher_name || '未设置' }}
        </div>
      </div>
      <el-tag type="info">当前人数 {{ boundStudents.length }} / {{ classData?.max_count || '-' }}</el-tag>
    </div>

    <div class="manager-grid">
      <el-card shadow="never" class="manager-card">
        <template #header>
          <div class="card-head">
            <span>班级内学生</span>
            <el-button
              type="danger"
              link
              :disabled="selectedBoundIds.length === 0"
              @click="handleBatchUnbind"
            >
              批量移除
            </el-button>
          </div>
        </template>

        <el-table
          v-loading="loadingBound"
          :data="boundStudents"
          height="430"
          border
          @selection-change="handleBoundSelectionChange"
        >
          <el-table-column type="selection" width="50" />
          <el-table-column prop="student_no" label="学号" width="120" />
          <el-table-column prop="name" label="姓名" width="100" />
          <el-table-column label="性别" width="80">
            <template #default="{ row }">
              {{ row.gender === 'male' ? '男' : '女' }}
            </template>
          </el-table-column>
          <el-table-column prop="grade" label="年级" width="100" />
          <el-table-column prop="contact" label="联系方式" min-width="140" show-overflow-tooltip />
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button type="danger" link @click="handleSingleUnbind(row)">移除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never" class="manager-card">
        <template #header>
          <div class="card-head">
            <span>可加入学生</span>
            <el-button
              type="primary"
              link
              :disabled="selectedAvailableIds.length === 0"
              @click="handleBatchBind"
            >
              批量加入
            </el-button>
          </div>
        </template>

        <el-form :inline="true" :model="searchForm" class="search-form">
          <el-form-item>
            <el-input
              v-model="searchForm.keyword"
              placeholder="搜索姓名或学号"
              clearable
              style="width: 180px"
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item>
            <el-select v-model="searchForm.grade" clearable placeholder="年级" style="width: 120px">
              <el-option v-for="item in gradeOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-select v-model="searchForm.gender" clearable placeholder="性别" style="width: 100px">
              <el-option label="男" value="male" />
              <el-option label="女" value="female" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-select v-model="searchForm.tag" clearable placeholder="标签" style="width: 120px">
              <el-option label="关怀" value="关怀" />
              <el-option label="违纪" value="违纪" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-select v-model="searchForm.class_id" clearable placeholder="当前班级" style="width: 150px">
              <el-option label="未分班" value="__unassigned__" />
              <el-option
                v-for="item in classOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>

        <el-table
          v-loading="loadingAvailable"
          :data="availableStudents"
          height="334"
          border
          @selection-change="handleAvailableSelectionChange"
        >
          <el-table-column type="selection" width="50" />
          <el-table-column prop="student_no" label="学号" width="120" />
          <el-table-column prop="name" label="姓名" width="100" />
          <el-table-column prop="grade" label="年级" width="90" />
          <el-table-column prop="class_name" label="当前班级" min-width="120" show-overflow-tooltip />
          <el-table-column prop="tags" label="标签" min-width="110" show-overflow-tooltip />
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="handleSingleBind(row)">加入</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </el-dialog>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { bindStudents, unbindStudents } from '@/api/class_'
import { getStudentList } from '@/api/student'
import { getClassList } from '@/api/class_'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  classData: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:visible', 'success'])

const dialogVisible = ref(props.visible)
const loadingBound = ref(false)
const loadingAvailable = ref(false)
const boundStudents = ref([])
const availableStudents = ref([])
const selectedBoundIds = ref([])
const selectedAvailableIds = ref([])
const classOptions = ref([])
const gradeOptions = ref([])

const searchForm = reactive({
  keyword: '',
  grade: '',
  gender: '',
  tag: '',
  class_id: ''
})

watch(
  () => props.visible,
  async (value) => {
    dialogVisible.value = value
    if (!value || !props.classData?.id) return
    await fetchClassOptions()
    await refreshStudents()
  }
)

async function fetchClassOptions() {
  const res = await getClassList({ page: 1, page_size: 100 })
  classOptions.value = res.list || []
  gradeOptions.value = Array.from(new Set(classOptions.value.map((item) => item.grade).filter(Boolean)))
}

async function refreshStudents() {
  await Promise.all([fetchBoundStudents(), fetchAvailableStudents()])
}

async function fetchBoundStudents() {
  loadingBound.value = true
  try {
    const res = await getStudentList({
      page: 1,
      page_size: 100,
      class_id: props.classData.id
    })
    boundStudents.value = res.list || []
  } finally {
    loadingBound.value = false
  }
}

async function fetchAvailableStudents() {
  loadingAvailable.value = true
  try {
    const params = {
      page: 1,
      page_size: 100,
      keyword: searchForm.keyword || undefined,
      grade: searchForm.grade || undefined,
      gender: searchForm.gender || undefined,
      tag: searchForm.tag || undefined
    }

    if (searchForm.class_id && searchForm.class_id !== '__unassigned__') {
      params.class_id = searchForm.class_id
    }

    const res = await getStudentList(params)
    availableStudents.value = (res.list || []).filter((item) => {
      if (item.class_id === props.classData.id) return false
      if (searchForm.class_id === '__unassigned__') {
        return !item.class_id
      }
      return true
    })
  } finally {
    loadingAvailable.value = false
  }
}

function handleSearch() {
  fetchAvailableStudents()
}

function handleReset() {
  Object.assign(searchForm, {
    keyword: '',
    grade: '',
    gender: '',
    tag: '',
    class_id: ''
  })
  fetchAvailableStudents()
}

function handleBoundSelectionChange(selection) {
  selectedBoundIds.value = selection.map((item) => item.id)
}

function handleAvailableSelectionChange(selection) {
  selectedAvailableIds.value = selection.map((item) => item.id)
}

async function handleSingleBind(row) {
  await bindSelected([row.id])
}

async function handleBatchBind() {
  await bindSelected(selectedAvailableIds.value)
}

async function bindSelected(ids) {
  if (!ids.length) return
  await bindStudents(props.classData.id, ids)
  ElMessage.success('学生已加入班级')
  await refreshStudents()
  emit('success')
}

async function handleSingleUnbind(row) {
  await unbindSelected([row.id])
}

async function handleBatchUnbind() {
  await unbindSelected(selectedBoundIds.value)
}

async function unbindSelected(ids) {
  if (!ids.length) return
  await unbindStudents(props.classData.id, ids)
  ElMessage.success('学生已移出班级')
  await refreshStudents()
  emit('success')
}

function handleClosed() {
  handleReset()
  selectedBoundIds.value = []
  selectedAvailableIds.value = []
  emit('update:visible', false)
}
</script>

<style scoped lang="scss">
.manager-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.class-name {
  font-size: 18px;
  font-weight: 700;
  color: #303133;
}

.class-meta {
  margin-top: 6px;
  font-size: 13px;
  color: #909399;
}

.manager-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.manager-card {
  min-width: 0;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.search-form {
  margin-bottom: 12px;
}

@media (max-width: 980px) {
  .manager-grid {
    grid-template-columns: 1fr;
  }
}
</style>
