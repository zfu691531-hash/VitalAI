<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑学生' : '新增学生'"
    width="640px"
    :close-on-click-modal="false"
    @closed="handleClosed"
  >
    <el-form ref="formRef" :model="formState" :rules="rules" label-width="100px">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="学号" prop="student_no">
            <el-input v-model="formState.student_no" placeholder="请输入学号" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="姓名" prop="name">
            <el-input v-model="formState.name" placeholder="请输入姓名" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="性别" prop="gender">
            <el-radio-group v-model="formState.gender">
              <el-radio value="male">男</el-radio>
              <el-radio value="female">女</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="年龄" prop="age">
            <el-input-number v-model="formState.age" :min="1" :max="100" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="年级" prop="grade">
            <el-select v-model="formState.grade" placeholder="请选择年级" style="width: 100%">
              <el-option v-for="item in gradeOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="所属班级" prop="class_id">
            <el-select
              v-model="formState.class_id"
              clearable
              placeholder="请选择班级"
              style="width: 100%"
              @change="handleClassChange"
            >
              <el-option
                v-for="item in classOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="联系方式" prop="contact">
        <el-input v-model="formState.contact" placeholder="请输入联系方式" />
      </el-form-item>

      <el-form-item label="特长" prop="specialty">
        <el-input v-model="formState.specialty" placeholder="请输入特长" />
      </el-form-item>

      <el-form-item label="标签" prop="tags">
        <el-select
          v-model="selectedTags"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="请选择或输入标签"
          style="width: 100%"
        >
          <el-option-group label="正向标签">
            <el-option v-for="tag in tagGroups.positive" :key="tag" :label="tag" :value="tag" />
          </el-option-group>
          <el-option-group label="中性标签">
            <el-option v-for="tag in tagGroups.neutral" :key="tag" :label="tag" :value="tag" />
          </el-option-group>
          <el-option-group label="负向标签">
            <el-option v-for="tag in tagGroups.negative" :key="tag" :label="tag" :value="tag" />
          </el-option-group>
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">
        {{ loading ? '提交中...' : '确定' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { getClassList } from '@/api/class_'
import { createStudent, updateStudent } from '@/api/student'
import { useUserStore } from '@/stores/user'
import { STUDENT_TAGS } from '@/utils/constants'
import { getAvailableTagDefinitions } from '@/api/tagDefinitions'

const props = defineProps({
  visible: { type: Boolean, default: false },
  student: { type: Object, default: null }
})

const emit = defineEmits(['update:visible', 'success'])

const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)
const dialogVisible = ref(props.visible)
const classOptions = ref([])
const selectedTags = ref([])

const careTags = STUDENT_TAGS.CARE
const disciplineTags = STUDENT_TAGS.DISCIPLINE
const tagDefinitions = ref([])

const formState = reactive({
  student_no: '',
  name: '',
  gender: 'male',
  age: null,
  grade: '',
  class_id: null,
  contact: '',
  specialty: '',
  tags: ''
})

const isEdit = computed(() => !!props.student?.id)

const gradeOptions = computed(() => {
  const grades = new Set(classOptions.value.map((item) => item.grade).filter(Boolean))
  if (formState.grade) grades.add(formState.grade)
  return Array.from(grades)
})

const tagGroups = computed(() => {
  const groups = {
    positive: new Set(),
    neutral: new Set(),
    negative: new Set()
  }
  careTags.forEach((tag) => groups.neutral.add(tag))
  disciplineTags.forEach((tag) => groups.neutral.add(tag))
  tagDefinitions.value.forEach((item) => {
    const polarity = item.polarity || 'neutral'
    if (!groups[polarity]) {
      groups.neutral.add(item.tag_text)
      return
    }
    groups[polarity].add(item.tag_text)
  })
  return {
    positive: Array.from(groups.positive),
    neutral: Array.from(groups.neutral),
    negative: Array.from(groups.negative)
  }
})

const rules = {
  student_no: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  gender: [{ required: true, message: '请选择性别', trigger: 'change' }],
  age: [{ required: true, message: '请输入年龄', trigger: 'change' }],
  grade: [{ required: true, message: '请选择年级', trigger: 'change' }],
  class_id: [
    {
      validator: (_rule, value, callback) => {
        if (userStore.role === 'teacher' && !value) {
          callback(new Error('教师新增或编辑学生时必须选择本班班级'))
          return
        }
        callback()
      },
      trigger: 'change'
    }
  ],
  contact: [
    {
      validator: (_rule, value, callback) => {
        if (!value) {
          callback()
          return
        }
        if (!/^1[3-9]\d{9}$/.test(value)) {
          callback(new Error('请输入正确的手机号'))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ]
}

watch(
  () => props.visible,
  (value) => {
    dialogVisible.value = value
    if (!value) return
    if (props.student) {
      Object.assign(formState, {
        student_no: props.student.student_no || '',
        name: props.student.name || '',
        gender: props.student.gender || 'male',
        age: props.student.age,
        grade: props.student.grade || '',
        class_id: props.student.class_id ?? null,
        contact: props.student.contact || '',
        specialty: props.student.specialty || '',
        tags: props.student.tags || ''
      })
      selectedTags.value = formState.tags ? formState.tags.split(',').filter(Boolean) : []
      fetchAvailableTags()
    } else {
      resetForm()
      fetchAvailableTags()
    }
  }
)

watch(
  () => formState.grade,
  () => {
    fetchAvailableTags()
  }
)

onMounted(() => {
  fetchClassOptions()
  fetchAvailableTags()
})

async function fetchClassOptions() {
  const res = await getClassList({ page: 1, page_size: 100 })
  classOptions.value = (res.list || []).map((item) => ({
    value: item.id,
    label: `${item.grade} · ${item.name}`,
    grade: item.grade
  }))
}

async function fetchAvailableTags() {
  try {
    const res = await getAvailableTagDefinitions({
      class_id: formState.class_id || undefined,
      grade: formState.grade || undefined
    })
    tagDefinitions.value = res.list || []
  } catch (error) {
    console.error('获取标签字典失败', error)
  }
}

function handleClassChange(value) {
  const selected = classOptions.value.find((item) => item.value === value)
  if (selected) {
    formState.grade = selected.grade
  }
  fetchAvailableTags()
}

function resetForm() {
  Object.assign(formState, {
    student_no: '',
    name: '',
    gender: 'male',
    age: null,
    grade: '',
    class_id: null,
    contact: '',
    specialty: '',
    tags: ''
  })
  selectedTags.value = []
}

function handleClosed() {
  emit('update:visible', false)
  formRef.value?.resetFields()
  resetForm()
}

async function handleSubmit() {
  await formRef.value?.validate()
  loading.value = true
  try {
    const payload = {
      ...formState,
      tags: selectedTags.value.join(',') || null,
      class_id: formState.class_id || null
    }
    if (isEdit.value) {
      await updateStudent(props.student.id, payload)
      ElMessage.success('学生信息已更新')
    } else {
      await createStudent(payload)
      ElMessage.success('学生已创建')
    }
    dialogVisible.value = false
    emit('success')
  } finally {
    loading.value = false
  }
}
</script>
