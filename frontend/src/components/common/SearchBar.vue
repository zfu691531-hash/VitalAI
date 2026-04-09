<template>
  <div class="search-bar">
    <el-form :inline="true" :model="formState" class="search-form">
      <el-form-item>
        <el-input
          v-model="formState.keyword"
          placeholder="请输入关键词搜索"
          clearable
          @keyup.enter="handleSearch"
          style="width: 220px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </el-form-item>

      <el-form-item v-for="filter in filters" :key="filter.key">
        <el-select
          v-model="formState[filter.key]"
          :placeholder="`请选择${filter.label}`"
          clearable
          style="width: 150px"
        >
          <el-option
            v-for="option in filter.options"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="handleSearch">
          <el-icon><Search /></el-icon>搜索
        </el-button>
        <el-button @click="handleReset">
          <el-icon><Refresh /></el-icon>重置
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'

const props = defineProps({
  filters: {
    type: Array,
    default: () => []
  },
  initialValues: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['search', 'reset'])

const formState = reactive({
  keyword: '',
  ...props.initialValues
})

watch(
  () => props.initialValues,
  (newVal) => {
    Object.assign(formState, newVal)
  },
  { deep: true }
)

function handleSearch() {
  emit('search', { ...formState })
}

function handleReset() {
  formState.keyword = ''
  props.filters.forEach((filter) => {
    formState[filter.key] = ''
  })
  Object.assign(formState, props.initialValues)
  emit('reset')
}
</script>

<style scoped lang="scss">
.search-bar {
  margin-bottom: 16px;

  .search-form {
    display: flex;
    flex-wrap: wrap;

    .el-form-item {
      margin-bottom: 0;
      margin-right: 12px;

      &:last-child {
        margin-right: 0;
      }
    }
  }
}
</style>
