<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑班级' : '新增班级'"
    width="620px"
    :close-on-click-modal="false"
    @closed="handleClosed"
  >
    <el-form ref="formRef" :model="formState" :rules="rules" label-width="100px">
      <el-form-item label="年级" prop="grade">
        <el-select v-model="formState.grade" placeholder="请选择年级" style="width: 100%">
          <el-option
            v-for="item in GRADES"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="班级名称" prop="name">
        <el-input v-model="formState.name" placeholder="请输入班级名称" />
      </el-form-item>

      <el-form-item label="班主任" prop="head_teacher_id">
        <el-select v-model="formState.head_teacher_id" placeholder="请选择班主任" filterable style="width: 100%">
          <el-option
            v-for="item in teacherOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="人数上限" prop="max_count">
        <el-input-number v-model="formState.max_count" :min="1" :max="200" style="width: 100%" />
      </el-form-item>

      <el-form-item label="状态" prop="status">
        <el-radio-group v-model="formState.status">
          <el-radio :label="1">在读</el-radio>
          <el-radio :label="0">毕业</el-radio>
        </el-radio-group>
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
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createClass, updateClass } from '@/api/class_'
import { getTeacherList } from '@/api/teacher'
import { GRADES } from '@/utils/constants'

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

const formRef = ref(null)
const dialogVisible = ref(props.visible)
const loading = ref(false)
const teacherOptions = ref([])

const isEdit = computed(() => !!props.classData?.id)

const formState = reactive({
  grade: '',
  name: '',
  head_teacher_id: '',
  max_count: 50,
  status: 1
})

const rules = {
  grade: [{ required: true, message: '请选择年级', trigger: 'change' }],
  name: [{ required: true, message: '请输入班级名称', trigger: 'blur' }],
  head_teacher_id: [{ required: true, message: '请选择班主任', trigger: 'change' }],
  max_count: [{ required: true, message: '请设置人数上限', trigger: 'change' }]
}

watch(
  () => props.visible,
  async (value) => {
    dialogVisible.value = value
    if (!value) return

    await fetchTeacherOptions()
    if (props.classData) {
      formState.grade = props.classData.grade || ''
      formState.name = props.classData.name || ''
      formState.head_teacher_id = props.classData.head_teacher_id || ''
      formState.max_count = props.classData.max_count || 50
      formState.status = props.classData.status ?? 1
    } else {
      resetForm()
    }
  }
)

async function fetchTeacherOptions() {
  const res = await getTeacherList({ page: 1, page_size: 100 })
  teacherOptions.value = res.list.map((item) => ({
    value: item.id,
    label: `${item.name}${item.subject ? ` · ${item.subject}` : ''}`
  }))
}

function resetForm() {
  formState.grade = ''
  formState.name = ''
  formState.head_teacher_id = ''
  formState.max_count = 50
  formState.status = 1
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
      grade: formState.grade,
      name: formState.name,
      head_teacher_id: Number(formState.head_teacher_id),
      max_count: Number(formState.max_count),
      status: Number(formState.status)
    }

    if (isEdit.value) {
      await updateClass(props.classData.id, payload)
      ElMessage.success('班级信息已更新')
    } else {
      await createClass(payload)
      ElMessage.success('班级已创建')
    }

    emit('success')
    dialogVisible.value = false
  } finally {
    loading.value = false
  }
}
</script>
