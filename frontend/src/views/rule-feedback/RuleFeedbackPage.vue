<template>
  <div class="page-container">
    <SearchBar :filters="filterOptions" @search="handleSearch" @reset="handleReset" />

    <el-table v-loading="loading" :data="tableData" border stripe>
      <el-table-column prop="question" label="问题" min-width="220" show-overflow-tooltip />
      <el-table-column prop="rating" label="满意度" width="100">
        <template #default="{ row }">
          <el-tag :type="row.rating === 'up' ? 'success' : 'danger'">
            {{ row.rating === 'up' ? '满意' : '不满意' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="处理状态" width="130">
        <template #default="{ row }">
          {{ statusText(row.status) }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="提交时间" width="180" />
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openDetail(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <Pagination
      :total="total"
      :page="queryParams.page"
      :page-size="queryParams.page_size"
      @change="handlePageChange"
    />

    <el-drawer v-model="detailVisible" title="反馈详情" size="760px">
      <template v-if="detailData">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="问题">{{ detailData.question }}</el-descriptions-item>
          <el-descriptions-item label="原回答">{{ detailData.answer }}</el-descriptions-item>
          <el-descriptions-item label="改进理由">{{ detailData.improvement_reason || '-' }}</el-descriptions-item>
          <el-descriptions-item label="建议答案">{{ detailData.suggested_answer || '-' }}</el-descriptions-item>
          <el-descriptions-item label="处理状态">{{ statusText(detailData.status) }}</el-descriptions-item>
        </el-descriptions>

        <el-divider>命中片段</el-divider>
        <el-card
          v-for="item in detailData.sources || []"
          :key="item.chunk_id"
          shadow="never"
          class="source-card"
        >
          <div class="source-head">
            <span>校规 #{{ item.rule_id }}</span>
            <span>融合分：{{ item.scores?.fused }}</span>
          </div>
          <div class="source-meta">
            <span>BM25：{{ item.scores?.bm25 }}</span>
            <span>标题加权：{{ item.scores?.title_boost ?? 0 }}</span>
            <span>稀疏：{{ item.scores?.sparse }}</span>
            <span>稠密：{{ item.scores?.dense }}</span>
          </div>
          <div class="source-text">{{ item.chunk_text }}</div>
        </el-card>

        <el-divider>处理操作</el-divider>
        <el-form :model="reviewForm" label-width="90px">
          <el-form-item label="处理说明">
            <el-input v-model="reviewForm.review_note" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="修订标题">
            <el-input v-model="reviewForm.revised_title" placeholder="仅在修改后采纳时填写" />
          </el-form-item>
          <el-form-item label="修订分类">
            <el-input v-model="reviewForm.revised_category" placeholder="仅在修改后采纳时填写" />
          </el-form-item>
          <el-form-item label="修订内容">
            <el-input
              v-model="reviewForm.revised_content"
              type="textarea"
              :rows="5"
              placeholder="仅在修改后采纳时填写"
            />
          </el-form-item>
        </el-form>

        <div class="action-row">
          <el-button type="success" :loading="submitLoading" @click="handleAdopt(false)">直接采纳</el-button>
          <el-button type="primary" :loading="submitLoading" @click="handleAdopt(true)">修改后采纳</el-button>
          <el-button type="danger" :loading="submitLoading" @click="handleReject">驳回</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import Pagination from '@/components/common/Pagination.vue'
import SearchBar from '@/components/common/SearchBar.vue'
import {
  adoptRuleFeedback,
  getRuleFeedbackDetail,
  getRuleFeedbackList,
  rejectRuleFeedback,
  reviseAndAdoptRuleFeedback
} from '@/api/ruleFeedback'

const filterOptions = [
  {
    key: 'status',
    label: '处理状态',
    options: [
      { value: 'pending', label: '待处理' },
      { value: 'adopted', label: '已采纳' },
      { value: 'revised', label: '已修改后采纳' },
      { value: 'rejected', label: '已驳回' }
    ]
  }
]

const queryParams = reactive({
  page: 1,
  page_size: 10,
  status: ''
})

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const detailVisible = ref(false)
const detailData = ref(null)
const submitLoading = ref(false)
const reviewForm = reactive({
  review_note: '',
  revised_title: '',
  revised_category: '',
  revised_content: ''
})

fetchList()

async function fetchList() {
  loading.value = true
  try {
    const res = await getRuleFeedbackList({
      page: queryParams.page,
      page_size: queryParams.page_size,
      status: queryParams.status || undefined
    })
    tableData.value = res.list
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function handleSearch(params) {
  Object.assign(queryParams, params, { page: 1 })
  fetchList()
}

function handleReset() {
  Object.assign(queryParams, { page: 1, page_size: 10, status: '' })
  fetchList()
}

function handlePageChange({ page, pageSize }) {
  queryParams.page = page
  queryParams.page_size = pageSize
  fetchList()
}

async function openDetail(row) {
  detailData.value = await getRuleFeedbackDetail(row.id)
  detailVisible.value = true
  Object.assign(reviewForm, {
    review_note: '',
    revised_title: '',
    revised_category: '',
    revised_content: ''
  })
}

async function handleAdopt(withRevision) {
  if (!detailData.value?.id) return
  if (withRevision && !reviewForm.revised_content && !reviewForm.revised_title && !reviewForm.revised_category) {
    ElMessage.warning('修改后采纳至少需要填写一项修订内容')
    return
  }

  submitLoading.value = true
  try {
    if (withRevision) {
      await reviseAndAdoptRuleFeedback(detailData.value.id, { ...reviewForm })
    } else {
      await adoptRuleFeedback(detailData.value.id, { review_note: reviewForm.review_note })
    }
    ElMessage.success('处理成功')
    detailVisible.value = false
    fetchList()
  } finally {
    submitLoading.value = false
  }
}

async function handleReject() {
  if (!detailData.value?.id) return
  submitLoading.value = true
  try {
    await rejectRuleFeedback(detailData.value.id, { review_note: reviewForm.review_note })
    ElMessage.success('已驳回')
    detailVisible.value = false
    fetchList()
  } finally {
    submitLoading.value = false
  }
}

function statusText(status) {
  return (
    {
      pending: '待处理',
      adopted: '已采纳',
      revised: '已修改后采纳',
      rejected: '已驳回'
    }[status] || status
  )
}
</script>

<style scoped lang="scss">
.source-card {
  margin-bottom: 12px;
}

.source-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 12px;
}

.source-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 10px;
  color: #64748b;
  font-size: 12px;
}

.source-text {
  white-space: pre-wrap;
  line-height: 1.7;
}

.action-row {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}
</style>
