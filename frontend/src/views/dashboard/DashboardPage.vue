<template>
  <div class="dashboard-page" :style="dashboardVars">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="hero-badge">{{ currentUi.dashboard.heroBadge }}</span>
        <h1 class="hero-title">{{ currentUi.dashboard.heroTitle }}</h1>
        <p class="hero-text">{{ currentUi.dashboard.heroText }}</p>

        <div class="hero-actions">
          <button
            v-for="item in currentUi.dashboard.shortcuts"
            :key="item.path"
            type="button"
            class="shortcut-pill"
            @click="goTo(item.path)"
          >
            <strong>{{ item.title }}</strong>
            <span>{{ item.description }}</span>
          </button>
        </div>
      </div>

      <div class="hero-panel">
        <div class="hero-panel-title">当前账号</div>
        <div class="hero-user-name">{{ userStore.name || userStore.username || '欢迎使用' }}</div>
        <div class="hero-user-role">{{ currentUi.name }}端 · 今日概览</div>
        <div class="hero-user-stats">
          <div v-for="item in metrics" :key="item.label" class="metric-mini">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </div>
    </section>

    <section class="metrics-grid">
      <article v-for="item in metrics" :key="item.label" class="metric-card">
        <div class="metric-icon">{{ item.icon }}</div>
        <div class="metric-copy">
          <span class="metric-label">{{ item.label }}</span>
          <strong class="metric-value">{{ item.value }}</strong>
          <p class="metric-desc">{{ item.description }}</p>
        </div>
      </article>
    </section>

    <section class="content-grid">
      <article class="dashboard-card">
        <header class="card-head">
          <div>
            <span class="card-kicker">重点信息</span>
            <h2>{{ currentUi.dashboard.noticeTitle }}</h2>
          </div>
        </header>
        <div class="feed-list">
          <div v-for="item in primaryFeed" :key="item.title" class="feed-item">
            <span class="feed-badge">{{ item.tag }}</span>
            <div>
              <h3>{{ item.title }}</h3>
              <p>{{ item.content }}</p>
            </div>
          </div>
        </div>
      </article>

      <article class="dashboard-card">
        <header class="card-head">
          <div>
            <span class="card-kicker">工作安排</span>
            <h2>{{ currentUi.dashboard.secondaryTitle }}</h2>
          </div>
        </header>
        <div class="agenda-list">
          <div v-for="item in secondaryFeed" :key="item.title" class="agenda-item">
            <strong>{{ item.time }}</strong>
            <div>
              <h3>{{ item.title }}</h3>
              <p>{{ item.content }}</p>
            </div>
          </div>
        </div>
      </article>
    </section>

    <section class="insight-grid">
      <article class="dashboard-card chart-card">
        <header class="card-head">
          <div>
            <span class="card-kicker">统计摘要</span>
            <h2>成绩概览</h2>
          </div>
        </header>
        <div v-if="scoreStats.length > 0" class="score-summary">
          <div v-for="item in scoreStats" :key="item.subject" class="score-stat">
            <div class="score-subject">{{ item.subject }}</div>
            <div class="score-values">
              <span>平均 {{ item.average }}</span>
              <span>最高 {{ item.maximum }}</span>
              <span>最低 {{ item.minimum }}</span>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无成绩统计数据" />
      </article>

      <article class="dashboard-card table-card">
        <header class="card-head">
          <div>
            <span class="card-kicker">最近动态</span>
            <h2>{{ tableTitle }}</h2>
          </div>
        </header>
        <el-table
          v-if="tableRows.length > 0"
          :data="tableRows"
          size="small"
          stripe
          class="dashboard-table"
        >
          <el-table-column
            v-for="column in tableColumns"
            :key="column.prop"
            :prop="column.prop"
            :label="column.label"
            :min-width="column.width"
            show-overflow-tooltip
          />
        </el-table>
        <el-empty v-else description="暂无可展示数据" />
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getClassList } from '@/api/class_'
import { getScoreList, getScoreStats } from '@/api/score'
import { getStudentList } from '@/api/student'
import { getTeacherList } from '@/api/teacher'
import { useUserStore } from '@/stores/user'
import { getRoleUi } from '@/utils/role-ui'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const metrics = ref([])
const scoreStats = ref([])
const tableRows = ref([])
const tableTitle = ref('最新记录')
const tableColumns = ref([])
const primaryFeed = ref([])
const secondaryFeed = ref([])

const currentRole = computed(() => userStore.role || 'student')
const currentUi = computed(() => getRoleUi(currentRole.value))

const dashboardVars = computed(() => ({
  '--dash-primary': currentUi.value.palette.primary,
  '--dash-secondary': currentUi.value.palette.secondary,
  '--dash-soft': currentUi.value.palette.soft,
  '--dash-text': currentUi.value.palette.text
}))

onMounted(() => {
  loadDashboard()
})

watch(currentRole, () => {
  loadDashboard()
})

async function loadDashboard() {
  if (loading.value) return
  loading.value = true

  try {
    if (currentRole.value === 'admin') {
      await loadAdminDashboard()
    } else if (currentRole.value === 'teacher') {
      await loadTeacherDashboard()
    } else {
      await loadStudentDashboard()
    }
  } catch (error) {
    ElMessage.warning('首页数据加载部分失败，已展示基础内容')
    applyFallbackData()
  } finally {
    loading.value = false
  }
}

async function loadStudentDashboard() {
  const [scoreListRes, statsRes] = await Promise.all([
    getScoreList({ page: 1, page_size: 6 }),
    getScoreStats({})
  ])

  scoreStats.value = statsRes || []
  tableTitle.value = '我的近期成绩'
  tableColumns.value = [
    { prop: 'subject', label: '科目', width: 120 },
    { prop: 'exam_batch', label: '考试批次', width: 140 },
    { prop: 'score', label: '分数', width: 90 }
  ]
  tableRows.value = (scoreListRes.list || []).slice(0, 6)

  const averageScore = scoreStats.value.length > 0
    ? Math.round(scoreStats.value.reduce((sum, item) => sum + Number(item.average || 0), 0) / scoreStats.value.length)
    : '--'

  metrics.value = [
    { icon: '📘', label: '近期成绩条目', value: scoreListRes.total || 0, description: '查看个人全部成绩记录' },
    { icon: '🎯', label: '平均分', value: averageScore, description: '来自当前可见科目统计' },
    { icon: '🤖', label: 'AI 学习入口', value: 2, description: '校规问答与模拟面试已就绪' }
  ]

  primaryFeed.value = [
    { tag: '通知', title: '本周关注学习节奏', content: '建议优先复盘最近成绩波动较大的科目，并结合 AI 学习工具进行针对性练习。' },
    { tag: '提醒', title: '保持课后整理', content: '成绩页和 AI 工具页已经联通，课后遇到疑问可以直接进入问答或面试练习。' },
    { tag: '校园', title: '校规助手可直接使用', content: '关于手机管理、请假流程、日常行为规范的问题，现在都可以在校规问答里快速查询。' }
  ]

  secondaryFeed.value = [
    { time: '08:00', title: '晨读与作业确认', content: '优先检查当天学习任务，明确需要补强的科目。' },
    { time: '14:30', title: '查看最近一次考试得分', content: '复盘低于预期的科目，整理错题原因。' },
    { time: '20:00', title: 'AI 模拟练习', content: '使用模拟面试或校规问答做 10 分钟轻量训练。' }
  ]
}

async function loadTeacherDashboard() {
  const [studentRes, classRes, scoreRes, statsRes] = await Promise.all([
    getStudentList({ page: 1, page_size: 5 }),
    getClassList({ page: 1, page_size: 50 }),
    getScoreList({ page: 1, page_size: 6 }),
    getScoreStats({})
  ])

  scoreStats.value = statsRes || []
  tableTitle.value = '近期成绩录入'
  tableColumns.value = [
    { prop: 'student_name', label: '学生', width: 120 },
    { prop: 'class_name', label: '班级', width: 140 },
    { prop: 'subject', label: '科目', width: 120 },
    { prop: 'score', label: '分数', width: 90 }
  ]
  tableRows.value = (scoreRes.list || []).slice(0, 6)

  metrics.value = [
    { icon: '👥', label: '可管理学生', value: studentRes.total || 0, description: '当前权限范围内学生总数' },
    { icon: '🏫', label: '班级数量', value: classRes.total || 0, description: '可查看班级与教学组织情况' },
    { icon: '📝', label: '成绩记录', value: scoreRes.total || 0, description: '近期录入与查看的成绩数据' }
  ]

  primaryFeed.value = [
    { tag: '班级', title: '优先处理成绩异常学生', content: '首页会先展示最近成绩记录，建议结合成绩统计与学生管理页同步查看。' },
    { tag: '教学', title: 'AI 教学工具随手可达', content: '评语生成、公告润色和班会策划都已接到统一入口，适合高频日常使用。' },
    { tag: '提醒', title: '班级任务建议集中处理', content: '把学生管理、班级管理与成绩录入串成一条主流程，会比逐页跳转更顺。' }
  ]

  secondaryFeed.value = [
    { time: '09:00', title: '班级出勤与状态确认', content: '先看学生标签与重点关注对象，避免遗漏异常情况。' },
    { time: '13:30', title: '成绩录入与波动诊断', content: '利用成绩管理和 AI 诊断查看班级整体走势。' },
    { time: '16:40', title: '班会与通知准备', content: '公告润色、班会策划等 AI 工具可直接从首页快捷进入。' }
  ]
}

async function loadAdminDashboard() {
  const [studentRes, classRes, teacherRes, scoreRes, statsRes] = await Promise.all([
    getStudentList({ page: 1, page_size: 5 }),
    getClassList({ page: 1, page_size: 50 }),
    getTeacherList({ page: 1, page_size: 5 }),
    getScoreList({ page: 1, page_size: 6 }),
    getScoreStats({})
  ])

  scoreStats.value = statsRes || []
  tableTitle.value = '最近教学数据'
  tableColumns.value = [
    { prop: 'student_name', label: '学生', width: 110 },
    { prop: 'class_name', label: '班级', width: 130 },
    { prop: 'exam_batch', label: '考试批次', width: 140 },
    { prop: 'score', label: '分数', width: 90 }
  ]
  tableRows.value = (scoreRes.list || []).slice(0, 6)

  metrics.value = [
    { icon: '🎓', label: '学生总数', value: studentRes.total || 0, description: '全校学生规模概览' },
    { icon: '👔', label: '教师总数', value: teacherRes.total || 0, description: '教师与岗位配置情况' },
    { icon: '🏢', label: '班级总数', value: classRes.total || 0, description: '班级结构与编制概览' }
  ]

  primaryFeed.value = [
    { tag: '运营', title: '全校运行状态集中展示', content: '管理员首页优先展示学生、教师、班级和成绩数据，便于快速掌握学校运行情况。' },
    { tag: '制度', title: '校规管理与 AI 答疑联动', content: '校规维护后可直接影响校规问答结果，建议定期更新制度条目。' },
    { tag: '治理', title: '建议按人员、班级、成绩三条主线查看', content: '这样可以更快定位问题，并避免在多模块之间来回切换。' }
  ]

  secondaryFeed.value = [
    { time: '08:30', title: '检查全校数据概览', content: '先浏览学生、教师、班级规模，确认数据同步情况。' },
    { time: '11:00', title: '查看近期成绩样本', content: '从成绩摘要观察是否存在明显波动或异常分布。' },
    { time: '15:30', title: '维护制度与权限模块', content: '根据学校事务安排调整校规与管理配置。' }
  ]
}

function applyFallbackData() {
  metrics.value = [
    { icon: '📌', label: '工作台状态', value: '可用', description: '基础界面已经加载，可以继续操作其他模块。' },
    { icon: '🧭', label: '导航状态', value: '正常', description: '侧边栏和路由已经按角色收敛。' },
    { icon: '🧩', label: '页面状态', value: '稳定', description: '即使接口异常也不会再出现空白页。' }
  ]
  scoreStats.value = []
  tableRows.value = []
  tableColumns.value = []
  tableTitle.value = '暂无数据'
  primaryFeed.value = [
    { tag: '提示', title: '数据接口暂时不可用', content: '前端已经降级展示基础信息，你仍然可以继续访问其他页面。' }
  ]
  secondaryFeed.value = [
    { time: '现在', title: '检查网络或接口状态', content: '如果后端接口恢复，刷新页面即可重新拉取数据。' }
  ]
}

function goTo(path) {
  router.push(path)
}
</script>

<style scoped lang="scss">
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.7fr);
  gap: 20px;
  padding: 28px;
  border-radius: 28px;
  background:
    radial-gradient(circle at top left, rgba(255, 255, 255, 0.84), transparent 28%),
    linear-gradient(135deg, color-mix(in srgb, var(--dash-primary) 10%, white), #ffffff 70%);
  box-shadow: 0 24px 48px rgba(30, 61, 98, 0.08);
}

.hero-badge,
.card-kicker {
  display: inline-flex;
  padding: 8px 14px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--dash-primary) 14%, white);
  color: var(--dash-primary);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.hero-title {
  margin-top: 18px;
  color: var(--dash-text);
  font-size: clamp(28px, 3vw, 40px);
  line-height: 1.18;
}

.hero-text {
  margin-top: 12px;
  max-width: 720px;
  color: rgba(39, 60, 88, 0.74);
  line-height: 1.8;
}

.hero-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin-top: 22px;
}

.shortcut-pill {
  padding: 16px;
  border: 1px solid rgba(122, 144, 175, 0.14);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.82);
  cursor: pointer;
  text-align: left;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease;

  strong,
  span {
    display: block;
  }

  strong {
    color: var(--dash-text);
    font-size: 15px;
  }

  span {
    margin-top: 8px;
    color: rgba(39, 60, 88, 0.64);
    line-height: 1.6;
    font-size: 13px;
  }

  &:hover {
    transform: translateY(-3px);
    border-color: color-mix(in srgb, var(--dash-primary) 24%, white);
    box-shadow: 0 18px 34px color-mix(in srgb, var(--dash-primary) 12%, transparent);
  }
}

.hero-panel,
.dashboard-card,
.metric-card {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(122, 144, 175, 0.12);
  box-shadow: 0 22px 44px rgba(30, 61, 98, 0.06);
}

.hero-panel {
  padding: 22px;
  border-radius: 24px;
}

.hero-panel-title {
  color: rgba(39, 60, 88, 0.56);
  font-size: 13px;
  font-weight: 700;
}

.hero-user-name {
  margin-top: 14px;
  color: var(--dash-text);
  font-size: 30px;
  font-weight: 700;
}

.hero-user-role {
  margin-top: 8px;
  color: rgba(39, 60, 88, 0.6);
}

.hero-user-stats {
  display: grid;
  gap: 12px;
  margin-top: 20px;
}

.metric-mini {
  padding: 14px 16px;
  border-radius: 18px;
  background: color-mix(in srgb, var(--dash-primary) 8%, white);

  span,
  strong {
    display: block;
  }

  span {
    color: rgba(39, 60, 88, 0.56);
    font-size: 12px;
  }

  strong {
    margin-top: 8px;
    color: var(--dash-text);
    font-size: 24px;
  }
}

.metrics-grid,
.content-grid,
.insight-grid {
  display: grid;
  gap: 20px;
}

.metrics-grid {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.metric-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 22px;
  border-radius: 24px;
}

.metric-icon {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  border-radius: 18px;
  background: color-mix(in srgb, var(--dash-primary) 14%, white);
  font-size: 26px;
}

.metric-label,
.metric-value,
.metric-desc {
  display: block;
}

.metric-label {
  color: rgba(39, 60, 88, 0.6);
  font-size: 13px;
}

.metric-value {
  margin-top: 8px;
  color: var(--dash-text);
  font-size: 30px;
}

.metric-desc {
  margin-top: 10px;
  color: rgba(39, 60, 88, 0.58);
  line-height: 1.7;
  font-size: 13px;
}

.content-grid,
.insight-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.dashboard-card {
  padding: 22px;
  border-radius: 24px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;

  h2 {
    margin-top: 10px;
    color: var(--dash-text);
    font-size: 24px;
  }
}

.feed-list,
.agenda-list,
.score-summary {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.feed-item,
.agenda-item,
.score-stat {
  display: flex;
  gap: 14px;
  padding: 16px;
  border-radius: 20px;
  background: color-mix(in srgb, var(--dash-primary) 6%, white);
}

.feed-badge {
  min-width: 54px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: color-mix(in srgb, var(--dash-primary) 14%, white);
  color: var(--dash-primary);
  font-size: 12px;
  font-weight: 700;
}

.feed-item h3,
.agenda-item h3,
.score-subject {
  color: var(--dash-text);
  font-size: 16px;
}

.feed-item p,
.agenda-item p,
.score-values {
  margin-top: 8px;
  color: rgba(39, 60, 88, 0.62);
  line-height: 1.7;
}

.agenda-item strong {
  min-width: 62px;
  color: var(--dash-primary);
  font-size: 15px;
}

.score-values {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.dashboard-table {
  :deep(.el-table__inner-wrapper::before) {
    display: none;
  }
}

@media (max-width: 1100px) {
  .hero-card,
  .content-grid,
  .insight-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-card,
  .metric-card,
  .dashboard-card {
    padding: 18px;
    border-radius: 22px;
  }

  .hero-actions,
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
