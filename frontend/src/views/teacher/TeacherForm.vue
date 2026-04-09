<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑教师' : '新增教师'"
    width="620px"
    :close-on-click-modal="false"
    @closed="handleClosed"
  >
    <el-form ref="formRef" :model="formState" :rules="rules" label-width="100px">
      <el-form-item label="姓名" prop="name">
        <el-input v-model="formState.name" placeholder="请输入教师姓名" />
      </el-form-item>

      <el-form-item label="学科" prop="subject">
        <el-input v-model="formState.subject" placeholder="请输入任教学科" />
      </el-form-item>

      <el-form-item label="职务" prop="title">
        <el-radio-group v-model="formState.title">
          <el-radio label="normal">普通教师</el-radio>
          <el-radio label="head_teacher">班主任</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="绑定班级">
        <el-select
          v-model="selectedClassIds"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="请选择绑定班级"
          style="width: 100%"
        >
          <el-option
            v-for="item in classOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
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
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getClassList } from '@/api/class_'
import { createTeacher, updateTeacher } from '@/api/teacher'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  teacher: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:visible', 'success'])

const formRef = ref(null)
const dialogVisible = ref(props.visible)
const loading = ref(false)
const classOptions = ref([])
const selectedClassIds = ref([])

const isEdit = computed(() => !!props.teacher?.id)

const formState = reactive({
  name: '',
  subject: '',
  title: 'normal',
  class_ids: ''
})

const rules = {
  name: [{ required: true, message: '请输入教师姓名', trigger: 'blur' }],
  subject: [{ required: true, message: '请输入任教学科', trigger: 'blur' }],
  title: [{ required: true, message: '请选择职务', trigger: 'change' }]
}

watch(
  () => props.visible,
  async (value) => {
    dialogVisible.value = value
    if (!value) return

    await fetchClassOptions()
    if (props.teacher) {
      formState.name = props.teacher.name || ''
      formState.subject = props.teacher.subject || ''
      formState.title = props.teacher.title || 'normal'
      selectedClassIds.value = parseClassIds(props.teacher.class_ids)
    } else {
      resetForm()
    }
  }
)

function parseClassIds(value) {
  if (!value) return []
  return value
    .split(',')
    .map((item) => Number(item.trim()))
    .filter((item) => !Number.isNaN(item))
}

async function fetchClassOptions() {
  const res = await getClassList({ page: 1, page_size: 100 })
  classOptions.value = res.list.map((item) => ({
    value: item.id,
    label: item.name
  }))
}

function resetForm() {
  formState.name = ''
  formState.subject = ''
  formState.title = 'normal'
  formState.class_ids = ''
  selectedClassIds.value = []
}

function handleClosed() {
  emit('update:visible', false)
  formRef.value?.resetFields()
  resetForm()
}

async function handleSubmit() {
  await formRef.value?.validate()

  loading.value = true
  formState.class_ids = selectedClassIds.value.length
    ? selectedClassIds.value.join(',')
    : null

  try {
    if (isEdit.value) {
      await updateTeacher(props.teacher.id, { ...formState })
      ElMessage.success('教师信息已更新')
    } else {
      await createTeacher({ ...formState })
      ElMessage.success('教师已创建')
    }
    emit('success')
    dialogVisible.value = false
  } finally {
    loading.value = false
  }
}
</script>
