<template>
  <div class="edit-view" v-if="scriptData">
    <div class="edit-layout">
      <!-- 左侧：场次列表面板 -->
      <aside class="scene-panel">
        <div class="panel-header">
          <div class="ph-left">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/></svg>
            <span>场次列表</span>
            <span class="scene-total">{{ scriptData.script_scenes.length }}</span>
          </div>
          <button class="add-scene-btn" @click="addScene">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
        </div>

        <div class="scene-list">
          <div
            v-for="(scene, index) in scriptData.script_scenes"
            :key="scene.scene_id"
            class="scene-item"
            :class="{ active: activeSceneId === scene.scene_id }"
            @click="activeSceneId = scene.scene_id"
          >
            <div class="item-serial">{{ scene.scene_serial }}</div>
            <div class="item-info">
              <span class="item-location">{{ scene.scene_attr.location || '未命名场景' }}</span>
              <span class="item-meta">
                <span class="meta-dot" :class="scene.scene_attr.scene_type === '内景' ? 'int' : 'ext'"></span>
                {{ scene.scene_attr.time_type }}
              </span>
            </div>
            <button
              class="delete-btn"
              title="删除场次"
              @click.stop="deleteScene(index)"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
            </button>
          </div>
        </div>

        <!-- 面板底部统计 -->
        <div class="panel-footer">
          <span>{{ currentScene?.scene_content.length || 0 }} 个单元</span>
        </div>
      </aside>

      <!-- 右侧：编辑区域 -->
      <main class="editor-panel">
        <template v-if="currentScene">
          <!-- 场景属性编辑 -->
          <section class="attr-section">
            <div class="sec-header">
              <span class="sec-badge">{{ currentScene.scene_serial }}</span>
              <h3>场景属性</h3>
              <div class="sec-tags">
                <span class="tag" :class="currentScene.scene_attr.scene_type === '内景' ? 'tag-int' : 'tag-ext'">
                  {{ currentScene.scene_attr.scene_type }}
                </span>
                <span class="tag tag-time">{{ currentScene.scene_attr.time_type }}</span>
                <span class="tag tag-loc">{{ currentScene.scene_attr.location || '—' }}</span>
              </div>
            </div>

            <div class="attr-grid">
              <div class="attr-field full">
                <label>剧情概要</label>
                <el-input v-model="currentScene.scene_summary" type="textarea" :rows="2" resize="vertical" />
              </div>
              <div class="attr-field full">
                <label>改编备注</label>
                <el-input v-model="currentScene.scene_note" type="textarea" :rows="2" resize="vertical" />
              </div>
              <div class="attr-field">
                <label>地点</label>
                <el-input v-model="currentScene.scene_attr.location" placeholder="输入地点..." />
              </div>
              <div class="attr-field">
                <label>内外景</label>
                <el-select v-model="currentScene.scene_attr.scene_type" style="width: 100%">
                  <el-option label="内景 INT." value="内景" />
                  <el-option label="外景 EXT." value="外景" />
                </el-select>
              </div>
              <div class="attr-field">
                <label>时间</label>
                <el-select v-model="currentScene.scene_attr.time_type" style="width: 100%">
                  <el-option label="日 DAY" value="日" />
                  <el-option label="夜 NIGHT" value="夜" />
                  <el-option label="黄昏 DUSK" value="黄昏" />
                  <el-option label="凌晨 DAWN" value="凌晨" />
                </el-select>
              </div>
            </div>
          </section>

          <!-- 剧情单元编辑列表 -->
          <section class="units-section">
            <div class="sec-header">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
              <h3>剧情单元</h3>
              <span class="unit-count">{{ currentScene.scene_content.length }}</span>
              <button class="add-unit-btn" @click="addUnit">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                添加
              </button>
            </div>

            <div class="unit-editor-list">
              <transition-group name="unit-list">
                <div
                  v-for="(unit, uIndex) in currentScene.scene_content"
                  :key="unit.unit_id"
                  class="unit-editor-item"
                >
                  <div class="unit-editor-controls">
                    <select
                      v-model="unit.unit_type"
                      class="type-select"
                      :class="'type-' + unit.unit_type"
                    >
                      <option value="action">动作</option>
                      <option value="dialogue">台词</option>
                      <option value="narration">旁白</option>
                      <option value="psy">心理</option>
                    </select>
                    <input
                      v-model="unit.character"
                      type="text"
                      class="char-input"
                      placeholder="人物名..."
                      list="char-list"
                    />
                    <datalist id="char-list">
                      <option v-for="c in scriptData.global_characters" :key="c.char_id" :value="c.char_name" />
                    </datalist>
                    <button
                      class="remove-unit-btn"
                      title="删除单元"
                      @click="deleteUnit(uIndex)"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                  <textarea
                    v-model="unit.content"
                    class="content-textarea"
                    placeholder="输入内容..."
                    rows="2"
                  ></textarea>
                </div>
              </transition-group>
            </div>

            <div class="empty-units-hint" v-if="!currentScene.scene_content.length">
              <p>暂无剧情单元，点击上方「添加」按钮创建</p>
            </div>
          </section>

          <!-- 操作栏 -->
          <div class="editor-actions">
            <button class="act-btn ghost" @click="$router.back()">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
              返回预览
            </button>
            <button class="act-btn primary" @click="saveChanges">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
              保存修改
            </button>
            <button class="act-btn success" @click="downloadYaml">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              导出 YAML
            </button>
          </div>
        </template>

        <div class="no-selection" v-else>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></svg>
          <p>在左侧选择一个场次开始编辑</p>
        </div>
      </main>
    </div>
  </div>

  <div class="empty-state" v-else>
    <h3>暂无剧本数据</h3>
    <p>请先上传小说进行转换</p>
    <button class="empty-action" @click="$router.push('/')">去上传</button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { ScriptYAML, ScriptScene, SceneContentUnit } from '@/types/script'

const router = useRouter()
const scriptData = ref<ScriptYAML | null>(null)
const activeSceneId = ref<number | null>(null)
let idCounter = 0

const currentScene = computed<ScriptScene | undefined>(() => {
  if (!scriptData.value || activeSceneId.value === null) return undefined
  return scriptData.value.script_scenes.find(s => s.scene_id === activeSceneId.value)
})

onMounted(() => {
  const stored = sessionStorage.getItem('script_data')
  if (stored) {
    try {
      const parsed = JSON.parse(stored) as ScriptYAML
      scriptData.value = JSON.parse(JSON.stringify(parsed))
      if (parsed.script_scenes.length > 0) {
        const maxSceneId = Math.max(...parsed.script_scenes.map(s => s.scene_id))
        idCounter = maxSceneId + 1
      }
      if (scriptData.value.script_scenes.length > 0) {
        activeSceneId.value = scriptData.value.script_scenes[0].scene_id
      }
    } catch {
      ElMessage.error('数据加载失败')
    }
  }
})

function addScene() {
  if (!scriptData.value) return
  const newScene: ScriptScene = {
    scene_id: ++idCounter,
    scene_serial: `S${String(scriptData.value.script_scenes.length + 1).padStart(2, '0')}`,
    scene_attr: { location: '', scene_type: '内景', time_type: '日' },
    scene_summary: '',
    scene_content: [],
    scene_note: '',
  }
  scriptData.value.script_scenes.push(newScene)
  activeSceneId.value = newScene.scene_id
}

async function deleteScene(index: number) {
  if (!scriptData.value) return
  try {
    await ElMessageBox.confirm('确定删除该场次吗？此操作不可撤销。', '确认删除', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    scriptData.value.script_scenes.splice(index, 1)
    if (scriptData.value.script_scenes.length > 0) {
      activeSceneId.value = scriptData.value.script_scenes[0].scene_id
    } else {
      activeSceneId.value = null
    }
  } catch { /* cancel */ }
}

function addUnit() {
  if (!scriptData.value || !currentScene.value) return
  const newUnit: SceneContentUnit = {
    unit_id: currentScene.value.scene_content.length + 1,
    unit_type: 'action',
    character: '',
    content: '',
  }
  currentScene.value.scene_content.push(newUnit)
}

function deleteUnit(index: number) {
  if (currentScene.value) currentScene.value.scene_content.splice(index, 1)
}

function saveChanges() {
  if (!scriptData.value) return
  sessionStorage.setItem('script_data', JSON.stringify(scriptData.value))
  ElMessage.success('修改已保存')
}

function downloadYaml() {
  if (!scriptData.value) return
  let yaml = `script_meta:\n`
  yaml += `  script_title: ${scriptData.value.script_meta.script_title}\n`
  yaml += `  original_novel_title: ${scriptData.value.script_meta.original_novel_title}\n`
  yaml += `  chapter_range: ${scriptData.value.script_meta.chapter_range}\n`
  yaml += `  create_time: ${scriptData.value.script_meta.create_time}\n`
  yaml += `  script_type: ${scriptData.value.script_meta.script_type}\n`
  yaml += `  version: ${scriptData.value.script_meta.version}\n\n`
  for (const scene of scriptData.value.script_scenes) {
    yaml += `- scene_id: ${scene.scene_id}\n  scene_serial: ${scene.scene_serial}\n  scene_attr:\n    location: ${scene.scene_attr.location}\n    scene_type: ${scene.scene_attr.scene_type}\n    time_type: ${scene.scene_attr.time_type}\n  scene_summary: ${scene.scene_summary}\n  scene_content:\n`
    for (const unit of scene.scene_content) {
      yaml += `    - unit_id: ${unit.unit_id}\n      unit_type: ${unit.unit_type}\n      character: "${unit.character}"\n      content: ${unit.content}\n`
    }
    yaml += `  scene_note: ${scene.scene_note}\n`
  }
  yaml += `\nglobal_characters:\n`
  for (const char of scriptData.value.global_characters) {
    yaml += `  - char_id: ${char.char_id}\n    char_name: ${char.char_name}\n    char_profile: ${char.char_profile}\n`
  }
  yaml += `\nadapt_rule_note: ${scriptData.value.adapt_rule_note}\n`

  const blob = new Blob([yaml], { type: 'text/yaml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${scriptData.value.script_meta.script_title}_edited.yaml`
  document.body.appendChild(link); link.click(); document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success('文件已开始下载')
}
</script>

<style scoped>
.edit-view {
  height: calc(100vh - 120px);
}

.edit-layout {
  display: flex;
  gap: 20px;
  height: 100%;
}

/* ====== 左侧面板 ====== */
.scene-panel {
  width: 260px;
  min-width: 260px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border-bottom: 1px solid var(--border-subtle);
}

.ph-left {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
}
.ph-left svg { opacity: 0.6; }

.scene-total {
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--accent-dim);
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
}

.add-scene-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;
}
.add-scene-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-dim);
}

.scene-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.scene-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s var(--ease-out);
  margin-bottom: 4px;
  border: 1px solid transparent;
}
.scene-item:hover {
  background: var(--bg-card-hover);
}
.scene-item.active {
  background: rgba(201, 162, 39, 0.06);
  border-color: rgba(201, 162, 39, 0.2);
}

.item-serial {
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 800;
  color: var(--accent);
  background: var(--accent-dim);
  padding: 3px 8px;
  border-radius: 5px;
  letter-spacing: -0.3px;
  flex-shrink: 0;
}

.item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.item-location {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-meta {
  font-size: 11px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 5px;
}

.meta-dot {
  width: 5px; height: 5px; border-radius: 50%;
  display: inline-block;
}
.meta-dot.int { background: var(--color-int); }
.meta-dot.ext { background: var(--color-ext); }

.delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s;
}
.scene-item:hover .delete-btn {
  opacity: 1;
}
.delete-btn:hover {
  background: rgba(238, 76, 60, 0.1);
  color: #ee4c3c;
}

.panel-footer {
  padding: 12px 18px;
  border-top: 1px solid var(--border-subtle);
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
}

/* ====== 右侧编辑区 ====== */
.editor-panel {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.sec-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.sec-header svg { opacity: 0.5; color: var(--accent); }
.sec-header h3 {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 1px;
}

.sec-badge {
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 800;
  color: var(--accent);
  background: var(--accent-dim);
  padding: 2px 9px;
  border-radius: 5px;
  letter-spacing: 0.5px;
}

.sec-tags {
  display: flex;
  gap: 6px;
  margin-left: auto;
}

.tag {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.tag-int { background: rgba(232, 168, 76, 0.12); color: var(--color-int); }
.tag-ext { background: rgba(94, 184, 184, 0.12); color: var(--color-ext); }
.tag-time { background: var(--bg-elevated); color: var(--text-muted); }
.tag-loc { background: var(--bg-elevated); color: var(--text-secondary); max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.unit-count {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  background: var(--bg-base);
  padding: 2px 8px;
  border-radius: 99px;
}

.add-unit-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  border: 1px dashed var(--border-medium);
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-family: var(--font-ui);
}
.add-unit-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* 属性区域 */
.attr-section {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 22px 26px;
}

.attr-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.attr-field.full { grid-column: 1 / -1; }
.attr-field label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-bottom: 6px;
}

/* 单元区域 */
.units-section {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 22px 26px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.unit-editor-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
}

.unit-editor-item {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  transition: border-color 0.2s;
  position: relative;
}
.unit-editor-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 2px;
  border-radius: 1px;
  background: var(--border-medium);
  transition: background 0.2s;
}
.unit-editor-item:nth-child(4n+1)::before { background: var(--color-action); }
.unit-editor-item:nth-child(4n+2)::before { background: var(--color-dialogue); }
.unit-editor-item:nth-child(4n+3)::before { background: var(--color-narration); }
.unit-editor-item:nth-child(4n+0)::before { background: var(--color-psy); }

.unit-editor-controls {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.type-select {
  padding: 4px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 5px;
  background: var(--bg-elevated);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-ui);
  cursor: pointer;
  outline: none;
  min-width: 72px;
}
.type-select:focus { border-color: var(--accent); }
.type-select.option-action, .type-select.type-action { color: var(--color-action); }
.type-select.option-dialogue, .type-select.type-dialogue { color: var(--color-dialogue); }
.type-select.option-narration, .type-select.type-narration { color: var(--color-narration); }
.type-select.option-psy, .type-select.type-psy { color: var(--color-psy); }

.char-input {
  flex: 1;
  padding: 4px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 5px;
  background: var(--bg-elevated);
  color: var(--text-primary);
  font-size: 12px;
  font-family: var(--font-ui);
  outline: none;
  min-width: 0;
  transition: border-color 0.2s;
}
.char-input:focus { border-color: var(--accent); }
.char-input::placeholder { color: var(--text-muted); }

.remove-unit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;
}
.remove-unit-btn:hover {
  background: rgba(238, 76, 60, 0.08);
  color: #ee4c3c;
}

.content-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  background: var(--bg-base);
  color: var(--text-primary);
  font-size: 13px;
  font-family: var(--font-ui);
  line-height: 1.65;
  resize: vertical;
  outline: none;
  transition: border-color 0.2s;
}
.content-textarea:focus { border-color: var(--accent); }
.content-textarea::placeholder { color: var(--text-muted); }

.empty-units-hint {
  text-align: center;
  padding: 32px 0;
  color: var(--text-muted);
  font-size: 13px;
}

/* 操作栏 */
.editor-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  padding-top: 8px;
}

.act-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 20px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font-ui);
  cursor: pointer;
  transition: all 0.25s var(--ease-out);
}
.act-btn:hover {
  border-color: var(--border-medium);
  color: var(--text-primary);
}
.act-btn.primary {
  border-color: var(--accent);
  color: var(--accent);
}
.act-btn.primary:hover { background: var(--accent-dim); }
.act-btn.success {
  border-color: var(--color-dialogue);
  color: var(--color-dialogue);
}
.act-btn.success:hover { background: rgba(126, 207, 153, 0.08); }

/* 无选中状态 */
.no-selection {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--text-muted);
  opacity: 0.35;
}
.no-selection p { font-size: 14px; }

/* 单元列表动画 */
.unit-list-enter-active { transition: all 0.3s var(--ease-out); }
.unit-list-leave-active { transition: all 0.2s ease-in; }
.unit-list-enter-from { opacity: 0; transform: translateX(-12px); }
.unit-list-leave-to { opacity: 0; transform: translateX(12px); }

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 80px 0;
  color: var(--text-muted);
}
.empty-state h3 { font-family: var(--font-display); font-size: 18px; }
.empty-state p { font-size: 13px; }
.empty-action {
  padding: 8px 24px;
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font-ui);
  cursor: pointer;
  margin-top: 8px;
}
.empty-action:hover { background: var(--accent-dim); }
</style>
