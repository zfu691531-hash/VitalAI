<!--
  分页组件
  ========
  封装el-pagination，提供统一的分页交互：
  - 显示总条数
  - 可切换每页条数（10/20/50）
  - 页码切换
  props: { total, page, pageSize }
  emit: update:page, update:pageSize
-->
<template>
  <div class="pagination-container">
    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="currentPageSize"
      :page-sizes="pageSizes"
      :total="total"
      :background="true"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="handleSizeChange"
      @current-change="handleCurrentChange"
    />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  total: {
    type: Number,
    default: 0
  },
  page: {
    type: Number,
    default: 1
  },
  pageSize: {
    type: Number,
    default: 10
  },
  pageSizes: {
    type: Array,
    default: () => [10, 20, 50, 100]
  }
})

const emit = defineEmits(['update:page', 'update:pageSize', 'change'])

const currentPage = ref(props.page)
const currentPageSize = ref(props.pageSize)

// 监听props变化
watch(
  () => props.page,
  (val) => {
    currentPage.value = val
  }
)

watch(
  () => props.pageSize,
  (val) => {
    currentPageSize.value = val
  }
)

// 每页条数变化
function handleSizeChange(val) {
  emit('update:pageSize', val)
  emit('change', { page: currentPage.value, pageSize: val })
}

// 页码变化
function handleCurrentChange(val) {
  emit('update:page', val)
  emit('change', { page: val, pageSize: currentPageSize.value })
}
</script>

<style scoped lang="scss">
.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
