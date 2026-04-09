<template>
  <div class="ai-history-list">
    <el-empty v-if="!loading && historyList.length === 0" description="暂无 AI 历史记录" />

    <el-table v-else v-loading="loading" :data="historyList" border stripe>
      <el-table-column label="工具类型" width="140">
        <template #default="{ row }">
          {{ toolNameMap[row.tool_type] || row.tool_type }}
        </template>
      </el-table-column>
      <el-table-column prop="content" label="内容摘要" min-width="320" show-overflow-tooltip />
      <el-table-column prop="created_at" label="生成时间" width="180" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="$emit('view', row)">查看</el-button>
          <el-button type="success" link @click="$emit('reuse', row)">复用</el-button>
          <el-button type="danger" link @click="$emit('delete', row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
const toolNameMap = {
  comment: '评语生成',
  discipline: '违纪话术',
  notice: '公告润色',
  rule_qa: '校规问答',
  score_diag: '成绩诊断',
  meeting: '班会策划',
  interview: '模拟面试',
  group: '分组分班'
}

defineProps({
  historyList: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['view', 'reuse', 'delete'])
</script>
