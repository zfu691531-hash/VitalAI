<template>
  <div class="page-container profile-page">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="基本信息" name="profile">
        <el-card shadow="never">
          <el-form ref="profileFormRef" :model="profileForm" label-width="100px" class="profile-form">
            <el-form-item label="账号">
              <el-input :model-value="userStore.username" disabled />
            </el-form-item>
            <el-form-item label="角色">
              <el-input :model-value="userStore.role" disabled />
            </el-form-item>
            <el-form-item label="姓名">
              <el-input v-model="profileForm.name" placeholder="请输入姓名" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="profileLoading" @click="handleUpdateProfile">
                保存基本信息
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never" class="password-card">
          <template #header>修改密码</template>
          <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="100px">
            <el-form-item label="旧密码" prop="old_password">
              <el-input v-model="passwordForm.old_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input v-model="passwordForm.new_password" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="passwordLoading" @click="handleChangePassword">
                更新密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="AI 生成历史" name="history">
        <AiHistoryList
          :history-list="historyList"
          :loading="historyLoading"
          @view="handleViewHistory"
          @reuse="handleReuseHistory"
          @delete="handleDeleteHistory"
        />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="historyDetailVisible" title="AI 历史详情" width="760px">
      <pre class="history-content">{{ selectedHistory?.content || '' }}</pre>
    </el-dialog>

    <ConfirmDialog
      v-model:visible="deleteVisible"
      title="删除确认"
      :message="deleteMessage"
      confirm-type="danger"
      confirm-text="删除"
      :loading="deleteLoading"
      @confirm="confirmDeleteHistory"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { changePassword, updateUserInfo } from '@/api/user'
import { batchDeleteAiHistory, getAiHistoryDetail, getAiHistoryList } from '@/api/aiHistory'
import AiHistoryList from '@/components/ai/AiHistoryList.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const userStore = useUserStore()
const router = useRouter()

const activeTab = ref('profile')
const profileFormRef = ref(null)
const passwordFormRef = ref(null)
const profileLoading = ref(false)
const passwordLoading = ref(false)
const historyLoading = ref(false)
const historyList = ref([])
const historyDetailVisible = ref(false)
const selectedHistory = ref(null)
const deleteVisible = ref(false)
const deleteLoading = ref(false)
const deleteTargetId = ref(null)
const deleteMessage = ref('')

const profileForm = reactive({
  name: ''
})

const passwordForm = reactive({
  old_password: '',
  new_password: ''
})

const passwordRules = {
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '新密码至少 6 位', trigger: 'blur' }
  ]
}

onMounted(async () => {
  await userStore.fetchUserInfo()
  profileForm.name = userStore.name
  await fetchHistory()
})

async function fetchHistory() {
  historyLoading.value = true
  try {
    const res = await getAiHistoryList({ page: 1, page_size: 20 })
    historyList.value = res.list
  } finally {
    historyLoading.value = false
  }
}

async function handleUpdateProfile() {
  profileLoading.value = true
  try {
    await updateUserInfo({ name: profileForm.name })
    await userStore.fetchUserInfo()
    ElMessage.success('基本信息已更新')
  } finally {
    profileLoading.value = false
  }
}

async function handleChangePassword() {
  await passwordFormRef.value?.validate()
  passwordLoading.value = true
  try {
    await changePassword({ ...passwordForm })
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    ElMessage.success('密码修改成功')
  } finally {
    passwordLoading.value = false
  }
}

async function handleViewHistory(item) {
  const detail = await getAiHistoryDetail(item.id)
  selectedHistory.value = detail
  historyDetailVisible.value = true
}

function handleReuseHistory(item) {
  const routeMap = {
    comment: '/ai/comment',
    discipline: '/ai/discipline',
    notice: '/ai/notice',
    rule_qa: '/ai/rule',
    score_diag: '/ai/diagnosis',
    meeting: '/ai/meeting',
    interview: '/ai/interview',
    group: '/ai/group'
  }
  const target = routeMap[item.tool_type]

  if (!target) {
    ElMessage.warning('该历史记录暂不支持直接复用')
    return
  }

  router.push({
    path: target,
    query: { historyId: item.id }
  })
}

function handleDeleteHistory(id) {
  deleteTargetId.value = id
  deleteMessage.value = '确定删除这条 AI 历史记录吗？删除后不可恢复。'
  deleteVisible.value = true
}

async function confirmDeleteHistory() {
  deleteLoading.value = true
  try {
    await batchDeleteAiHistory([deleteTargetId.value])
    deleteVisible.value = false
    ElMessage.success('删除成功')
    await fetchHistory()
  } finally {
    deleteLoading.value = false
  }
}
</script>

<style scoped lang="scss">
.profile-form,
.password-card {
  max-width: 720px;
}

.password-card {
  margin-top: 16px;
}

.history-content {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  line-height: 1.7;
}
</style>
