<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { UploadFilled, DataBoard, Document, Setting, QuestionFilled, CircleCheck, MagicStick, Delete, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

interface DataItem { id: number; key: string; value: string }
interface ParseResponse { items: DataItem[]; message?: string }

const DEMO_DATA: DataItem[] = [
  { id: 1, key: '组织机构', value: '技术研发中心' },
  { id: 2, key: '核心目标', value: 'Q2 产品交付率提升至 95%' },
  { id: 3, key: '关键结果 1', value: '完成 3 个主要版本迭代' },
  { id: 4, key: '关键结果 2', value: '缺陷率降低 40%' },
  { id: 5, key: '关键结果 3', value: '自动化测试覆盖率达 85%' },
  { id: 6, key: '服务器名称', value: 'Production-Node-01' },
  { id: 7, key: 'CPU 使用率', value: '67.3%' },
  { id: 8, key: '内存使用率', value: '82.1%' },
  { id: 9, key: '磁盘 IOPS', value: '2,340 ops/s' },
  { id: 10, key: '网络吞吐量', value: '1.2 Gbps' },
  { id: 11, key: '运行时长', value: '142 天 6 小时' },
]

const activeTab = ref('grid')
const tableData = ref<DataItem[]>([])
const editingCell = ref<{ rowId: number; field: 'key' | 'value' } | null>(null)
const editingValue = ref('')
const hasData = ref(false)
const isDragging = ref(false)
const isLoading = ref(false)
const selectedFile = ref<File | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

const jsonOutput = computed(() => {
  const obj: Record<string, string> = {}
  for (const item of tableData.value) obj[item.key] = item.value
  return JSON.stringify(obj, null, 2)
})

function loadDemo() {
  tableData.value = DEMO_DATA.map(i => ({ ...i }))
  hasData.value = true
  activeTab.value = 'grid'
  ElMessage({ message: 'Demo \u6570\u636E\u5DF2\u52A0\u8F7D', type: 'success', duration: 2000, offset: 60 })
}

function triggerFileInput() { fileInputRef.value?.click() }
function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) selectedFile.value = input.files[0]
}

function hDragOver(e: DragEvent) { e.preventDefault(); isDragging.value = true }
function hDragLeave() { isDragging.value = false }
function hDrop(e: DragEvent) {
  e.preventDefault(); isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) selectedFile.value = file
}

async function uploadAndParse() {
  if (!selectedFile.value) return
  isLoading.value = true
  hasData.value = false
  const fd = new FormData()
  fd.append('file', selectedFile.value)
  try {
    const res = await fetch('/api/parse-docx', { method: 'POST', body: fd })
    if (!res.ok) throw new Error('HTTP ' + res.status)
    const json: ParseResponse = await res.json()
    if (json.items?.length) {
      tableData.value = json.items; hasData.value = true; activeTab.value = 'grid'
      ElMessage({ message: '\u89E3\u6790\u5B8C\u6210\uFF0C\u5171 ' + json.items.length + ' \u6761\u8BB0\u5F55', type: 'success', duration: 2000, offset: 60 })
    } else {
      ElMessage({ message: json.message || '\u6587\u6863\u4E2D\u672A\u8BC6\u522B\u5230\u6570\u636E', type: 'warning', duration: 3000, offset: 60 })
    }
  } catch (err) {
    ElMessage({ message: '\u6587\u6863\u89E3\u6790\u5931\u8D25\uFF0C\u8BF7\u68C0\u67E5\u540E\u7AEF\u670D\u52A1', type: 'error', duration: 3000, offset: 60 })
  } finally { isLoading.value = false }
}

function startEdit(id: number, fld: 'key' | 'value', cur: string) {
  editingCell.value = { rowId: id, field: fld }; editingValue.value = cur
  nextTick(() => { const inp = document.querySelector('.inline-edit-input input') as HTMLInputElement; inp?.focus(); inp?.select() })
}
function confirmEdit() {
  if (!editingCell.value) return
  const it = tableData.value.find(d => d.id === editingCell.value!.rowId)
  if (it && editingValue.value.trim()) it[editingCell.value.field] = editingValue.value.trim()
  editingCell.value = null; editingValue.value = ''
}
function cancelEdit() { editingCell.value = null; editingValue.value = '' }
function handleCellClick(row: DataItem) { startEdit(row.id, 'value', row.value) }
function handleKeyDblClick(row: DataItem) { startEdit(row.id, 'key', row.key) }
function clearData() { tableData.value = []; hasData.value = false; editingCell.value = null }
function downloadJson() {
  const b = new Blob([jsonOutput.value], { type: 'application/json' })
  const u = URL.createObjectURL(b); const a = document.createElement('a')
  a.href = u; a.download = 'data.json'; a.click(); URL.revokeObjectURL(u)
}
const tabThemeClass = computed(() => 'tab-theme--' + activeTab.value)
</script>

<template>
  <div class="app-root" :class="tabThemeClass">
    <aside class="left-panel">
      <div class="panel-header">
        <div class="brand">
          <DataBoard class="brand-icon" />
          <div class="brand-text">
            <span class="brand-title">数据解析工作台</span>
            <span class="brand-sub">Data Parser Studio</span>
          </div>
        </div>
     </div>

      <input ref="fileInputRef" type="file" accept=".doc,.docx" style="display:none" @change="onFileSelected" />
      <div ref="uploadRef" class="upload-zone" :class="{ 'is-dragover': isDragging }"
        @dragover="hDragOver" @dragleave="hDragLeave" @drop="hDrop">
        <div class="upload-placeholder" @click="triggerFileInput">
            <template v-if="!selectedFile">
              <UploadFilled class="upload-icon" />
              <p class="upload-text">点击选择 Word 文档</p>
              <p class="upload-hint">支持 .doc / .docx 格式</p>
            </template>
            <template v-else>
              <Document class="upload-icon" />
              <p class="upload-text">{{ selectedFile.name }}</p>
              <p class="upload-hint">{{ (selectedFile.size / 1024).toFixed(1) }} KB</p>
            </template>
        </div>
        <button v-if="selectedFile && !isLoading" class="parse-btn" @click="uploadAndParse">
          <MagicStick class="btn-icon" />
          <span>解析文档</span>
        </button>
       <div class="loading-spinner" v-if="isLoading"></div>
      </div>
      <div class="demo-section">
        <button class="demo-btn" @click="loadDemo">
          <MagicStick class="btn-icon" />
          <span class="btn-label">一键加载 Demo</span>
        </button>
        <p class="demo-hint">免文件启动 · 含部门 OKR 与服务器指标数据</p>
      </div>

      <div class="settings-section" v-if="hasData">
        <div class="section-title">
          <Setting class="section-icon" />
          <span>服务配置</span>
        </div>
        <div class="settings-body">
          <div class="setting-row">
            <label class="setting-label">视图模式</label>
            <el-radio-group v-model="activeTab" size="small">
              <el-radio-button value="grid">表格</el-radio-button>
              <el-radio-button value="json">JSON</el-radio-button>
            </el-radio-group>
          </div>
          <div class="setting-row">
            <label class="setting-label">数据操作</label>
            <div class="action-row">
              <el-button size="small" :icon="Download" @click="downloadJson">导出 JSON</el-button>
              <el-button size="small" :icon="Delete" type="danger" plain @click="clearData">清除</el-button>
            </div>
          </div>
        </div>
      </div>

      <div class="help-section">
        <div class="section-title">
          <QuestionFilled class="section-icon" />
          <span>快速指引</span>
        </div>
        <ul class="help-list">
          <li><CircleCheck class="check-icon" /> 单击单元格编辑值</li>
          <li><CircleCheck class="check-icon" /> 双击键名编辑字段名</li>
          <li><CircleCheck class="check-icon" /> JSON 同步实时更新</li>
        </ul>
      </div>

      <div class="panel-footer"><span>v1.1.0</span></div>
    </aside>

    <main class="right-panel">
      <div class="right-header">
        <h2 class="right-title">
          <template v-if="activeTab === 'grid'">表格可视化</template>
          <template v-else>JSON 数据结构</template>
        </h2>
        <span class="right-meta" v-if="hasData">{{ tableData.length }} 条记录</span>
        <span class="right-meta muted" v-else>等待数据加载...</span>
      </div>

      <div class="tab-bar">
        <button class="tab-btn" :class="{ active: activeTab === 'grid' }" @click="activeTab = 'grid'">
          <DataBoard class="tab-btn-icon" />
          <span>Grid</span>
        </button>
        <button class="tab-btn" :class="{ active: activeTab === 'json' }" @click="activeTab = 'json'">
          <Document class="tab-btn-icon" />
          <span>JSON</span>
        </button>
      </div>

     <div class="tab-content">
        <div class="grid-view" v-show="activeTab === 'grid'">
           <div class="table-wrap" v-if="hasData">
             <el-table :data="tableData" stripe highlight-current-row size="small" style="width: 100%" :cell-style="{ cursor: 'pointer' }">
               <el-table-column type="index" label="#" width="48" fixed />
                <el-table-column prop="key" label="键名 (Key)" min-width="180">
                  <template #default="{ row }">
                    <div class="cell-content">
                      <template v-if="editingCell?.rowId === row.id && editingCell?.field === 'key'">
                        <el-input v-model="editingValue" size="small" class="inline-edit-input"
                          @blur="confirmEdit" @keyup.enter="confirmEdit" @keyup.escape="cancelEdit" />
                      </template>
                      <span v-else class="cell-key" @dblclick.stop="handleKeyDblClick(row)" title="双击编辑键名">{{ row.key }}</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="value" label="值 (Value)" min-width="240">
                  <template #default="{ row }">
                    <div class="cell-content">
                      <template v-if="editingCell?.rowId === row.id && editingCell?.field === 'value'">
                        <el-input v-model="editingValue" size="small" class="inline-edit-input"
                          @blur="confirmEdit" @keyup.enter="confirmEdit" @keyup.escape="cancelEdit" />
                      </template>
                      <span v-else class="cell-value" @click.stop="handleCellClick(row)" title="单击编辑值">{{ row.value }}</span>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div class="empty-state" v-else>
              <UploadFilled class="empty-icon" />
              <p class="empty-text">暂无数据</p>
              <p class="empty-hint">通过左侧上传文件或点击 Demo 加载示例数据</p>
           </div>
         </div>

        <div class="code-view" v-show="activeTab === 'json'">
           <div class="code-toolbar">
             <span class="code-lang">JSON</span>
             <el-button size="small" :icon="Download" text @click="downloadJson">下载</el-button>
           </div>
           <pre class="code-block" v-if="hasData"><code>{{ jsonOutput }}</code></pre>
            <div class="empty-state" v-else>
              <Document class="empty-icon" />
              <p class="empty-text">暂无 JSON 数据</p>
           </div>
         </div>
     </div>
    </main>
  </div>
</template>

<style scoped>
.app-root {
  --color-grid: #58a6ff;
  --color-json: #3fb950;
  --color-grid-soft: rgba(88, 166, 255, 0.12);
  --color-json-soft: rgba(63, 185, 80, 0.12);
  --left-bg: #161b22;
  --left-border: #30363d;
  --text-primary: #e6edf3;
  --text-secondary: #8b949e;
  --text-muted: #6e7681;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --transition-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: #0d1117;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: var(--text-primary);
}

.left-panel {
  width: 320px;
  min-width: 320px;
  background: var(--left-bg);
  border-right: 1px solid var(--left-border);
  display: flex;
  flex-direction: column;
  padding: 24px 20px;
  box-sizing: border-box;
  overflow-y: auto;
  gap: 18px;
}

.panel-header { padding-bottom: 14px; border-bottom: 1px solid var(--left-border) }
.brand { display: flex; align-items: center; gap: 10px }
.brand-icon { width: 28px; height: 28px; color: var(--color-grid); transition: color 0.4s var(--transition-spring) }
.tab-theme--json .brand-icon { color: var(--color-json) }
.brand-text { display: flex; flex-direction: column }
.brand-title { font-size: 16px; font-weight: 600; line-height: 1.3 }
.brand-sub { font-size: 11px; color: var(--text-muted); letter-spacing: 0.3px }

.upload-zone {
  border: 2px dashed #484f5a;
  border-radius: var(--radius-md);
  padding: 18px 12px;
  text-align: center;
  transition: all 0.35s var(--transition-spring);
  background: rgba(255,255,255,0.03);
}
.upload-zone.is-dragover { border-color: var(--color-grid); background: var(--color-grid-soft); transform: scale(1.02) }
.tab-theme--json .upload-zone.is-dragover { border-color: var(--color-json); background: var(--color-json-soft) }
.upload-inner { width: 100% }
.upload-placeholder { display: flex; flex-direction: column; align-items: center; gap: 6px; cursor: pointer }
.upload-icon { width: 32px; height: 32px; color: #484f5a; transition: color 0.3s, transform 0.35s var(--transition-spring) }
.upload-zone:hover .upload-icon { color: var(--color-grid); transform: translateY(-2px) }
.tab-theme--json .upload-zone:hover .upload-icon { color: var(--color-json) }
.spinning { animation: spin 1s linear infinite }
@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }
.upload-text { font-size: 14px; font-weight: 500; margin: 0; color: var(--text-primary) }
.upload-hint { font-size: 11px; margin: 0; color: var(--text-muted) }
.loading-spinner { width: 32px; height: 32px; border: 3px solid #484f5a; border-top-color: var(--color-grid); border-radius: 50%; animation: spin 0.8s linear infinite }
.upload-zone .parse-btn { margin-top: 12px; width: 100%; padding: 10px 16px; border: none; border-radius: var(--radius-sm); background: var(--color-grid); color: #fff; font-size: 14px; font-weight: 500; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; transition: all 0.25s var(--transition-spring) }
.upload-zone .parse-btn:hover { filter: brightness(1.1); transform: translateY(-1px) }
.upload-zone .parse-btn:active { transform: translateY(0) }
.tab-theme--json .upload-zone .parse-btn { background: var(--color-json) }
.tab-theme--json .loading-spinner { border-top-color: var(--color-json) }

.demo-section { display: flex; flex-direction: column; gap: 8px }
.demo-btn {
  display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%;
  padding: 12px 16px; border: none; border-radius: var(--radius-sm);
  background: linear-gradient(135deg, #58a6ff, #1d7cf2); color: #fff;
  font-size: 14px; font-weight: 500; cursor: pointer;
  transition: all 0.3s var(--transition-spring);
  box-shadow: 0 2px 8px rgba(88, 166, 255, 0.25);
}
.demo-btn:hover { transform: translateY(-1px) scale(1.01); box-shadow: 0 4px 16px rgba(88, 166, 255, 0.35) }
.demo-btn:active { transform: translateY(0) scale(0.98) }
.tab-theme--json .demo-btn { background: linear-gradient(135deg, #3fb950, #2d8a3e); box-shadow: 0 2px 8px rgba(63, 185, 80, 0.25) }
.tab-theme--json .demo-btn:hover { box-shadow: 0 4px 16px rgba(63, 185, 80, 0.35) }
.btn-icon { width: 18px; height: 18px }
.demo-hint { font-size: 11px; color: var(--text-muted); margin: 0; text-align: center }

.settings-section { background: rgba(255,255,255,0.04); border-radius: var(--radius-md); padding: 14px 16px; border: 1px solid var(--left-border); animation: slideDown 0.35s var(--transition-spring) }
.section-title { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 12px }
.section-icon { width: 16px; height: 16px }
.settings-body { display: flex; flex-direction: column; gap: 12px }
.setting-row { display: flex; flex-direction: column; gap: 6px }
.setting-label { font-size: 12px; color: var(--text-muted) }
.action-row { display: flex; gap: 8px; flex-wrap: wrap }

.help-section { margin-top: auto }
.help-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px }
.help-list li { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-secondary) }
.check-icon { width: 14px; height: 14px; color: var(--color-grid); flex-shrink: 0 }
.tab-theme--json .check-icon { color: var(--color-json) }
.panel-footer { padding-top: 12px; border-top: 1px solid var(--left-border); font-size: 11px; color: var(--text-muted); text-align: center }

.right-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: #0d1117 }
.right-header { display: flex; align-items: baseline; gap: 12px; padding: 20px 28px 0 }
.right-title { font-size: 18px; font-weight: 600; margin: 0; transition: color 0.3s }
.tab-theme--grid .right-title { color: var(--color-grid) }
.tab-theme--json .right-title { color: var(--color-json) }
.right-meta { font-size: 12px; padding: 2px 10px; border-radius: 20px; background: var(--color-grid-soft); color: var(--color-grid); font-weight: 500; transition: all 0.3s }
.right-meta.muted { background: #21262d; color: var(--text-muted) }
.tab-theme--json .right-meta:not(.muted) { background: var(--color-json-soft); color: var(--color-json) }

.tab-bar { display: flex; gap: 4px; padding: 16px 28px 0; border-bottom: 1px solid #21262d }
.tab-btn {
  display: flex; align-items: center; gap: 6px; padding: 8px 20px; border: none;
  background: transparent; color: var(--text-muted); font-size: 13px; font-weight: 500;
  cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px;
  transition: all 0.25s var(--transition-spring); border-radius: 6px 6px 0 0;
}
.tab-btn:hover { color: var(--text-primary); background: #1c2333 }
.tab-btn.active { color: var(--color-grid); border-bottom-color: var(--color-grid); background: var(--color-grid-soft) }
.tab-theme--json .tab-btn.active { color: var(--color-json); border-bottom-color: var(--color-json); background: var(--color-json-soft) }
.tab-btn-icon { width: 16px; height: 16px }

.tab-content { flex: 1; overflow: auto; padding: 16px 28px 28px }
.grid-view { height: 100% }
.table-wrap { border: 1px solid #21262d; border-radius: var(--radius-md); overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.3) }
.cell-content { min-height: 28px; display: flex; align-items: center }
.cell-key { cursor: default; font-weight: 500; color: var(--text-primary); padding: 2px 4px; border-radius: 4px; transition: background 0.15s }
.cell-key:hover { background: rgba(63,185,80,0.10) }
.cell-value { cursor: pointer; padding: 2px 4px; border-radius: 4px; transition: all 0.2s; border: 1px solid transparent }
.cell-value:hover { background: #1c2333; border-color: #30363d }
.inline-edit-input { width: 100% }

.code-view { display: flex; flex-direction: column; height: 100% }
.code-toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px }
.code-lang { font-size: 12px; font-weight: 600; padding: 2px 10px; border-radius: 20px; background: var(--color-json-soft); color: var(--color-json) }
.code-block {
  flex: 1; margin: 0; padding: 18px 20px; background: #1a1b26; color: #c9d1d9;
  border-radius: var(--radius-md); font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
  font-size: 13px; line-height: 1.6; overflow: auto; white-space: pre; tab-size: 2; border: 1px solid #2e303a;
}
.code-block code { font-family: inherit; background: transparent; color: inherit; padding: 0 }

.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 260px; gap: 10px; color: var(--text-muted) }
.empty-icon { width: 40px; height: 40px; opacity: 0.5 }
.empty-text { font-size: 15px; font-weight: 500; margin: 0 }
.empty-hint { font-size: 12px; margin: 0; color: var(--text-muted) }

@keyframes slideDown { from { opacity: 0; transform: translateY(-8px) } to { opacity: 1; transform: translateY(0) } }

:deep(.el-table__header th.el-table__cell) { background: #1c2333; color: var(--text-secondary); font-weight: 600; font-size: 12px }
:deep(.el-table--small .el-table__cell) { padding: 6px 8px }
:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) { background: #161b22 }
.upload-placeholder { cursor: pointer }
:deep(.el-radio-group--small .el-radio-button__inner) { font-size: 12px; padding: 4px 12px }
:deep(.el-button--small) { font-size: 12px }
</style>
