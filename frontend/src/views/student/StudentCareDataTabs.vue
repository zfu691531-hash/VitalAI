<template>
  <div class="data-tabs">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="出勤记录" name="attendance">
        <div class="tab-toolbar"><el-button type="primary" @click="openAttendanceDialog">新增记录</el-button></div>
        <el-table :data="attendanceList" size="small" border stripe>
          <el-table-column prop="date" label="日期" width="130" />
          <el-table-column prop="status" label="状态" width="120"><template #default="{ row }">{{ statusLabel(row.status) }}</template></el-table-column>
          <el-table-column prop="remark" label="备注" min-width="220" show-overflow-tooltip />
          <el-table-column label="操作" width="150"><template #default="{ row }"><el-button type="primary" link @click="editAttendance(row)">编辑</el-button><el-button type="danger" link @click="removeAttendance(row)">删除</el-button></template></el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="行为事件" name="behavior">
        <div class="tab-toolbar"><el-button type="primary" @click="openBehaviorDialog">新增事件</el-button></div>
        <el-table :data="behaviorList" size="small" border stripe>
          <el-table-column prop="occurred_at" label="发生时间" width="170" />
          <el-table-column prop="event_type" label="类型" width="130"><template #default="{ row }">{{ behaviorTypeLabel(row.event_type) }}</template></el-table-column>
          <el-table-column prop="event_level" label="级别" width="100"><template #default="{ row }">{{ levelLabel(row.event_level) }}</template></el-table-column>
          <el-table-column prop="event_desc" label="描述" min-width="240" show-overflow-tooltip />
          <el-table-column label="操作" width="150"><template #default="{ row }"><el-button type="primary" link @click="editBehavior(row)">编辑</el-button><el-button type="danger" link @click="removeBehavior(row)">删除</el-button></template></el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="关怀观察" name="observation">
        <div class="tab-toolbar"><el-button type="primary" @click="openObservationDialog">新增观察</el-button></div>
        <el-table :data="observationList" size="small" border stripe>
          <el-table-column prop="observed_at" label="观察时间" width="170" />
          <el-table-column prop="dimension" label="维度" width="120"><template #default="{ row }">{{ dimensionLabel(row.dimension) }}</template></el-table-column>
          <el-table-column prop="observation_type" label="类型" width="140"><template #default="{ row }">{{ observationTypeLabel(row.observation_type) }}</template></el-table-column>
          <el-table-column prop="observation_level" label="关注级别" width="110"><template #default="{ row }">{{ levelLabel(row.observation_level) }}</template></el-table-column>
          <el-table-column prop="summary" label="观察摘要" min-width="260" show-overflow-tooltip />
          <el-table-column label="操作" width="150"><template #default="{ row }"><el-button type="primary" link @click="editObservation(row)">编辑</el-button><el-button type="danger" link @click="removeObservation(row)">删除</el-button></template></el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="家校沟通" name="family">
        <div class="tab-toolbar"><el-button type="primary" @click="openFamilyDialog">新增沟通</el-button></div>
        <el-table :data="familyList" size="small" border stripe>
          <el-table-column prop="created_at" label="记录时间" width="170" />
          <el-table-column prop="contact_type" label="方式" width="120"><template #default="{ row }">{{ contactTypeLabel(row.contact_type) }}</template></el-table-column>
          <el-table-column prop="summary" label="摘要" min-width="260" show-overflow-tooltip />
          <el-table-column label="操作" width="120"><template #default="{ row }"><el-button type="danger" link @click="removeFamily(row)">删除</el-button></template></el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="图谱关系" name="graph">
        <div class="tab-toolbar">
          <div class="graph-toolbar-tip">可补录关联同学或关键事件，这些关系会同步进入图谱与画像。</div>
          <el-button type="primary" @click="openGraphDialog">新增关系</el-button>
        </div>
        <el-table :data="graphRelationList" size="small" border stripe>
          <el-table-column prop="target_type" label="关系对象" width="100"><template #default="{ row }">{{ graphTargetTypeLabel(row.target_type) }}</template></el-table-column>
          <el-table-column label="关联内容" min-width="180"><template #default="{ row }">{{ graphRelationTargetText(row) }}</template></el-table-column>
          <el-table-column prop="relation_type" label="关系类型" width="120"><template #default="{ row }">{{ graphRelationTypeLabel(row.relation_type) }}</template></el-table-column>
          <el-table-column prop="dimension" label="作用维度" width="110"><template #default="{ row }">{{ dimensionLabel(row.dimension) }}</template></el-table-column>
          <el-table-column prop="relation_level" label="强度" width="90"><template #default="{ row }">{{ levelLabel(row.relation_level) }}</template></el-table-column>
          <el-table-column prop="summary" label="备注" min-width="220" show-overflow-tooltip />
          <el-table-column label="操作" width="150"><template #default="{ row }"><el-button type="primary" link @click="editGraphRelation(row)">编辑</el-button><el-button type="danger" link @click="removeGraphRelation(row)">删除</el-button></template></el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="attendanceDialogVisible" :title="attendanceForm.id ? '编辑出勤记录' : '新增出勤记录'" width="420px">
      <el-form :model="attendanceForm" label-width="80px">
        <el-form-item label="日期"><el-date-picker v-model="attendanceForm.date" type="date" value-format="YYYY-MM-DD" /></el-form-item>
        <el-form-item label="状态"><el-select v-model="attendanceForm.status"><el-option label="正常" value="normal" /><el-option label="迟到" value="late" /><el-option label="缺勤" value="absent" /><el-option label="早退" value="early_leave" /></el-select></el-form-item>
        <el-form-item label="备注"><el-input v-model="attendanceForm.remark" placeholder="可选" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="attendanceDialogVisible = false">取消</el-button><el-button type="primary" @click="submitAttendance">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="behaviorDialogVisible" :title="behaviorForm.id ? '编辑行为事件' : '新增行为事件'" width="520px">
      <el-form :model="behaviorForm" label-width="90px">
        <el-form-item label="发生时间"><el-date-picker v-model="behaviorForm.occurred_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" /></el-form-item>
        <el-form-item label="类型"><el-select v-model="behaviorForm.event_type"><el-option label="纪律事件" value="discipline" /><el-option label="冲突事件" value="conflict" /><el-option label="预警事件" value="warning" /><el-option label="欺凌线索" value="bullying" /><el-option label="威胁线索" value="threat" /><el-option label="宿舍冲突" value="dorm_conflict" /><el-option label="网络冲突" value="cyber_conflict" /></el-select></el-form-item>
        <el-form-item label="级别"><el-select v-model="behaviorForm.event_level"><el-option label="低" value="low" /><el-option label="中" value="medium" /><el-option label="高" value="high" /></el-select></el-form-item>
        <el-form-item label="描述"><el-input v-model="behaviorForm.event_desc" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="behaviorDialogVisible = false">取消</el-button><el-button type="primary" @click="submitBehavior">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="observationDialogVisible" :title="observationForm.id ? '编辑关怀观察' : '新增关怀观察'" width="540px">
      <el-form :model="observationForm" label-width="90px">
        <el-form-item label="观察时间"><el-date-picker v-model="observationForm.observed_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" /></el-form-item>
        <el-form-item label="风险维度"><el-select v-model="observationForm.dimension"><el-option label="情绪状态" value="emotion" /><el-option label="社交融入" value="social" /><el-option label="校园安全" value="safety" /><el-option label="家庭支持" value="family" /><el-option label="学习压力" value="study" /><el-option label="行为稳定" value="behavior" /></el-select></el-form-item>
        <el-form-item label="观察类型"><el-select v-model="observationForm.observation_type"><el-option label="关怀谈话" value="care_talk" /><el-option label="情绪观察" value="emotion_observation" /><el-option label="社交观察" value="social_observation" /><el-option label="安全线索" value="safety_observation" /><el-option label="学习观察" value="study_observation" /><el-option label="行为观察" value="behavior_observation" /><el-option label="后续跟进" value="follow_up" /></el-select></el-form-item>
        <el-form-item label="关注级别"><el-select v-model="observationForm.observation_level"><el-option label="低" value="low" /><el-option label="中" value="medium" /><el-option label="高" value="high" /></el-select></el-form-item>
        <el-form-item label="观察摘要"><el-input v-model="observationForm.summary" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="observationDialogVisible = false">取消</el-button><el-button type="primary" @click="submitObservation">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="familyDialogVisible" title="新增家校沟通" width="460px">
      <el-form :model="familyForm" label-width="90px">
        <el-form-item label="沟通方式"><el-select v-model="familyForm.contact_type"><el-option label="电话" value="phone" /><el-option label="面谈" value="meeting" /><el-option label="家访" value="home_visit" /></el-select></el-form-item>
        <el-form-item label="摘要"><el-input v-model="familyForm.summary" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="familyDialogVisible = false">取消</el-button><el-button type="primary" @click="submitFamily">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="graphDialogVisible" :title="graphForm.id ? '编辑图谱关系' : '新增图谱关系'" width="560px">
      <el-form :model="graphForm" label-width="90px">
        <el-form-item label="关系对象"><el-radio-group v-model="graphForm.target_type"><el-radio-button label="student">关联同学</el-radio-button><el-radio-button label="event">关联事件</el-radio-button></el-radio-group></el-form-item>
        <el-form-item v-if="graphForm.target_type === 'student'" label="目标学生"><el-select v-model="graphForm.target_student_id" filterable><el-option v-for="item in classmateOptions" :key="item.id" :label="`${item.name} (${item.student_no})`" :value="item.id" /></el-select></el-form-item>
        <el-form-item v-else label="事件标题"><el-input v-model="graphForm.event_title" placeholder="例如：宿舍争执、课间推搡" /></el-form-item>
        <el-form-item label="关系类型"><el-select v-model="graphForm.relation_type"><el-option label="同伴支持" value="peer_support" /><el-option label="冲突关系" value="conflict" /><el-option label="欺凌关联" value="bullying_link" /><el-option label="共同活动" value="shared_activity" /><el-option label="重点关注" value="concern" /></el-select></el-form-item>
        <el-form-item label="作用维度"><el-select v-model="graphForm.dimension"><el-option label="情绪状态" value="emotion" /><el-option label="社交融入" value="social" /><el-option label="校园安全" value="safety" /><el-option label="家庭支持" value="family" /><el-option label="学习压力" value="study" /><el-option label="行为稳定" value="behavior" /></el-select></el-form-item>
        <el-form-item label="关系强度"><el-select v-model="graphForm.relation_level"><el-option label="低" value="low" /><el-option label="中" value="medium" /><el-option label="高" value="high" /></el-select></el-form-item>
        <el-form-item label="发生时间"><el-date-picker v-model="graphForm.occurred_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" placeholder="可选" /></el-form-item>
        <el-form-item label="备注说明"><el-input v-model="graphForm.summary" type="textarea" :rows="4" placeholder="补充这条关系线索的具体情况" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="graphDialogVisible = false">取消</el-button><el-button type="primary" @click="submitGraphRelation">保存</el-button></template>
    </el-dialog>

    <ConfirmDialog v-model:visible="deleteDialog.visible" title="删除确认" :message="deleteDialog.message" :sub-message="deleteDialog.subMessage" confirm-type="danger" confirm-text="确认删除" cancel-text="再想想" width="460px" :loading="deleteDialog.loading" @confirm="confirmDelete" @cancel="resetDeleteDialog" />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import { getStudentList } from '@/api/student'
import { createAttendance, createBehaviorEvent, createCareObservation, createFamilyContact, createGraphRelation, deleteAttendance, deleteBehaviorEvent, deleteCareObservation, deleteFamilyContact, deleteGraphRelation, getAttendance, getBehaviorEvents, getCareObservations, getFamilyContacts, getGraphRelations, updateAttendance, updateBehaviorEvent, updateCareObservation, updateGraphRelation } from '@/api/studentCareData'

const props = defineProps({ student: { type: Object, default: null }, visible: { type: Boolean, default: false } })
const emit = defineEmits(['data-changed'])

const activeTab = ref('attendance')
const attendanceList = ref([]), behaviorList = ref([]), observationList = ref([]), familyList = ref([]), graphRelationList = ref([]), classmateOptions = ref([])
const attendanceDialogVisible = ref(false), behaviorDialogVisible = ref(false), observationDialogVisible = ref(false), familyDialogVisible = ref(false), graphDialogVisible = ref(false)
const attendanceForm = reactive({ id: null, date: '', status: 'normal', remark: '' })
const behaviorForm = reactive({ id: null, occurred_at: '', event_type: 'discipline', event_level: 'medium', event_desc: '' })
const observationForm = reactive({ id: null, dimension: 'emotion', observation_type: 'care_talk', observation_level: 'medium', observed_at: '', summary: '' })
const familyForm = reactive({ contact_type: 'phone', summary: '' })
const graphForm = reactive({ id: null, target_type: 'student', target_student_id: null, relation_type: 'peer_support', dimension: 'social', relation_level: 'medium', summary: '', event_title: '', occurred_at: '' })
const deleteDialog = reactive({ visible: false, loading: false, type: '', row: null, message: '', subMessage: '' })

const dimensionOptions = ['emotion', 'social', 'safety', 'family', 'study', 'behavior']

onMounted(() => { if (props.student?.id) fetchAll() })
watch(() => props.student?.id, () => { if (props.student?.id) fetchAll() })
watch(() => props.visible, (val) => { if (val && props.student?.id) fetchAll() })
watch(() => graphForm.target_type, (val) => { if (val === 'student') graphForm.event_title = ''; else graphForm.target_student_id = null })

async function fetchAll() { await Promise.all([fetchAttendance(), fetchBehavior(), fetchObservation(), fetchFamily(), fetchGraphRelations(), fetchClassmates()]) }
async function fetchAttendance() { const res = await getAttendance({ student_id: props.student.id }); attendanceList.value = res.list || [] }
async function fetchBehavior() { const res = await getBehaviorEvents({ student_id: props.student.id }); behaviorList.value = res.list || [] }
async function fetchObservation() { const res = await getCareObservations({ student_id: props.student.id }); observationList.value = res.list || [] }
async function fetchFamily() { const res = await getFamilyContacts({ student_id: props.student.id }); familyList.value = res.list || [] }
async function fetchGraphRelations() { const res = await getGraphRelations({ student_id: props.student.id }); graphRelationList.value = res.list || [] }
async function fetchClassmates() {
  if (!props.student?.class_id) { classmateOptions.value = []; return }
  const res = await getStudentList({ class_id: props.student.class_id, page: 1, page_size: 100 })
  classmateOptions.value = (res.list || []).filter((item) => item.id !== props.student.id)
}

function resetAttendanceForm() { Object.assign(attendanceForm, { id: null, date: '', status: 'normal', remark: '' }) }
function resetBehaviorForm() { Object.assign(behaviorForm, { id: null, occurred_at: '', event_type: 'discipline', event_level: 'medium', event_desc: '' }) }
function resetObservationForm() { Object.assign(observationForm, { id: null, dimension: 'emotion', observation_type: 'care_talk', observation_level: 'medium', observed_at: '', summary: '' }) }
function resetFamilyForm() { Object.assign(familyForm, { contact_type: 'phone', summary: '' }) }
function resetGraphForm() { Object.assign(graphForm, { id: null, target_type: 'student', target_student_id: null, relation_type: 'peer_support', dimension: 'social', relation_level: 'medium', summary: '', event_title: '', occurred_at: '' }) }

function openAttendanceDialog() { resetAttendanceForm(); attendanceDialogVisible.value = true }
function editAttendance(row) { Object.assign(attendanceForm, { id: row.id, date: row.date, status: row.status, remark: row.remark || '' }); attendanceDialogVisible.value = true }
async function submitAttendance() {
  if (!attendanceForm.date || !attendanceForm.status) return ElMessage.warning('请补全出勤记录')
  try {
    if (attendanceForm.id) await updateAttendance(attendanceForm.id, { status: attendanceForm.status, remark: attendanceForm.remark })
    else await createAttendance({ student_id: props.student.id, date: attendanceForm.date, status: attendanceForm.status, remark: attendanceForm.remark })
    attendanceDialogVisible.value = false; await fetchAttendance(); emitDataChanged('attendance'); ElMessage.success('出勤记录已保存')
  } catch (error) { console.error(error); ElMessage.error('保存出勤记录失败') }
}
function removeAttendance(row) { openDeleteDialog('attendance', row, `确定删除 ${row.date} 的出勤记录吗？`, '删除后这条记录将无法恢复。') }

function openBehaviorDialog() { resetBehaviorForm(); behaviorDialogVisible.value = true }
function editBehavior(row) { Object.assign(behaviorForm, { id: row.id, occurred_at: row.occurred_at, event_type: row.event_type, event_level: row.event_level, event_desc: row.event_desc }); behaviorDialogVisible.value = true }
async function submitBehavior() {
  if (!behaviorForm.occurred_at || !behaviorForm.event_desc) return ElMessage.warning('请补全行为事件')
  try {
    const payload = { student_id: props.student.id, event_type: behaviorForm.event_type, event_level: behaviorForm.event_level, event_desc: behaviorForm.event_desc, occurred_at: behaviorForm.occurred_at }
    if (behaviorForm.id) await updateBehaviorEvent(behaviorForm.id, payload); else await createBehaviorEvent(payload)
    behaviorDialogVisible.value = false; await fetchBehavior(); emitDataChanged('behavior'); ElMessage.success('行为事件已保存')
  } catch (error) { console.error(error); ElMessage.error('保存行为事件失败') }
}
function removeBehavior(row) { openDeleteDialog('behavior', row, '确定删除这条行为事件吗？', `事件描述：${row.event_desc || '未填写'}`) }

function openObservationDialog() { resetObservationForm(); observationDialogVisible.value = true }
function editObservation(row) { Object.assign(observationForm, { id: row.id, dimension: row.dimension, observation_type: row.observation_type, observation_level: row.observation_level, observed_at: row.observed_at, summary: row.summary }); observationDialogVisible.value = true }
async function submitObservation() {
  if (!observationForm.observed_at || !observationForm.summary || !dimensionOptions.includes(observationForm.dimension)) return ElMessage.warning('请补全关怀观察')
  try {
    const payload = { student_id: props.student.id, dimension: observationForm.dimension, observation_type: observationForm.observation_type, observation_level: observationForm.observation_level, observed_at: observationForm.observed_at, summary: observationForm.summary }
    if (observationForm.id) await updateCareObservation(observationForm.id, payload); else await createCareObservation(payload)
    observationDialogVisible.value = false; await fetchObservation(); emitDataChanged('observation'); ElMessage.success('关怀观察已保存')
  } catch (error) { console.error(error); ElMessage.error('保存关怀观察失败') }
}
function removeObservation(row) { openDeleteDialog('observation', row, '确定删除这条关怀观察吗？', `观察摘要：${row.summary || '未填写'}`) }

function openFamilyDialog() { resetFamilyForm(); familyDialogVisible.value = true }
async function submitFamily() {
  if (!familyForm.summary) return ElMessage.warning('请填写沟通摘要')
  try {
    await createFamilyContact({ student_id: props.student.id, contact_type: familyForm.contact_type, summary: familyForm.summary })
    familyDialogVisible.value = false; await fetchFamily(); emitDataChanged('family'); ElMessage.success('家校沟通已保存')
  } catch (error) { console.error(error); ElMessage.error('保存家校沟通失败') }
}
function removeFamily(row) { openDeleteDialog('family', row, '确定删除这条家校沟通记录吗？', `沟通摘要：${row.summary || '未填写'}`) }

function openGraphDialog() { resetGraphForm(); graphDialogVisible.value = true }
function editGraphRelation(row) { Object.assign(graphForm, { id: row.id, target_type: row.target_type, target_student_id: row.target_student_id || null, relation_type: row.relation_type, dimension: row.dimension, relation_level: row.relation_level, summary: row.summary || '', event_title: row.event_title || '', occurred_at: row.occurred_at || '' }); graphDialogVisible.value = true }
async function submitGraphRelation() {
  if (!graphForm.summary) return ElMessage.warning('请填写关系备注')
  if (graphForm.target_type === 'student' && !graphForm.target_student_id) return ElMessage.warning('请选择关联同学')
  if (graphForm.target_type === 'event' && !graphForm.event_title) return ElMessage.warning('请填写事件标题')
  try {
    const payload = { student_id: props.student.id, target_type: graphForm.target_type, target_student_id: graphForm.target_type === 'student' ? graphForm.target_student_id : null, relation_type: graphForm.relation_type, dimension: graphForm.dimension, relation_level: graphForm.relation_level, summary: graphForm.summary, event_title: graphForm.target_type === 'event' ? graphForm.event_title : null, occurred_at: graphForm.occurred_at || null }
    if (graphForm.id) await updateGraphRelation(graphForm.id, payload); else await createGraphRelation(payload)
    graphDialogVisible.value = false; await fetchGraphRelations(); emitDataChanged('graph'); ElMessage.success('图谱关系已保存')
  } catch (error) { console.error(error); ElMessage.error('保存图谱关系失败') }
}
function removeGraphRelation(row) { openDeleteDialog('graph', row, '确定删除这条图谱关系吗？', graphRelationTargetText(row)) }

function openDeleteDialog(type, row, message, subMessage = '') { Object.assign(deleteDialog, { visible: true, loading: false, type, row, message, subMessage }) }
function resetDeleteDialog() { Object.assign(deleteDialog, { visible: false, loading: false, type: '', row: null, message: '', subMessage: '' }) }
async function confirmDelete() {
  deleteDialog.loading = true
  try {
    if (deleteDialog.type === 'attendance') { await deleteAttendance(deleteDialog.row.id); await fetchAttendance() }
    else if (deleteDialog.type === 'behavior') { await deleteBehaviorEvent(deleteDialog.row.id); await fetchBehavior() }
    else if (deleteDialog.type === 'observation') { await deleteCareObservation(deleteDialog.row.id); await fetchObservation() }
    else if (deleteDialog.type === 'family') { await deleteFamilyContact(deleteDialog.row.id); await fetchFamily() }
    else if (deleteDialog.type === 'graph') { await deleteGraphRelation(deleteDialog.row.id); await fetchGraphRelations() }
    emitDataChanged(deleteDialog.type); ElMessage.success('删除成功'); resetDeleteDialog()
  } catch (error) { console.error(error); deleteDialog.loading = false; ElMessage.error('删除失败，请稍后重试') }
}

function emitDataChanged(section) { emit('data-changed', { studentId: props.student?.id || null, section, updatedAt: Date.now() }) }
function statusLabel(v) { return ({ normal: '正常', late: '迟到', absent: '缺勤', early_leave: '早退' })[v] || v }
function behaviorTypeLabel(v) { return ({ discipline: '纪律事件', conflict: '冲突事件', warning: '预警事件', bullying: '欺凌线索', threat: '威胁线索', dorm_conflict: '宿舍冲突', cyber_conflict: '网络冲突' })[v] || v }
function observationTypeLabel(v) { return ({ care_talk: '关怀谈话', emotion_observation: '情绪观察', social_observation: '社交观察', safety_observation: '安全线索', study_observation: '学习观察', behavior_observation: '行为观察', follow_up: '后续跟进' })[v] || v }
function dimensionLabel(v) { return ({ emotion: '情绪状态', social: '社交融入', safety: '校园安全', family: '家庭支持', study: '学习压力', behavior: '行为稳定' })[v] || v }
function levelLabel(v) { return ({ low: '低', medium: '中', high: '高' })[v] || v }
function contactTypeLabel(v) { return ({ phone: '电话', meeting: '面谈', home_visit: '家访' })[v] || v }
function graphTargetTypeLabel(v) { return v === 'student' ? '关联同学' : '关联事件' }
function graphRelationTypeLabel(v) { return ({ peer_support: '同伴支持', conflict: '冲突关系', bullying_link: '欺凌关联', shared_activity: '共同活动', concern: '重点关注' })[v] || v }
function graphRelationTargetText(row) { return row.target_type === 'student' ? `${row.target_student_name || '未关联同学'}${row.target_student_no ? ` (${row.target_student_no})` : ''}` : (row.event_title || '未命名事件') }

function openGraphTab() {
  activeTab.value = 'graph'
}

function openCreateGraphRelation(prefill = {}) {
  activeTab.value = 'graph'
  resetGraphForm()
  Object.assign(graphForm, prefill)
  graphDialogVisible.value = true
}

async function openEditGraphRelationById(relationId) {
  if (!relationId) return
  activeTab.value = 'graph'
  if (!graphRelationList.value.length) {
    await fetchGraphRelations()
  }
  const row = graphRelationList.value.find((item) => item.id === relationId)
  if (row) {
    editGraphRelation(row)
  }
}

defineExpose({
  openGraphTab,
  openCreateGraphRelation,
  openEditGraphRelationById
})
</script>

<style scoped lang="scss">
.data-tabs { margin-top: 18px; padding: 16px 18px; border-radius: 18px; background: #fff; border: 1px solid rgba(148, 163, 184, 0.16); }
.tab-toolbar { margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.graph-toolbar-tip { font-size: 12px; line-height: 1.6; color: #64748b; }
</style>
