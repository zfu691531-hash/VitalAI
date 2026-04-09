/**
 * 全局常量定义
 */

export const ROLES = {
  STUDENT: 'student',
  TEACHER: 'teacher',
  ADMIN: 'admin'
}

export const ROLE_NAMES = {
  [ROLES.STUDENT]: '学生',
  [ROLES.TEACHER]: '教师',
  [ROLES.ADMIN]: '管理员'
}

export const GENDERS = [
  { value: 'male', label: '男' },
  { value: 'female', label: '女' }
]

export const SUBJECTS = [
  { value: '语文', label: '语文' },
  { value: '数学', label: '数学' },
  { value: '英语', label: '英语' },
  { value: '物理', label: '物理' },
  { value: '化学', label: '化学' },
  { value: '生物', label: '生物' },
  { value: '历史', label: '历史' },
  { value: '地理', label: '地理' },
  { value: '政治', label: '政治' }
]

export const EXAM_BATCHES = [
  { value: '期中考试', label: '期中考试' },
  { value: '期末考试', label: '期末考试' },
  { value: '月考', label: '月考' },
  { value: '模拟考试', label: '模拟考试' }
]

export const STUDENT_TAGS = {
  CARE: ['学习困难', '家庭困难', '心理关怀', '身体关怀'],
  DISCIPLINE: ['迟到', '旷课', '打架', '作弊', '其他违纪']
}

export const TEACHER_TITLES = [
  { value: '初级教师', label: '初级教师' },
  { value: '中级教师', label: '中级教师' },
  { value: '高级教师', label: '高级教师' },
  { value: '特级教师', label: '特级教师' }
]

export const GRADES = [
  { value: '一年级', label: '一年级' },
  { value: '二年级', label: '二年级' },
  { value: '三年级', label: '三年级' },
  { value: '四年级', label: '四年级' },
  { value: '五年级', label: '五年级' },
  { value: '六年级', label: '六年级' },
  { value: '七年级', label: '七年级' },
  { value: '八年级', label: '八年级' },
  { value: '九年级', label: '九年级' },
  { value: '高一', label: '高一' },
  { value: '高二', label: '高二' },
  { value: '高三', label: '高三' }
]

export const AI_TOOL_TYPES = {
  COMMENT: 'comment',
  DISCIPLINE: 'discipline',
  NOTICE: 'notice',
  RULE: 'rule',
  DIAGNOSIS: 'diagnosis',
  MEETING: 'meeting',
  INTERVIEW: 'interview',
  GROUP: 'group'
}

export const AI_TOOL_NAMES = {
  [AI_TOOL_TYPES.COMMENT]: '期末评语生成',
  [AI_TOOL_TYPES.DISCIPLINE]: '违纪沟通话术',
  [AI_TOOL_TYPES.NOTICE]: '公告润色助手',
  [AI_TOOL_TYPES.RULE]: '校规问答助手',
  [AI_TOOL_TYPES.DIAGNOSIS]: '成绩波动诊断',
  [AI_TOOL_TYPES.MEETING]: '班会活动策划',
  [AI_TOOL_TYPES.INTERVIEW]: '模拟面试助手',
  [AI_TOOL_TYPES.GROUP]: '智能分组分班'
}

export const RULE_CATEGORIES = [
  { value: '日常行为', label: '日常行为' },
  { value: '学习纪律', label: '学习纪律' },
  { value: '校园安全', label: '校园安全' },
  { value: '宿舍管理', label: '宿舍管理' },
  { value: '食堂管理', label: '食堂管理' },
  { value: '其他', label: '其他' }
]

export const COMMUNICATION_MODES = [
  { value: 'gentle', label: '温和' },
  { value: 'strict', label: '严格' }
]

export const COMMUNICATION_TARGETS = [
  { value: 'student', label: '学生' },
  { value: 'parent', label: '家长' }
]

export const POLISH_STYLES = [
  { value: 'formal', label: '正式' },
  { value: 'friendly', label: '亲切' },
  { value: 'concise', label: '简洁' }
]

export const PAGINATION = {
  PAGE_SIZES: [10, 20, 50, 100],
  DEFAULT_PAGE_SIZE: 10
}
