<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑成绩' : '录入成绩'"
    width="640px"
    :close-on-click-modal="false"
    @closed="handleClosed"
  >
    <el-form ref="formRef" :model="formState" :rules="rules" label-width="100px">
      <el-form-item label="学生" prop="student_id">
        <el-select v-model="formState.student_id" placeholder="请选择学生" style="width: 100%" filterable>
          <el-option
            v-for="item in studentOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="班级" prop="class_id">
        <el-select v-model="formState.class_id" placeholder="请选择班级" style="width: 100%">
          <el-option
            v-for="item in classOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="考试批次" prop="exam_batch">
        <el-select v-model="formState.exam_batch" placeholder="请选择考试批次" style="width: 100%">
          <el-option
            v-for="item in EXAM_BATCHES"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="科目" prop="subject">
        <el-select v-model="formState.subject" placeholder="请选择科目" style="width: 100%">
          <el-option
            v-for="item in SUBJECTS"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="分数" prop="score">
        <el-input-number v-model="formState.score" :min="0" :max="100" :precision="1" style="width: 100%" />
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
import { getStudentList } from '@/api/student'
import { getClassList } from '@/api/class_'
import { createScore, updateScore } from '@/api/score'
import { EXAM_BATCHES, SUBJECTS } from '@/utils/constants'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  scoreData: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:visible', 'success'])

const formRef = ref(null)
const dialogVisible = ref(props.visible)
const loading = ref(false)
const studentOptions = ref([])
const classOptions = ref([])

const isEdit = computed(() => !!props.scoreData?.id)

const formState = reactive({
  student_id: null,
  class_id: null,
  exam_batch: '',
  subject: '',
  score: null
})

const rules = {
  student_id: [{ required: true, message: '请选择学生', trigger: 'change' }],
  class_id: [{ required: true, message: '请选择班级', trigger: 'change' }],
  exam_batch: [{ required: true, message: '请选择考试批次', trigger: 'change' }],
  subject: [{ required: true, message: '请选择科目', trigger: 'change' }],
  score: [{ required: true, message: '请输入分数', trigger: 'blur' }]
}

watch(
  () => props.visible,
  async (value) => {
    dialogVisible.value = value
    if (!value) return
    await Promise.all([fetchStudents(), fetchClasses()])
    if (props.scoreData) {
      Object.assign(formState, {
        student_id: props.scoreData.student_id,
        class_id: props.scoreData.class_id,
        exam_batch: props.scoreData.exam_batch,
        subject: props.scoreData.subject,
        score: props.scoreData.score
      })
    } else {
      resetForm()
    }
  }
)

async function fetchStudents() {
  const res = await getStudentList({ page: 1, page_size: 100 })
  studentOptions.value = res.list.map((item) => ({
    value: item.id,
    label: `${item.student_no} - ${item.name}`
  }))
}

async function fetchClasses() {
  const res = await getClassList({ page: 1, page_size: 100 })
  classOptions.value = res.list.map((item) => ({
    value: item.id,
    label: item.name
  }))
}

function resetForm() {
  formState.student_id = null
  formState.class_id = null
  formState.exam_batch = ''
  formState.subject = ''
  formState.score = null
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
    if (isEdit.value) {
      await updateScore(props.scoreData.id, { ...formState })
      ElMessage.success('成绩已更新')
    } else {
      await createScore({ ...formState })
      ElMessage.success('成绩录入成功')
    }
    dialogVisible.value = false
    emit('success')
  } finally {
    loading.value = false
  }
}
</script>
