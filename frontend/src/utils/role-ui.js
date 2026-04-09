import { ROLES } from './constants'

export const ROLE_TEST_ACCOUNTS = {
  [ROLES.STUDENT]: { username: 'stu_2024001', password: 'student123' },
  [ROLES.TEACHER]: { username: 'wang_math', password: 'teacher123' },
  [ROLES.ADMIN]: { username: 'admin', password: 'admin123' }
}

export const ROLE_UI = {
  [ROLES.STUDENT]: {
    name: '学生',
    home: '/dashboard',
    palette: {
      primary: '#5f8dff',
      secondary: '#ff92b6',
      soft: '#eef4ff',
      surface: '#ffffff',
      text: '#284163'
    },
    login: {
      eyebrow: '校园成长中心',
      title: '把学习进度、成绩变化和 AI 助手放到一个轻松好用的空间里',
      subtitle: '更柔和的视觉、更直接的入口，让学生一登录就知道今天该关注什么。',
      visualTitle: '青春校园 · 今日启航',
      visualSubtitle: '课表、成绩、通知与 AI 学习工具集中呈现。',
      highlights: ['成绩查询更直观', 'AI 学习工具一键进入', '通知与课表同屏查看']
    },
    dashboard: {
      heroBadge: '学生工作台',
      heroTitle: '你好，今天也适合把学习安排得清清楚楚。',
      heroText: '首页会优先展示成绩趋势、近期考试和 AI 学习入口，让你少找一步，专注学习本身。',
      shortcuts: [
        { title: '成绩管理', path: '/scores', description: '查看科目成绩与考试批次' },
        { title: '校规问答', path: '/ai/rule', description: '常见校园问题随时咨询' },
        { title: '模拟面试', path: '/ai/interview', description: '提前练习表达与应答' }
      ],
      noticeTitle: '校园提醒',
      secondaryTitle: '今日课表'
    },
    layout: {
      shellStart: '#f8fbff',
      shellEnd: '#eef5ff',
      sidebarStart: '#fefeff',
      sidebarEnd: '#eef5ff',
      sidebarOverlay: 'rgba(255,255,255,0.74)',
      accentSoft: 'rgba(95, 141, 255, 0.14)',
      accentStrong: '#5f8dff',
      accentText: '#25416a',
      iconColor: '#7e95bb'
    },
    assistant: {
      badge: '学习搭子',
      fabLabel: '小助手',
      fabHint: '随时陪你聊聊',
      panelTitle: '今天也一起慢慢变好',
      panelSubtitle: '学习、校园生活和小心情，都可以轻松跟我说。',
      placeholder: '可以问成绩、校规，也可以聊聊今天的心情',
      shell: 'linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(255,247,252,0.98) 100%)',
      header: 'linear-gradient(135deg, #fff3fb 0%, #eef6ff 100%)',
      messageBg: 'linear-gradient(180deg, #fff9fd 0%, #f6f9ff 100%)',
      accent: '#ff7eb3',
      accentSecondary: '#6fa8ff',
      accentSoft: 'rgba(255, 126, 179, 0.14)',
      userBubble: 'linear-gradient(135deg, #ff8bbd 0%, #7aa8ff 100%)',
      assistantBubble: '#fff4fb',
      statusBg: 'rgba(255, 126, 179, 0.12)',
      statusText: '#9d4a78',
      fabShadow: '0 22px 44px rgba(255, 126, 179, 0.34)'
    }
  },
  [ROLES.TEACHER]: {
    name: '教师',
    home: '/dashboard',
    palette: {
      primary: '#2f9d8f',
      secondary: '#78d7c6',
      soft: '#edf9f6',
      surface: '#ffffff',
      text: '#204a46'
    },
    login: {
      eyebrow: '教学协同中心',
      title: '把班级管理、成绩录入和 AI 教学工具放到更高效的一个入口里',
      subtitle: '清爽简洁的登录区与教学场景联动，进入系统后能快速切到常用模块。',
      visualTitle: '教学办公 · 清晰高效',
      visualSubtitle: '学生管理、成绩录入与 AI 教学助手无缝衔接。',
      highlights: ['班级事务入口更集中', '成绩录入与诊断更高效', '教学 AI 工具随用随开']
    },
    dashboard: {
      heroBadge: '教师工作台',
      heroTitle: '班级管理、成绩处理和教学辅助，现在都更顺手了。',
      heroText: '首页突出学生管理、班级情况和近期教学事项，让教师登录后能直接进入工作状态。',
      shortcuts: [
        { title: '学生管理', path: '/students', description: '筛选学生、查看标签与情况' },
        { title: '成绩管理', path: '/scores', description: '录入成绩并查看统计' },
        { title: 'AI 教学工具', path: '/ai/comment', description: '评语、公告和班会策划一站可达' }
      ],
      noticeTitle: '班级通知',
      secondaryTitle: '教学任务'
    },
    layout: {
      shellStart: '#f6fdfc',
      shellEnd: '#edf8f6',
      sidebarStart: '#fbfffe',
      sidebarEnd: '#edf8f4',
      sidebarOverlay: 'rgba(255,255,255,0.8)',
      accentSoft: 'rgba(47, 157, 143, 0.13)',
      accentStrong: '#2f9d8f',
      accentText: '#21524d',
      iconColor: '#6f9690'
    },
    assistant: {
      badge: '教学助手',
      fabLabel: '教务 AI',
      fabHint: '学生、班级、成绩随问',
      panelTitle: '教学事务可以更顺手一点',
      panelSubtitle: '班级、成绩、校规和教学灵感，我都可以帮你接住。',
      placeholder: '可以问班级、成绩、学生情况，或日常教学问题',
      shell: 'linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(242,252,248,0.98) 100%)',
      header: 'linear-gradient(135deg, #eefcf8 0%, #f7fffd 100%)',
      messageBg: 'linear-gradient(180deg, #f6fdfb 0%, #ffffff 100%)',
      accent: '#2f9d8f',
      accentSecondary: '#78d7c6',
      accentSoft: 'rgba(47, 157, 143, 0.13)',
      userBubble: 'linear-gradient(135deg, #2f9d8f 0%, #5fc6b7 100%)',
      assistantBubble: '#eefaf6',
      statusBg: 'rgba(47, 157, 143, 0.1)',
      statusText: '#23665d',
      fabShadow: '0 22px 44px rgba(47, 157, 143, 0.28)'
    }
  },
  [ROLES.ADMIN]: {
    name: '管理员',
    home: '/dashboard',
    palette: {
      primary: '#2f5b9a',
      secondary: '#7a8fae',
      soft: '#eef3fb',
      surface: '#ffffff',
      text: '#1f3554'
    },
    login: {
      eyebrow: '校园运营中心',
      title: '进入学校数据、人员管理与系统配置的统一驾驶舱',
      subtitle: '更规整的商务视觉与更明确的层级，让管理员在登录时就形成清晰的系统感知。',
      visualTitle: '学校治理 · 运营总览',
      visualSubtitle: '校务协同、数据总览与制度管理集中处理。',
      highlights: ['全校数据统一总览', '人员与班级管理更规整', '系统治理入口层级清晰']
    },
    dashboard: {
      heroBadge: '管理驾驶舱',
      heroTitle: '全校人员、班级和成绩数据，在一个更稳重清晰的界面里汇总。',
      heroText: '首页优先展示全局概览、核心管理入口和学校运营视角的数据摘要，适合管理端快速决策。',
      shortcuts: [
        { title: '教师管理', path: '/teachers', description: '查看人员与任课安排' },
        { title: '班级管理', path: '/classes', description: '掌握班级规模与结构' },
        { title: '校规管理', path: '/school-rules', description: '维护校园制度与答疑基础' }
      ],
      noticeTitle: '运营关注',
      secondaryTitle: '系统快照'
    },
    layout: {
      shellStart: '#f4f7fb',
      shellEnd: '#eaf0f7',
      sidebarStart: '#fbfcff',
      sidebarEnd: '#eef3fb',
      sidebarOverlay: 'rgba(255,255,255,0.84)',
      accentSoft: 'rgba(47, 91, 154, 0.12)',
      accentStrong: '#2f5b9a',
      accentText: '#213854',
      iconColor: '#7085a3'
    },
    assistant: {
      badge: '运营助手',
      fabLabel: '校务 AI',
      fabHint: '数据与制度随叫随到',
      panelTitle: '校务视角的决策辅助入口',
      panelSubtitle: '班级、教师、成绩、校规和全局信息，我会尽量答得更清楚。',
      placeholder: '可以问校务数据、教师、班级、成绩或最新信息',
      shell: 'linear-gradient(180deg, rgba(255,255,255,0.97) 0%, rgba(243,247,253,0.99) 100%)',
      header: 'linear-gradient(135deg, #eef3fb 0%, #f8fbff 100%)',
      messageBg: 'linear-gradient(180deg, #f7faff 0%, #ffffff 100%)',
      accent: '#2f5b9a',
      accentSecondary: '#7a8fae',
      accentSoft: 'rgba(47, 91, 154, 0.12)',
      userBubble: 'linear-gradient(135deg, #2f5b9a 0%, #587ab0 100%)',
      assistantBubble: '#eef4fb',
      statusBg: 'rgba(47, 91, 154, 0.1)',
      statusText: '#29476d',
      fabShadow: '0 22px 44px rgba(47, 91, 154, 0.24)'
    }
  }
}

export function getRoleHome(role) {
  return ROLE_UI[role]?.home || '/dashboard'
}

export function getRoleUi(role) {
  return ROLE_UI[role] || ROLE_UI[ROLES.STUDENT]
}

export function getRoleName(role) {
  return getRoleUi(role).name
}
