<template>
  <div class="page-container ai-page">
    <div class="ai-layout">
      <el-card shadow="never" class="config-card">
        <template #header>
          <div>
            <div class="card-title">AI分组分班建议</div>
            <div class="card-desc">这里保留 AI 参考能力。正式教师分组和校务分班，请前往专项管理页完成。</div>
          </div>
        </template>

        <el-form :model="form" label-width="96px">
          <el-form-item label="模式">
            <el-radio-group v-model="form.mode">
              <el-radio-button label="teacher" :disabled="userStore.role === 'admin'">教师分组建议</el-radio-button>
              <el-radio-button label="admin" :disabled="userStore.role !== 'admin'">校务分班建议</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item v-if="form.mode === 'teacher'" label="班级">
            <el-select v-model="form.class_id" clearable class="full-width" placeholder="请选择班级">
              <el-option v-for="item in classOptions" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </el-form-item>

          <el-form-item v-else label="年级">
            <el-select v-model="form.grade" class="full-width" placeholder="请选择年级">
              <el-option v-for="item in gradeOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>

          <el-form-item :label="form.mode === 'teacher' ? '分组数量' : '目标班级'">
            <template v-if="form.mode === 'teacher'">
              <el-input-number v-model="form.group_count" :min="2" :max="12" />
            </template>
            <template v-else>
              <div class="class-preview">
                <span v-if="gradeClassOptions.length">
                  {{ gradeClassOptions.map((item) => item.name).join('、') }}
                </span>
                <span v-else>当前年级暂无可用班级</span>
              </div>
            </template>
          </el-form-item>

          <el-form-item :label="form.mode === 'teacher' ? '应用场景' : '分班背景'">
            <el-input
              v-model="form.context_note"
              type="textarea"
              :rows="3"
              :placeholder="form.mode === 'teacher' ? '例如：课堂讨论、小组合作、值日安排' : '例如：新高一正式分班、插班生调整'"
            />
          </el-form-item>

          <el-form-item label="均衡因素">
            <el-checkbox-group v-model="form.balance_factors">
              <el-checkbox label="score">成绩</el-checkbox>
              <el-checkbox label="gender">性别</el-checkbox>
              <el-checkbox label="tag">标签</el-checkbox>
            </el-checkbox-group>
          </el-form-item>

          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="AI 结果仅供参考。教师请前往“教师分组管理”，管理员请前往“校务分班管理”完成正式操作。"
            class="mode-alert"
          />

          <el-form-item>
            <el-button type="primary" :loading="loading" @click="handleGenerate">生成建议</el-button>
            <el-button @click="handleOpenBusinessPage">
              前往{{ form.mode === 'teacher' ? '教师分组管理' : '校务分班管理' }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="result-card">
        <template #header>
          <div class="result-head">
            <div>
              <div class="card-title">{{ form.mode === 'teacher' ? 'AI分组建议' : 'AI分班建议' }}</div>
              <div class="card-desc">
                {{ result?.description || '生成后会展示 AI 给出的建议结果，你可以下载后再去专项管理页继续调整。' }}
              </div>
            </div>
            <el-button v-if="result?.groups?.length" link type="success" @click="handleDownload">下载 Word</el-button>
          </div>
        </template>

        <el-empty v-if="!loading && !result?.groups?.length" description="设置参数后即可生成 AI 建议" />
        <el-skeleton v-else-if="loading" :rows="6" animated />

        <div v-else class="group-list">
          <el-card
            v-for="(group, index) in result.groups"
            :key="`${group.target_class_id || 'group'}-${index}`"
            shadow="hover"
            class="group-item"
          >
            <template #header>
              <div class="group-head">
                <span>{{ form.mode === 'teacher' ? `第 ${index + 1} 组` : group.target_class_name || `第 ${index + 1} 班` }}</span>
                <span>均分 {{ group.avg_score }}</span>
              </div>
            </template>

            <div class="group-meta">
              男生 {{ group.male_count }} 人 / 女生 {{ group.female_count }} 人
            </div>

            <el-table :data="group.students" size="small" border>
              <el-table-column prop="student_no" label="学号" width="120" />
              <el-table-column prop="name" label="姓名" min-width="90" />
              <el-table-column prop="grade" label="年级" width="90" />
              <el-table-column prop="gender" label="性别" width="70">
                <template #default="{ row }">
                  {{ row.gender === 'male' ? '男' : '女' }}
                </template>
              </el-table-column>
              <el-table-column prop="avg_score" label="均分" width="80" />
              <el-table-column prop="tags" label="标签" min-width="120" show-overflow-tooltip />
            </el-table>
          </el-card>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { getAiHistoryDetail } from '@/api/aiHistory'
import { generateGroup } from '@/api/aiTools'
import { getClassList } from '@/api/class_'
import { useAiGenerate } from '@/composables/useAiGenerate'
import { useUserStore } from '@/stores/user'
import { downloadWordDocument } from '@/utils/export'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const TEACHER_GROUPING_DRAFT_KEY = 'teacher-grouping-draft'

const classOptions = ref([])

const form = reactive({
  mode: 'teacher',
  class_id: '',
  grade: '',
  group_count: 4,
  balance_factors: ['score', 'gender'],
  context_note: ''
})

const { loading, result, generate } = useAiGenerate(generateGroup)

const gradeOptions = computed(() => Array.from(new Set(classOptions.value.map((item) => item.grade).filter(Boolean))))

const gradeClassOptions = computed(() => classOptions.value.filter((item) => item.grade === form.grade))

onMounted(async () => {
  await userStore.fetchUserInfo()
  if (userStore.role === 'admin') {
    form.mode = 'admin'
  }
  await fetchClasses()
  if (gradeOptions.value.length && !form.grade) {
    form.grade = gradeOptions.value[0]
  }
  syncAdminGroupCount()
  await loadHistory(route.query.historyId)
})

watch(
  () => [form.mode, form.grade, classOptions.value.length],
  () => {
    syncAdminGroupCount()
  }
)

watch(
  () => route.query.historyId,
  async (historyId, previousId) => {
    if (historyId && historyId !== previousId) {
      await loadHistory(historyId)
    }
  }
)

async function fetchClasses() {
  const res = await getClassList({ page: 1, page_size: 100, status: 1 })
  classOptions.value = res.list || []
}

function syncAdminGroupCount() {
  if (form.mode === 'admin') {
    form.group_count = gradeClassOptions.value.length || 0
  }
}

async function handleGenerate() {
  if (!form.balance_factors.length) {
    ElMessage.warning('请至少选择一个均衡因素')
    return
  }
  if (form.mode === 'teacher' && !form.class_id) {
    ElMessage.warning('教师分组建议下请选择班级')
    return
  }
  if (form.mode === 'admin') {
    if (!form.grade) {
      ElMessage.warning('校务分班建议下请选择年级')
      return
    }
    if (!gradeClassOptions.value.length) {
      ElMessage.warning('当前年级没有可用班级，无法生成建议')
      return
    }
  }

  await generate({
    mode: form.mode,
    class_id: form.mode === 'teacher' ? form.class_id : undefined,
    grade: form.mode === 'admin' ? form.grade : undefined,
    group_count: form.mode === 'teacher' ? form.group_count : gradeClassOptions.value.length,
    balance_factors: form.balance_factors,
    scenario: form.mode === 'teacher' ? form.context_note : undefined,
    background: form.mode === 'admin' ? form.context_note : undefined
  })
}

function handleOpenBusinessPage() {
  if (form.mode === 'teacher' && result.value?.groups?.length) {
    sessionStorage.setItem(
      TEACHER_GROUPING_DRAFT_KEY,
      JSON.stringify({
        class_id: form.class_id,
        group_count: form.group_count,
        balance_factors: form.balance_factors,
        scheme_name: `${classOptions.value.find((item) => item.id === form.class_id)?.name || '班级'}-AI建议分组`,
        groups: result.value.groups,
        description: result.value.description || ''
      })
    )
  }
  router.push(form.mode === 'teacher' ? '/grouping/teacher' : '/placement/admin')
}

async function loadHistory(historyId) {
  if (!historyId) return
  const detail = await getAiHistoryDetail(Number(historyId))
  const params = detail.input_params || {}
  form.mode = params.mode || form.mode
  form.class_id = params.class_id || ''
  form.grade = params.grade || form.grade
  form.group_count = params.group_count || form.group_count
  form.balance_factors = params.balance_factors?.length ? params.balance_factors : ['score', 'gender']
  form.context_note = params.scenario || params.background || ''
  result.value = { groups: [], description: detail.content }
}

function handleDownload() {
  const body = (result.value?.groups || [])
    .map((group, index) => {
      const title = form.mode === 'teacher' ? `第 ${index + 1} 组` : group.target_class_name || `第 ${index + 1} 班`
      const students = group.students
        .map((student) => `- ${student.student_no || '-'} / ${student.name} / ${student.gender === 'male' ? '男' : '女'} / ${student.grade || '-'} / 均分 ${student.avg_score}${student.tags ? ` / ${student.tags}` : ''}`)
        .join('\n')
      return `${title}\n均分 ${group.avg_score}，男生 ${group.male_count} 人，女生 ${group.female_count} 人\n${students}`
    })
    .join('\n\n')

  downloadWordDocument(
    form.mode === 'teacher' ? 'AI教师分组建议' : 'AI校务分班建议',
    [result.value?.description || '', body].filter(Boolean).join('\n\n'),
    form.mode === 'teacher' ? 'AI教师分组建议.doc' : 'AI校务分班建议.doc'
  )
}
</script>

<style scoped lang="scss">
.ai-layout {
  display: grid;
  grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
  gap: 16px;
}

.config-card {
  align-self: start;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.card-desc {
  margin-top: 4px;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.7;
}

.full-width {
  width: 100%;
}

.class-preview {
  width: 100%;
  min-height: 40px;
  padding: 10px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  line-height: 1.7;
}

.mode-alert {
  margin-bottom: 18px;
}

.result-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.group-list {
  display: grid;
  gap: 16px;
}

.group-head {
  display: flex;
  justify-content: space-between;
  font-weight: 600;
}

.group-meta {
  margin-bottom: 12px;
  font-size: 13px;
  color: #6b7280;
}

@media (max-width: 1100px) {
  .ai-layout {
    grid-template-columns: 1fr;
  }
}
</style>
