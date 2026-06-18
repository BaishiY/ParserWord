<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  CircleCheck,
  DataBoard,
  Delete,
  Document,
  Download,
  Files,
  Refresh,
  UploadFilled,
  WarningFilled,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

type ViewMode = 'summary' | 'stages' | 'json'

interface PumpScheduleItem {
  sequence: number
  phase: string
  phase_type: string
  rate_m3_per_min: number
  clean_vol_m3: number
  prop_conc_kg_per_m3: number
  fluid_viscosity_mpa_s: number
  cum_vol_m3: number
  cum_slurry_vol_m3: number
  cum_prop_t: number
  fluid_type: string
  proppant_type: string
}

interface StageData {
  stage_number: number
  top_md_m: number | null
  bottom_md_m: number | null
  length_m: number | null
  cluster_count: number | null
  classification: string
  design_params: Record<string, number | string | boolean | null>
  pump_schedule: PumpScheduleItem[]
}

interface ParseData {
  run_id: string
  file_name: string
  well_name: string
  total_stages: number
  casing_inner_diameter_mm: number | null
  default_pressure_limit_mpa: number | null
  stages: StageData[]
  raw_extract?: {
    paragraph_count?: number
    table_count?: number
  }
}

interface ParseResponse {
  success: boolean
  message: string
  run_id: string
  output_path: string
  data: ParseData
}

interface ResultSummary {
  run_id: string
  output_path: string
  size_bytes: number
  created_at: string
  file_name?: string
  well_name?: string
  total_stages?: number
  stage_count?: number
  parsed_at?: string
  warning?: string
}

interface ResultListResponse {
  success: boolean
  count: number
  results: ResultSummary[]
}

interface ResultDetailResponse {
  success: boolean
  run_id: string
  data: ParseData
}

const apiBase = import.meta.env.VITE_API_BASE ?? ''

const selectedFile = ref<File | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const isUploading = ref(false)
const isLoadingResults = ref(false)
const activeTab = ref<ViewMode>('summary')
const parseData = ref<ParseData | null>(null)
const currentRunId = ref('')
const results = ref<ResultSummary[]>([])

const hasData = computed(() => Boolean(parseData.value))
const stages = computed(() => parseData.value?.stages ?? [])
const jsonOutput = computed(() => JSON.stringify(parseData.value ?? {}, null, 2))
const selectedResult = computed(() => results.value.find((item) => item.run_id === currentRunId.value))

const summaryCards = computed(() => [
  { label: '井名', value: parseData.value?.well_name || '-' },
  { label: '压裂段数', value: parseData.value?.total_stages ?? '-' },
  { label: '套管内径', value: formatMetric(parseData.value?.casing_inner_diameter_mm, 'mm') },
  { label: '施工限压', value: formatMetric(parseData.value?.default_pressure_limit_mpa, 'MPa') },
  { label: '表格数量', value: parseData.value?.raw_extract?.table_count ?? '-' },
  { label: '段落数量', value: parseData.value?.raw_extract?.paragraph_count ?? '-' },
])

function apiUrl(path: string) {
  return `${apiBase}${path}`
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.length) {
    selectedFile.value = input.files[0]
  }
}

function onDragOver(event: DragEvent) {
  event.preventDefault()
  isDragging.value = true
}

function onDragLeave() {
  isDragging.value = false
}

function onDrop(event: DragEvent) {
  event.preventDefault()
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) {
    selectedFile.value = file
  }
}

async function readError(response: Response) {
  try {
    const body = await response.json()
    return body.detail || body.message || `HTTP ${response.status}`
  } catch {
    return `HTTP ${response.status}`
  }
}

async function uploadAndParse() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择 Word 文件')
    return
  }

  isUploading.value = true
  const formData = new FormData()
  formData.append('file', selectedFile.value)

  try {
    const response = await fetch(apiUrl('/api/parse-docx'), {
      method: 'POST',
      body: formData,
    })
    if (!response.ok) {
      throw new Error(await readError(response))
    }
    const payload = (await response.json()) as ParseResponse
    parseData.value = payload.data
    currentRunId.value = payload.run_id
    activeTab.value = 'summary'
    await refreshResults(false)
    ElMessage.success(payload.message || '解析完成')
  } catch (error) {
    ElMessage.error(`解析失败：${error instanceof Error ? error.message : '未知错误'}`)
  } finally {
    isUploading.value = false
  }
}

async function refreshResults(showMessage = true) {
  isLoadingResults.value = true
  try {
    const response = await fetch(apiUrl('/api/parse-results'))
    if (!response.ok) {
      throw new Error(await readError(response))
    }
    const payload = (await response.json()) as ResultListResponse
    results.value = payload.results
    if (showMessage) ElMessage.success('历史结果已刷新')
  } catch (error) {
    ElMessage.error(`结果列表获取失败：${error instanceof Error ? error.message : '未知错误'}`)
  } finally {
    isLoadingResults.value = false
  }
}

async function loadResult(runId: string) {
  try {
    const response = await fetch(apiUrl(`/api/parse-results/${encodeURIComponent(runId)}`))
    if (!response.ok) {
      throw new Error(await readError(response))
    }
    const payload = (await response.json()) as ResultDetailResponse
    parseData.value = payload.data
    currentRunId.value = payload.run_id
    activeTab.value = 'summary'
  } catch (error) {
    ElMessage.error(`结果读取失败：${error instanceof Error ? error.message : '未知错误'}`)
  }
}

function downloadResult(runId = currentRunId.value) {
  if (!runId) return
  const link = document.createElement('a')
  link.href = apiUrl(`/api/parse-results/${encodeURIComponent(runId)}/download`)
  link.download = `${runId}.json`
  document.body.appendChild(link)
  link.click()
  link.remove()
}

async function removeResult(runId: string) {
  try {
    await ElMessageBox.confirm('删除后将移除 JSON 结果，并默认删除对应上传文件。', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const response = await fetch(apiUrl(`/api/parse-results/${encodeURIComponent(runId)}`), {
      method: 'DELETE',
    })
    if (!response.ok) {
      throw new Error(await readError(response))
    }
    if (currentRunId.value === runId) {
      parseData.value = null
      currentRunId.value = ''
    }
    await refreshResults(false)
    ElMessage.success('删除完成')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`删除失败：${error instanceof Error ? error.message : '未知错误'}`)
    }
  }
}

function formatMetric(value: number | null | undefined, unit: string) {
  if (value === null || value === undefined) return '-'
  return `${value}${unit}`
}

function formatNumber(value: number | string | boolean | null | undefined, unit = '') {
  if (value === null || value === undefined || value === '') return '-'
  return `${value}${unit}`
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function shortRunId(runId: string) {
  return runId.length > 30 ? `${runId.slice(0, 24)}...` : runId
}

function stageParam(stage: StageData, key: string) {
  return stage.design_params?.[key]
}

onMounted(() => {
  refreshResults(false)
})
</script>

<template>
  <div class="app-root">
    <aside class="left-panel">
      <div class="brand">
        <DataBoard class="brand-icon" />
        <div>
          <h1>压裂设计解析</h1>
          <p>Word 读取 · 智能分析 · JSON 存储</p>
        </div>
      </div>

      <input
        ref="fileInputRef"
        class="hidden-input"
        type="file"
        accept=".doc,.docx"
        @change="onFileSelected"
      />

      <section class="upload-zone" :class="{ dragging: isDragging }" @dragover="onDragOver" @dragleave="onDragLeave" @drop="onDrop">
        <button class="upload-select" type="button" @click="triggerFileInput">
          <UploadFilled class="upload-icon" />
          <span>{{ selectedFile ? selectedFile.name : '选择 Word 文档' }}</span>
          <small>{{ selectedFile ? formatSize(selectedFile.size) : '支持 .doc / .docx，或拖拽到这里' }}</small>
        </button>
        <el-button class="parse-button" type="primary" :loading="isUploading" :disabled="!selectedFile" @click="uploadAndParse">
          开始解析
        </el-button>
      </section>

      <section class="history-panel">
        <div class="panel-title">
          <span>历史结果</span>
          <el-button size="small" :icon="Refresh" text :loading="isLoadingResults" @click="refreshResults()" />
        </div>

        <div v-if="results.length" class="result-list">
          <article
            v-for="item in results"
            :key="item.run_id"
            class="result-item"
            :class="{ active: item.run_id === currentRunId }"
          >
            <button class="result-main" type="button" @click="loadResult(item.run_id)">
              <strong>{{ item.well_name || item.file_name || '未命名结果' }}</strong>
              <span>{{ shortRunId(item.run_id) }}</span>
              <small>{{ item.stage_count ?? 0 }} 段 · {{ formatSize(item.size_bytes) }}</small>
            </button>
            <div class="result-actions">
              <el-button size="small" :icon="Download" text @click="downloadResult(item.run_id)" />
              <el-button size="small" :icon="Delete" text type="danger" @click="removeResult(item.run_id)" />
            </div>
          </article>
        </div>
        <div v-else class="empty-history">
          <Files class="empty-icon" />
          <span>暂无历史 JSON</span>
        </div>
      </section>
    </aside>

    <main class="workspace">
      <header class="workspace-header">
        <div>
          <h2>{{ parseData?.well_name || '等待解析文件' }}</h2>
          <p v-if="parseData">{{ parseData.file_name }} · {{ currentRunId }}</p>
          <p v-else>上传 Word 后，解析结果会显示在这里。</p>
        </div>
        <div class="header-actions" v-if="hasData">
          <el-button :icon="Download" @click="downloadResult()">下载 JSON</el-button>
          <el-button :icon="Delete" type="danger" plain @click="removeResult(currentRunId)">删除结果</el-button>
        </div>
      </header>

      <nav class="view-tabs">
        <button :class="{ active: activeTab === 'summary' }" type="button" @click="activeTab = 'summary'">
          <CircleCheck />
          摘要
        </button>
        <button :class="{ active: activeTab === 'stages' }" type="button" @click="activeTab = 'stages'">
          <DataBoard />
          分段
        </button>
        <button :class="{ active: activeTab === 'json' }" type="button" @click="activeTab = 'json'">
          <Document />
          JSON
        </button>
      </nav>

      <section class="content-area">
        <div v-if="!hasData" class="empty-state">
          <UploadFilled class="empty-main-icon" />
          <h3>还没有解析结果</h3>
          <p>先在左侧上传压裂设计 Word 文件，或从历史结果中选择一条记录。</p>
        </div>

        <template v-else>
          <section v-show="activeTab === 'summary'" class="summary-view">
            <div class="summary-grid">
              <article v-for="card in summaryCards" :key="card.label" class="metric-card">
                <span>{{ card.label }}</span>
                <strong>{{ card.value }}</strong>
              </article>
            </div>

            <div class="detail-band">
              <div>
                <h3>当前结果</h3>
                <p>{{ selectedResult?.output_path || '结果已返回，但暂未匹配到本地路径。' }}</p>
              </div>
              <el-tag v-if="selectedResult" type="success">已存储</el-tag>
              <el-tag v-else type="warning">新结果</el-tag>
            </div>

            <el-table :data="stages.slice(0, 8)" stripe size="small" class="preview-table">
              <el-table-column prop="stage_number" label="段号" width="80" />
              <el-table-column prop="classification" label="分类" width="120" />
              <el-table-column prop="length_m" label="段长(m)" width="100" />
              <el-table-column label="最大排量" width="110">
                <template #default="{ row }">{{ formatNumber(stageParam(row, 'max_rate_m3_per_min'), ' m³/min') }}</template>
              </el-table-column>
              <el-table-column label="暂堵次数" width="100">
                <template #default="{ row }">{{ formatNumber(stageParam(row, 'temporary_plugging_times')) }}</template>
              </el-table-column>
              <el-table-column label="泵注阶段">
                <template #default="{ row }">{{ row.pump_schedule?.length || 0 }} 行</template>
              </el-table-column>
            </el-table>
          </section>

          <section v-show="activeTab === 'stages'" class="stages-view">
            <el-table :data="stages" stripe height="100%" size="small">
              <el-table-column prop="stage_number" label="段号" width="70" fixed />
              <el-table-column prop="classification" label="分类" width="120" />
              <el-table-column prop="top_md_m" label="顶深(m)" width="100" />
              <el-table-column prop="bottom_md_m" label="底深(m)" width="100" />
              <el-table-column prop="length_m" label="段长(m)" width="95" />
              <el-table-column label="最大排量" width="110">
                <template #default="{ row }">{{ formatNumber(stageParam(row, 'max_rate_m3_per_min')) }}</template>
              </el-table-column>
              <el-table-column label="粉砂浓度" width="150">
                <template #default="{ row }">
                  {{ formatNumber(stageParam(row, 'sand_stage_min_conc_kg_per_m3')) }} -
                  {{ formatNumber(stageParam(row, 'sand_stage_max_conc_kg_per_m3')) }}
                </template>
              </el-table-column>
              <el-table-column label="陶粒浓度" width="150">
                <template #default="{ row }">
                  {{ formatNumber(stageParam(row, 'ceramic_stage_min_conc_kg_per_m3')) }} -
                  {{ formatNumber(stageParam(row, 'ceramic_stage_max_conc_kg_per_m3')) }}
                </template>
              </el-table-column>
              <el-table-column label="暂堵次数" width="100">
                <template #default="{ row }">{{ formatNumber(stageParam(row, 'temporary_plugging_times')) }}</template>
              </el-table-column>
              <el-table-column label="泵注程序" min-width="120">
                <template #default="{ row }">{{ row.pump_schedule?.length || 0 }} 行</template>
              </el-table-column>
            </el-table>
          </section>

          <section v-show="activeTab === 'json'" class="json-view">
            <div class="json-toolbar">
              <span>解析 JSON 数据体</span>
              <el-button size="small" :icon="Download" @click="downloadResult()">下载</el-button>
            </div>
            <pre><code>{{ jsonOutput }}</code></pre>
          </section>
        </template>
      </section>
    </main>

    <div class="service-tip">
      <WarningFilled />
      <span>请确保后端已启动：uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload</span>
    </div>
  </div>
</template>

<style scoped>
.app-root {
  display: grid;
  grid-template-columns: 340px 1fr;
  height: 100vh;
  width: 100vw;
  background: #0d1117;
  color: #e6edf3;
  overflow: hidden;
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
  padding: 22px;
  background: #151b23;
  border-right: 1px solid #30363d;
  overflow: hidden;
}

.brand {
  display: flex;
  gap: 12px;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid #30363d;
}

.brand-icon {
  width: 32px;
  height: 32px;
  color: #58a6ff;
}

.brand h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}

.brand p {
  margin: 3px 0 0;
  color: #8b949e;
  font-size: 12px;
}

.hidden-input {
  display: none;
}

.upload-zone {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  border: 1px dashed #484f58;
  border-radius: 8px;
  background: #0d1117;
}

.upload-zone.dragging {
  border-color: #58a6ff;
  background: rgba(88, 166, 255, 0.1);
}

.upload-select {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  min-height: 112px;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.upload-select span {
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 600;
}

.upload-select small {
  color: #8b949e;
}

.upload-icon {
  width: 34px;
  height: 34px;
  color: #58a6ff;
}

.parse-button {
  width: 100%;
}

.history-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  color: #c9d1d9;
  font-size: 14px;
  font-weight: 700;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: auto;
  padding-right: 2px;
}

.result-item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  align-items: center;
  border: 1px solid #30363d;
  border-radius: 8px;
  padding: 10px;
  background: #0d1117;
}

.result-item.active {
  border-color: #58a6ff;
  background: rgba(88, 166, 255, 0.1);
}

.result-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  border: 0;
  padding: 0;
  text-align: left;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.result-main strong,
.result-main span,
.result-main small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-main strong {
  font-size: 13px;
}

.result-main span,
.result-main small {
  color: #8b949e;
  font-size: 11px;
}

.result-actions {
  display: flex;
  align-items: center;
}

.empty-history {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 120px;
  color: #8b949e;
  border: 1px solid #30363d;
  border-radius: 8px;
}

.empty-icon {
  width: 20px;
  height: 20px;
}

.workspace {
  display: flex;
  min-width: 0;
  flex-direction: column;
  overflow: hidden;
}

.workspace-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  padding: 24px 30px 16px;
  border-bottom: 1px solid #21262d;
}

.workspace-header h2 {
  margin: 0;
  font-size: 22px;
}

.workspace-header p {
  margin: 6px 0 0;
  color: #8b949e;
  font-size: 13px;
}

.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.view-tabs {
  display: flex;
  gap: 6px;
  padding: 14px 30px 0;
}

.view-tabs button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 34px;
  padding: 0 14px;
  border: 1px solid transparent;
  border-radius: 8px 8px 0 0;
  background: transparent;
  color: #8b949e;
  cursor: pointer;
}

.view-tabs svg {
  width: 16px;
  height: 16px;
}

.view-tabs button.active {
  color: #58a6ff;
  border-color: #30363d;
  border-bottom-color: #0d1117;
  background: #0d1117;
}

.content-area {
  min-height: 0;
  flex: 1;
  overflow: auto;
  padding: 18px 30px 58px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 420px;
  color: #8b949e;
  text-align: center;
}

.empty-state h3 {
  margin: 12px 0 6px;
  color: #e6edf3;
}

.empty-main-icon {
  width: 48px;
  height: 48px;
  color: #58a6ff;
}

.summary-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(160px, 1fr));
  gap: 12px;
}

.metric-card {
  min-height: 92px;
  padding: 16px;
  border: 1px solid #30363d;
  border-radius: 8px;
  background: #151b23;
}

.metric-card span {
  color: #8b949e;
  font-size: 12px;
}

.metric-card strong {
  display: block;
  margin-top: 10px;
  font-size: 24px;
  color: #f0f6fc;
}

.detail-band {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 16px;
  border: 1px solid #30363d;
  border-radius: 8px;
  background: #10161f;
}

.detail-band h3 {
  margin: 0 0 6px;
  font-size: 15px;
}

.detail-band p {
  margin: 0;
  color: #8b949e;
  word-break: break-all;
}

.preview-table,
.stages-view {
  border: 1px solid #30363d;
  border-radius: 8px;
  overflow: hidden;
}

.stages-view {
  height: 100%;
  min-height: 520px;
}

.json-view {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.json-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #c9d1d9;
}

.json-view pre {
  margin: 0;
  padding: 18px;
  min-height: 560px;
  overflow: auto;
  border: 1px solid #30363d;
  border-radius: 8px;
  background: #0b1017;
  color: #c9d1d9;
  font-size: 13px;
  line-height: 1.55;
}

.service-tip {
  position: fixed;
  right: 18px;
  bottom: 14px;
  display: flex;
  gap: 8px;
  align-items: center;
  max-width: min(720px, calc(100vw - 36px));
  padding: 8px 12px;
  border: 1px solid #30363d;
  border-radius: 8px;
  background: rgba(13, 17, 23, 0.92);
  color: #8b949e;
  font-size: 12px;
}

.service-tip svg {
  width: 16px;
  height: 16px;
  color: #d29922;
  flex-shrink: 0;
}

:deep(.el-table) {
  --el-table-bg-color: #151b23;
  --el-table-tr-bg-color: #151b23;
  --el-table-header-bg-color: #10161f;
  --el-table-header-text-color: #c9d1d9;
  --el-table-text-color: #e6edf3;
  --el-table-border-color: #30363d;
  --el-table-row-hover-bg-color: #1f2937;
}

@media (max-width: 980px) {
  .app-root {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }

  .left-panel {
    max-height: 44vh;
    border-right: 0;
    border-bottom: 1px solid #30363d;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(140px, 1fr));
  }
}
</style>
