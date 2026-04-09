<template>
  <div class="login-page" :style="pageVars">
    <section class="login-hero">
      <div class="hero-overlay"></div>
      <div class="hero-copy">
        <span class="hero-eyebrow">{{ currentTheme.login.eyebrow }}</span>
        <h1 class="hero-title">{{ currentTheme.login.title }}</h1>
        <p class="hero-subtitle">{{ currentTheme.login.subtitle }}</p>

        <div class="hero-highlights">
          <div v-for="item in currentTheme.login.highlights" :key="item" class="highlight-chip">
            {{ item }}
          </div>
        </div>
      </div>

      <div class="hero-visual" :class="`hero-visual--${activeRole}`">
        <div class="visual-card visual-card--main">
          <span class="visual-label">校园主视觉</span>
          <h2>{{ currentTheme.login.visualTitle }}</h2>
          <p>{{ currentTheme.login.visualSubtitle }}</p>
        </div>
        <div class="visual-card visual-card--floating">
          <div class="floating-row">
            <span class="floating-dot"></span>
            <span>智慧教务</span>
          </div>
          <div class="floating-row">
            <span class="floating-dot"></span>
            <span>角色体验联动</span>
          </div>
          <div class="floating-row">
            <span class="floating-dot"></span>
            <span>页面响应式适配</span>
          </div>
        </div>
        <div class="campus-stage">
          <div class="building building-a"></div>
          <div class="building building-b"></div>
          <div class="building building-c"></div>
          <div class="stage-ground"></div>
        </div>
      </div>
    </section>

    <section class="login-panel">
      <div class="login-card">
        <div class="login-header">
          <img src="@/assets/logo.svg" alt="logo" class="logo" />
          <div>
            <p class="panel-kicker">校园AI教务助手</p>
            <h2 class="panel-title">{{ currentTheme.name }}端登录</h2>
          </div>
        </div>

        <div class="role-tabs" role="tablist" aria-label="登录角色">
          <button
            v-for="role in roleList"
            :key="role.value"
            type="button"
            class="role-tab"
            :class="{ active: activeRole === role.value }"
            @click="handleRoleChange(role.value)"
          >
            <span class="tab-title">{{ role.label }}</span>
            <span class="tab-desc">{{ role.desc }}</span>
          </button>
        </div>

        <el-form
          ref="formRef"
          :model="formState"
          :rules="rules"
          class="login-form"
          @keyup.enter="handleLogin"
        >
          <el-form-item prop="username">
            <el-input
              v-model="formState.username"
              size="large"
              placeholder="请输入账号"
              :prefix-icon="User"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="formState.password"
              size="large"
              :type="showPassword ? 'text' : 'password'"
              placeholder="请输入密码"
              :prefix-icon="Lock"
            >
              <template #suffix>
                <el-icon class="password-toggle" @click="showPassword = !showPassword">
                  <View v-if="showPassword" />
                  <Hide v-else />
                </el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              class="login-button"
              :loading="loading"
              @click="handleLogin"
            >
              {{ loading ? '正在登录...' : `进入${currentTheme.name}工作台` }}
            </el-button>
          </el-form-item>
        </el-form>

        <div class="test-accounts">
          <div class="test-head">
            <span>测试账号</span>
            <button type="button" class="fill-button" @click="fillCurrentRoleAccount">自动填入</button>
          </div>
          <div class="test-list">
            <p v-for="role in roleList" :key="role.value">
              <strong>{{ role.label }}</strong>
              <span>{{ roleAccounts[role.value].username }} / {{ roleAccounts[role.value].password }}</span>
            </p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Hide, Lock, User, View } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { ROLE_TEST_ACCOUNTS, ROLE_UI, getRoleHome } from '@/utils/role-ui'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const showPassword = ref(false)
const activeRole = ref('student')

const roleList = [
  { value: 'student', label: '学生', desc: '轻松学习' },
  { value: 'teacher', label: '教师', desc: '高效教学' },
  { value: 'admin', label: '管理员', desc: '稳定管理' }
]

const formState = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 位', trigger: 'blur' }
  ]
}

const roleAccounts = ROLE_TEST_ACCOUNTS

const currentTheme = computed(() => ROLE_UI[activeRole.value])

const pageVars = computed(() => ({
  '--page-bg-start': currentTheme.value.palette.soft,
  '--page-bg-end': currentTheme.value.palette.surface,
  '--brand-primary': currentTheme.value.palette.primary,
  '--brand-secondary': currentTheme.value.palette.secondary,
  '--brand-text': currentTheme.value.palette.text
}))

fillCurrentRoleAccount()

function fillCurrentRoleAccount() {
  const account = roleAccounts[activeRole.value]
  if (!account) return
  formState.username = account.username
  formState.password = account.password
}

function handleRoleChange(role) {
  activeRole.value = role
  showPassword.value = false
  fillCurrentRoleAccount()
}

async function handleLogin() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true

  try {
    await userStore.login(formState.username, formState.password)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    ElMessage.success('登录成功')
    await router.replace(redirect || getRoleHome(userStore.role))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.75fr);
  background:
    radial-gradient(circle at top left, rgba(255, 255, 255, 0.75), transparent 28%),
    linear-gradient(135deg, var(--page-bg-start) 0%, var(--page-bg-end) 100%);
}

.login-hero {
  position: relative;
  overflow: hidden;
  padding: 56px 56px 48px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background:
    linear-gradient(155deg, rgba(255, 255, 255, 0.36), rgba(255, 255, 255, 0.08)),
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 18%, white), transparent 65%);
}

.hero-overlay {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 24%, rgba(255, 255, 255, 0.55), transparent 28%),
    radial-gradient(circle at 82% 18%, rgba(255, 255, 255, 0.42), transparent 22%);
  pointer-events: none;
}

.hero-copy,
.hero-visual {
  position: relative;
  z-index: 1;
}

.hero-eyebrow {
  display: inline-flex;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.64);
  color: var(--brand-text);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.hero-title {
  max-width: 680px;
  margin-top: 24px;
  font-size: clamp(34px, 4vw, 56px);
  line-height: 1.08;
  color: var(--brand-text);
}

.hero-subtitle {
  max-width: 620px;
  margin-top: 18px;
  font-size: 17px;
  line-height: 1.8;
  color: rgba(40, 65, 99, 0.76);
}

.hero-highlights {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}

.highlight-chip {
  padding: 10px 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 12px 28px rgba(27, 57, 98, 0.08);
  color: var(--brand-text);
  font-size: 14px;
  font-weight: 600;
}

.hero-visual {
  position: relative;
  min-height: 360px;
  margin-top: 32px;
  border-radius: 32px;
  overflow: hidden;
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.26)),
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 18%, white), color-mix(in srgb, var(--brand-secondary) 30%, white));
  box-shadow: 0 30px 70px rgba(26, 56, 92, 0.14);
}

.visual-card {
  position: absolute;
  backdrop-filter: blur(14px);
  border: 1px solid rgba(255, 255, 255, 0.55);
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 24px 50px rgba(27, 57, 98, 0.12);
}

.visual-card--main {
  top: 34px;
  left: 34px;
  width: min(420px, calc(100% - 68px));
  padding: 28px;
  border-radius: 28px;

  h2 {
    margin-top: 14px;
    font-size: 30px;
    line-height: 1.2;
    color: var(--brand-text);
  }

  p {
    margin-top: 10px;
    color: rgba(32, 53, 84, 0.72);
    line-height: 1.8;
  }
}

.visual-label {
  display: inline-flex;
  padding: 6px 12px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--brand-primary) 16%, white);
  color: var(--brand-primary);
  font-size: 12px;
  font-weight: 700;
}

.visual-card--floating {
  right: 28px;
  top: 58px;
  width: 220px;
  padding: 20px;
  border-radius: 22px;
}

.floating-row {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--brand-text);
  font-size: 14px;
  font-weight: 600;

  & + .floating-row {
    margin-top: 12px;
  }
}

.floating-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary));
}

.campus-stage {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 190px;
}

.building {
  position: absolute;
  bottom: 42px;
  border-radius: 24px 24px 0 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.54));
  border: 1px solid rgba(255, 255, 255, 0.55);
}

.building::after {
  content: '';
  position: absolute;
  inset: 16px;
  border-radius: 18px 18px 0 0;
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.72) 10%, transparent 10%, transparent 22%, rgba(255, 255, 255, 0.72) 22%, rgba(255, 255, 255, 0.72) 32%, transparent 32%),
    linear-gradient(180deg, rgba(151, 182, 226, 0.32), rgba(151, 182, 226, 0.1));
}

.building-a {
  left: 10%;
  width: 180px;
  height: 120px;
}

.building-b {
  left: 34%;
  width: 240px;
  height: 146px;
}

.building-c {
  right: 10%;
  width: 160px;
  height: 110px;
}

.stage-ground {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 72px;
  background:
    radial-gradient(circle at center, rgba(255, 255, 255, 0.48), transparent 54%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0.7));
}

.hero-visual--student .stage-ground {
  background:
    radial-gradient(circle at center, rgba(255, 255, 255, 0.52), transparent 56%),
    linear-gradient(180deg, rgba(255, 214, 230, 0.12), rgba(255, 255, 255, 0.72));
}

.hero-visual--teacher .stage-ground {
  background:
    radial-gradient(circle at center, rgba(255, 255, 255, 0.52), transparent 56%),
    linear-gradient(180deg, rgba(128, 222, 198, 0.1), rgba(255, 255, 255, 0.72));
}

.hero-visual--admin .stage-ground {
  background:
    radial-gradient(circle at center, rgba(255, 255, 255, 0.42), transparent 56%),
    linear-gradient(180deg, rgba(93, 122, 165, 0.12), rgba(255, 255, 255, 0.74));
}

.login-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}

.login-card {
  width: min(460px, 100%);
  padding: 36px;
  border-radius: 32px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 28px 70px rgba(26, 56, 92, 0.14);
  backdrop-filter: blur(16px);
}

.login-header {
  display: flex;
  align-items: center;
  gap: 16px;

  .logo {
    width: 58px;
    height: 58px;
    padding: 10px;
    border-radius: 18px;
    background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary));
    box-shadow: 0 18px 34px color-mix(in srgb, var(--brand-primary) 24%, transparent);
  }
}

.panel-kicker {
  color: var(--brand-primary);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.panel-title {
  margin-top: 8px;
  color: var(--brand-text);
  font-size: 30px;
}

.role-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 28px;
}

.role-tab {
  padding: 16px 14px;
  border: 1px solid rgba(130, 150, 180, 0.16);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.82);
  cursor: pointer;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease,
    background-color 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 16px 30px rgba(27, 57, 98, 0.08);
  }

  &.active {
    border-color: color-mix(in srgb, var(--brand-primary) 24%, white);
    background: color-mix(in srgb, var(--brand-primary) 10%, white);
    box-shadow: 0 18px 34px color-mix(in srgb, var(--brand-primary) 14%, transparent);
  }
}

.tab-title,
.tab-desc {
  display: block;
  text-align: left;
}

.tab-title {
  color: var(--brand-text);
  font-weight: 700;
}

.tab-desc {
  margin-top: 6px;
  color: rgba(40, 65, 99, 0.56);
  font-size: 12px;
}

.login-form {
  margin-top: 28px;

  :deep(.el-input__wrapper) {
    min-height: 48px;
    border-radius: 16px;
    box-shadow: 0 0 0 1px rgba(129, 150, 180, 0.14) inset;
  }

  :deep(.el-input__wrapper.is-focus) {
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--brand-primary) 28%, transparent) inset;
  }
}

.password-toggle {
  cursor: pointer;
  color: rgba(40, 65, 99, 0.48);
}

.login-button {
  width: 100%;
  min-height: 50px;
  border: none;
  border-radius: 18px;
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary));
  box-shadow: 0 18px 36px color-mix(in srgb, var(--brand-primary) 22%, transparent);
  font-size: 16px;
  font-weight: 700;
}

.test-accounts {
  margin-top: 24px;
  padding: 18px;
  border-radius: 22px;
  background: color-mix(in srgb, var(--brand-primary) 7%, white);
  border: 1px solid rgba(130, 150, 180, 0.14);
}

.test-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--brand-text);
  font-weight: 700;
}

.fill-button {
  border: none;
  background: transparent;
  color: var(--brand-primary);
  cursor: pointer;
  font-weight: 700;
}

.test-list {
  margin-top: 12px;

  p {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: rgba(40, 65, 99, 0.72);
    font-size: 13px;
    line-height: 1.8;
  }

  span {
    font-family: 'Consolas', 'Courier New', monospace;
  }
}

@media (max-width: 1180px) {
  .login-page {
    grid-template-columns: 1fr;
  }

  .login-hero {
    min-height: 520px;
  }

  .login-panel {
    padding-top: 0;
    padding-bottom: 40px;
  }
}

@media (max-width: 768px) {
  .login-hero {
    padding: 28px 22px 20px;
  }

  .login-panel {
    padding: 18px 16px 28px;
  }

  .login-card {
    padding: 24px 18px;
    border-radius: 24px;
  }

  .role-tabs {
    grid-template-columns: 1fr;
  }

  .hero-visual {
    min-height: 300px;
  }

  .visual-card--main,
  .visual-card--floating {
    position: static;
    width: auto;
    margin: 18px;
  }

  .visual-card--main {
    margin-bottom: 0;
  }

  .campus-stage {
    height: 130px;
  }

  .building-a,
  .building-c {
    width: 100px;
  }

  .building-b {
    width: 140px;
  }

  .test-list p {
    flex-direction: column;
    gap: 2px;
  }
}
</style>
